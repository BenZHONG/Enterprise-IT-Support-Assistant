"""The model-facing tool catalogue.

For each tool: name, description for the model, argument model, result
model, and the error codes it can produce. The JSON Schema shown to the
model is generated from the SAME argument models that validate the
calls, so the two cannot drift apart.

create_ticket is deliberately NOT here: the model must never be able to
write a ticket. Only the service layer (Stage 15) can.

Permissions per tool are added in Stage 5 (roles) and the full registry,
with enable/disable switches, arrives in Stage 12.
"""

from dataclasses import dataclass

from pydantic import ValidationError

from assistant_app.schemas.base import (
    RegionId,
    StrictModel,
    TicketDescription,
    TicketId,
    TicketStatus,
    TicketSummary,
    constrained_str,
)
from assistant_app.schemas.errors import ErrorCode, ErrorResponse
from assistant_app.schemas.results import (
    DeviceCheckResult,
    KnowledgeSearchResult,
    OutageCheckResult,
    ProfileResult,
    TicketListResult,
    TicketPreview,
    TicketStatusResult,
    UserCheckResult,
)

MAX_ARGUMENT_CHARS = 10_000

KnowledgeQuery = constrained_str(3, 200)


# ----- argument models -----


class NoArguments(StrictModel):
    """For tools that take nothing. Who the employee is comes from trusted
    server context, so any model-supplied identity is an unexpected field."""


class CheckNetworkOutageByRegionArgs(StrictModel):
    region: RegionId


class SearchMyTicketsArgs(StrictModel):
    status: TicketStatus | None = None


class CreateSupportTicketArgs(StrictModel):
    summary: TicketSummary
    description: TicketDescription


class GetTicketStatusArgs(StrictModel):
    ticket_id: TicketId


class SearchKnowledgeBaseArgs(StrictModel):
    query: KnowledgeQuery


# ----- catalogue -----


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    arguments: type[StrictModel]
    result: type[StrictModel]
    errors: tuple[ErrorCode, ...]


_COMMON_ERRORS: tuple[ErrorCode, ...] = (
    "authentication_required",
    "permission_denied",
    "rate_limited",
    "upstream_error",
    "upstream_timeout",
    "internal_error",
)


def _errors(*extra: ErrorCode) -> tuple[ErrorCode, ...]:
    return extra + _COMMON_ERRORS


_SPECS = (
    ToolSpec(
        "check_network_outage",
        "Check for network outages in the signed-in employee's own office "
        "region. Takes no arguments.",
        NoArguments,
        OutageCheckResult,
        _errors(),
    ),
    ToolSpec(
        "check_network_outage_by_region",
        "Check for network outages in one named office region, only if the "
        "employee is allowed to see that region. region is a lowercase "
        "region ID such as 'melbourne'.",
        CheckNetworkOutageByRegionArgs,
        OutageCheckResult,
        _errors("validation_error"),
    ),
    ToolSpec(
        "search_my_tickets",
        "List the signed-in employee's own support tickets. Optionally "
        "filter by status.",
        SearchMyTicketsArgs,
        TicketListResult,
        _errors("validation_error"),
    ),
    ToolSpec(
        "create_support_ticket",
        "Prepare a ticket PREVIEW for the employee to review. This does not "
        "create a ticket. The employee must confirm it separately.",
        CreateSupportTicketArgs,
        TicketPreview,
        _errors("validation_error"),
    ),
    ToolSpec(
        "get_ticket_status",
        "Get the status of one of the employee's own tickets by ticket ID, "
        "for example 'TCK-1001'.",
        GetTicketStatusArgs,
        TicketStatusResult,
        _errors("validation_error", "not_found"),
    ),
    ToolSpec(
        "search_knowledge_base",
        "Search the IT knowledge articles the employee is allowed to read. "
        "Returns short excerpts with source IDs.",
        SearchKnowledgeBaseArgs,
        KnowledgeSearchResult,
        _errors("validation_error"),
    ),
    ToolSpec(
        "check_user",
        "Check whether the signed-in employee's account exists and is "
        "active. Takes no arguments.",
        NoArguments,
        UserCheckResult,
        _errors(),
    ),
    ToolSpec(
        "get_employee_profile",
        "Get the signed-in employee's basic profile (name, department, "
        "office region, role). Takes no arguments.",
        NoArguments,
        ProfileResult,
        _errors("not_found"),
    ),
    ToolSpec(
        "check_device",
        "Get diagnostics for the signed-in employee's own devices. Missing "
        "telemetry is reported separately from a device fault. Takes no "
        "arguments.",
        NoArguments,
        DeviceCheckResult,
        _errors(),
    ),
)

TOOL_SPECS: dict[str, ToolSpec] = {spec.name: spec for spec in _SPECS}


# ----- parsing -----


class ToolInputError(Exception):
    """A tool call that must be refused. The message is safe to show: it
    never contains text the model supplied."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_response(self, request_id: str) -> ErrorResponse:
        return ErrorResponse(
            code=self.code,
            message=self.message,
            retryable=False,
            request_id=request_id,
        )


def get_tool_spec(tool_name: object) -> ToolSpec:
    # isinstance first: a model could send a list, which is not hashable.
    if not isinstance(tool_name, str) or tool_name not in TOOL_SPECS:
        raise ToolInputError("unknown_tool", "Unknown tool.")
    return TOOL_SPECS[tool_name]


def _summarise(exc: ValidationError, model: type[StrictModel]) -> str:
    """Describe what is wrong using field names WE defined and error type
    names only. Never echo submitted keys or values: they are untrusted
    and may hold secrets or injected instructions."""
    known = set(model.model_fields)
    parts: list[str] = []
    for error in exc.errors():
        loc = error.get("loc", ())
        if error["type"] == "extra_forbidden":
            part = "unexpected field not allowed"
        else:
            field = str(loc[0]) if loc and loc[0] in known else "arguments"
            part = f"{field}: {error['type']}"
        if part not in parts:
            parts.append(part)
    return ("Invalid tool arguments - " + "; ".join(parts))[:300]


def parse_tool_arguments(
    tool_name: object, raw_arguments: object = None
) -> StrictModel:
    """Validate one model-requested tool call.

    raw_arguments may be None, a dict, or a JSON string.
    Raises ToolInputError for unknown tools and for any invalid arguments.
    """
    spec = get_tool_spec(tool_name)
    model = spec.arguments
    try:
        if raw_arguments is None:
            return model.model_validate({})
        if isinstance(raw_arguments, dict):
            return model.model_validate(raw_arguments)
        if isinstance(raw_arguments, str):
            text = raw_arguments.strip()
            if len(text) > MAX_ARGUMENT_CHARS:
                raise ToolInputError(
                    "validation_error", "Invalid tool arguments - arguments too long."
                )
            if not text:
                return model.model_validate({})
            return model.model_validate_json(text)
    except ValidationError as exc:
        # "from None": the original error text contains the submitted values.
        raise ToolInputError("validation_error", _summarise(exc, model)) from None
    raise ToolInputError(
        "validation_error",
        "Invalid tool arguments - arguments must be a JSON object.",
    )


def model_facing_schema(tool_name: str) -> dict:
    """The definition shown to the model, generated from the argument model."""
    spec = get_tool_spec(tool_name)
    return {
        "name": spec.name,
        "description": spec.description,
        "parameters": spec.arguments.model_json_schema(),
    }
