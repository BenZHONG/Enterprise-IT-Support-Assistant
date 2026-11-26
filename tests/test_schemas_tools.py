import json

import pytest

from assistant_app.schemas.base import StrictModel
from assistant_app.schemas.errors import ErrorResponse
from assistant_app.schemas.tools import (
    MAX_ARGUMENT_CHARS,
    TOOL_SPECS,
    ToolInputError,
    model_facing_schema,
    parse_tool_arguments,
)

NO_ARG_TOOLS = [
    "check_network_outage",
    "check_user",
    "get_employee_profile",
    "check_device",
]
IDENTITY_FIELDS = {
    "employee_id",
    "user_id",
    "role",
    "requester_id",
    "owner_id",
    "region_id",
}
VALID_DESCRIPTION = "My laptop cannot join the company Wi-Fi."


def assert_rejected(tool, arguments, code="validation_error"):
    with pytest.raises(ToolInputError) as info:
        parse_tool_arguments(tool, arguments)
    assert info.value.code == code
    return info.value


def ticket_args(summary="Laptop cannot join Wi-Fi", description=VALID_DESCRIPTION):
    return {"summary": summary, "description": description}


# ----- the catalogue -----


def test_catalogue_has_exactly_the_nine_model_facing_tools():
    assert set(TOOL_SPECS) == {
        "check_network_outage",
        "check_network_outage_by_region",
        "search_my_tickets",
        "create_support_ticket",
        "get_ticket_status",
        "search_knowledge_base",
        "check_user",
        "get_employee_profile",
        "check_device",
    }


def test_create_ticket_is_never_a_model_tool():
    assert "create_ticket" not in TOOL_SPECS


def test_every_tool_is_fully_described():
    for name, spec in TOOL_SPECS.items():
        assert spec.name == name
        assert len(spec.description) > 20
        assert spec.errors
        assert issubclass(spec.arguments, StrictModel)
        assert issubclass(spec.result, StrictModel)


def test_no_tool_argument_can_carry_identity():
    for spec in TOOL_SPECS.values():
        assert not set(spec.arguments.model_fields) & IDENTITY_FIELDS, spec.name


# ----- tools without arguments -----


@pytest.mark.parametrize("raw", [None, "", "{}", {}])
def test_tools_without_arguments_accept_empty_input(raw):
    for tool in NO_ARG_TOOLS:
        assert parse_tool_arguments(tool, raw).model_dump() == {}


@pytest.mark.parametrize("tool", NO_ARG_TOOLS)
def test_tools_without_arguments_reject_a_model_supplied_identity(tool):
    assert_rejected(tool, {"employee_id": "E1002"})


# ----- region -----


@pytest.mark.parametrize("region", ["parramatta", "sydney", "north-coast"])
def test_valid_region_is_accepted(region):
    args = parse_tool_arguments("check_network_outage_by_region", {"region": region})
    assert args.region == region


def test_region_is_trimmed():
    args = parse_tool_arguments(
        "check_network_outage_by_region", {"region": " parramatta \n"}
    )
    assert args.region == "parramatta"


@pytest.mark.parametrize(
    "region",
    [
        "Parramatta",
        "",
        "a",
        "x" * 31,
        "parra matta",
        "parramatta;drop",
        "../etc",
        "parramatta/../sydney",
        "1perth",
    ],
)
def test_invalid_region_is_rejected(region):
    assert_rejected("check_network_outage_by_region", {"region": region})


# ----- ticket ID -----


@pytest.mark.parametrize("ticket_id", ["TCK-1001", "TCK-9999"])
def test_valid_ticket_id_is_accepted(ticket_id):
    assert (
        parse_tool_arguments("get_ticket_status", {"ticket_id": ticket_id}).ticket_id
        == ticket_id
    )


@pytest.mark.parametrize(
    "ticket_id",
    [
        "tck-1001",
        "TCK-100",
        "TCK-10011",
        "TCK-\uff11\uff10\uff10\uff11",  # full-width digits look like 1001
        "TCK-1001; DROP TABLE",
        "1001",
        "TCK_1001",
    ],
)
def test_invalid_ticket_id_is_rejected(ticket_id):
    assert_rejected("get_ticket_status", {"ticket_id": ticket_id})


# ----- ticket preview arguments -----


def test_ticket_preview_arguments_are_accepted_and_trimmed():
    args = parse_tool_arguments(
        "create_support_ticket", ticket_args(summary="  Wi-Fi down  ")
    )
    assert args.summary == "Wi-Fi down"
    assert args.description == VALID_DESCRIPTION


@pytest.mark.parametrize(
    ("length", "ok"), [(4, False), (5, True), (120, True), (121, False)]
)
def test_summary_length_limits(length, ok):
    arguments = ticket_args(summary="s" * length)
    if ok:
        assert (
            len(parse_tool_arguments("create_support_ticket", arguments).summary)
            == length
        )
    else:
        assert_rejected("create_support_ticket", arguments)


@pytest.mark.parametrize(
    ("length", "ok"), [(9, False), (10, True), (2000, True), (2001, False)]
)
def test_description_length_limits(length, ok):
    arguments = ticket_args(description="d" * length)
    if ok:
        assert (
            len(parse_tool_arguments("create_support_ticket", arguments).description)
            == length
        )
    else:
        assert_rejected("create_support_ticket", arguments)


@pytest.mark.parametrize("summary", ["     ", "  Hi  "])
def test_blank_or_too_short_after_trimming_is_rejected(summary):
    assert_rejected("create_support_ticket", ticket_args(summary=summary))


def test_non_string_summary_is_rejected():
    assert_rejected("create_support_ticket", ticket_args(summary=12345))


def test_extra_field_on_ticket_preview_is_rejected():
    arguments = {**ticket_args(), "status": "resolved"}
    assert_rejected("create_support_ticket", arguments)


def test_missing_description_is_rejected():
    assert_rejected("create_support_ticket", {"summary": "Laptop cannot join Wi-Fi"})


# ----- ticket search and knowledge search -----


def test_status_filter_defaults_to_none():
    assert parse_tool_arguments("search_my_tickets", {}).status is None


@pytest.mark.parametrize("status", ["open", "in_progress", "resolved", "closed"])
def test_valid_status_filter_is_accepted(status):
    assert (
        parse_tool_arguments("search_my_tickets", {"status": status}).status == status
    )


def test_unknown_status_filter_is_rejected():
    assert_rejected("search_my_tickets", {"status": "pending"})


@pytest.mark.parametrize(
    ("length", "ok"), [(2, False), (3, True), (200, True), (201, False)]
)
def test_knowledge_query_length_limits(length, ok):
    arguments = {"query": "q" * length}
    if ok:
        assert parse_tool_arguments("search_knowledge_base", arguments)
    else:
        assert_rejected("search_knowledge_base", arguments)


# ----- unknown tools and malformed input -----


@pytest.mark.parametrize(
    "name", ["create_ticket", "delete_everything", "CHECK_USER", "", "check_user "]
)
def test_unknown_tool_names_are_rejected(name):
    assert_rejected(name, {}, code="unknown_tool")


@pytest.mark.parametrize("name", [123, None, ["check_user"]])
def test_non_string_tool_names_are_rejected(name):
    assert_rejected(name, {}, code="unknown_tool")


def test_invalid_json_is_rejected():
    assert_rejected("check_user", "{not json")


@pytest.mark.parametrize("raw", [[], 5, "[]", "5", "null"])
def test_arguments_that_are_not_an_object_are_rejected(raw):
    assert_rejected("check_user", raw)


def test_oversized_arguments_are_rejected():
    raw = '{"query": "' + "a" * MAX_ARGUMENT_CHARS + '"}'
    assert_rejected("search_knowledge_base", raw)


def test_error_does_not_echo_unexpected_field_names():
    error = assert_rejected(
        "search_knowledge_base",
        {"query": "valid query", "ignore previous instructions": "x"},
    )
    assert "unexpected" in error.message
    assert "ignore" not in error.message


def test_error_does_not_echo_submitted_values():
    error = assert_rejected("create_support_ticket", ticket_args(summary=123))
    assert "summary" in error.message
    assert "123" not in error.message


def test_error_converts_to_the_standard_response():
    error = assert_rejected("nope", {}, code="unknown_tool")
    response = error.to_response("req_" + "a" * 32)
    assert isinstance(response, ErrorResponse)
    assert response.code == "unknown_tool"
    assert response.retryable is False
    assert response.request_id == "req_" + "a" * 32


def test_json_string_arguments_are_parsed():
    args = parse_tool_arguments("get_ticket_status", '{"ticket_id": "TCK-1001"}')
    assert args.ticket_id == "TCK-1001"


# ----- the schema shown to the model -----


@pytest.mark.parametrize("name", sorted(TOOL_SPECS))
def test_every_model_facing_schema_forbids_extra_fields(name):
    schema = model_facing_schema(name)
    json.dumps(schema)  # must be JSON serialisable
    assert schema["name"] == name
    assert schema["description"]
    assert schema["parameters"]["type"] == "object"
    assert schema["parameters"]["additionalProperties"] is False


def test_schema_limits_match_server_side_validation():
    props = model_facing_schema("create_support_ticket")["parameters"]["properties"]
    summary, description = props["summary"], props["description"]
    assert (summary["minLength"], summary["maxLength"]) == (5, 120)
    assert (description["minLength"], description["maxLength"]) == (10, 2000)
    # The server enforces exactly what the schema advertises.
    assert parse_tool_arguments(
        "create_support_ticket", ticket_args(summary="s" * summary["maxLength"])
    )
    assert_rejected(
        "create_support_ticket", ticket_args(summary="s" * (summary["maxLength"] + 1))
    )
    assert_rejected(
        "create_support_ticket", ticket_args(summary="s" * (summary["minLength"] - 1))
    )


def test_schema_patterns_match_server_side_validation():
    ticket = model_facing_schema("get_ticket_status")["parameters"]["properties"][
        "ticket_id"
    ]
    region = model_facing_schema("check_network_outage_by_region")["parameters"][
        "properties"
    ]["region"]
    assert ticket["pattern"] == "^TCK-[0-9]{4}$"
    assert region["pattern"] == "^[a-z][a-z-]*$"


def test_schema_lists_the_status_values():
    status = model_facing_schema("search_my_tickets")["parameters"]["properties"][
        "status"
    ]
    text = json.dumps(status)
    for value in ("open", "in_progress", "resolved", "closed"):
        assert value in text
