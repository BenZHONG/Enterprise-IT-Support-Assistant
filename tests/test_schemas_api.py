import re
from typing import get_args

import pytest
from pydantic import ValidationError

from assistant_app.cli import MAX_MESSAGE_LENGTH as CLI_MAX_MESSAGE_LENGTH
from assistant_app.schemas import api
from assistant_app.schemas.api import ChatRequest, ChatResponse, ConfirmTicketRequest
from assistant_app.schemas.errors import ErrorCode, ErrorResponse, new_request_id

CITATION = {
    "source_id": "KB-001",
    "title": "Wi-Fi Troubleshooting",
    "version": "1.2",
    "chunk_id": "KB-001#03",
}
REQUEST_ID = "req_" + "a" * 32


def error_data(**changes):
    data = {
        "code": "not_found",
        "message": "Ticket not found.",
        "retryable": False,
        "request_id": REQUEST_ID,
    }
    data.update(changes)
    return data


# ----- chat request -----


def test_chat_request_trims_whitespace():
    assert ChatRequest(message="  my wifi is down  ").message == "my wifi is down"


def test_message_limit_matches_the_cli():
    assert api.MAX_MESSAGE_LENGTH == CLI_MAX_MESSAGE_LENGTH


@pytest.mark.parametrize(
    ("length", "ok"), [(0, False), (1, True), (500, True), (501, False)]
)
def test_message_length_limits(length, ok):
    data = {"message": "m" * length}
    if ok:
        assert ChatRequest.model_validate(data)
    else:
        with pytest.raises(ValidationError):
            ChatRequest.model_validate(data)


def test_whitespace_only_message_is_rejected():
    with pytest.raises(ValidationError):
        ChatRequest.model_validate({"message": "     "})


@pytest.mark.parametrize("field", ["employee_id", "role", "region_id"])
def test_chat_request_rejects_identity_fields(field):
    with pytest.raises(ValidationError):
        ChatRequest.model_validate({"message": "hi", field: "x"})


def test_non_string_message_is_rejected():
    with pytest.raises(ValidationError):
        ChatRequest.model_validate({"message": 123})


def test_chat_request_parses_json():
    assert ChatRequest.model_validate_json('{"message": "hello"}').message == "hello"
    with pytest.raises(ValidationError):
        ChatRequest.model_validate_json('{"message": ')


# ----- chat response -----


def test_chat_response_with_citations():
    response = ChatResponse.model_validate(
        {"reply": "Try restarting.", "request_id": REQUEST_ID, "citations": [CITATION]}
    )
    assert response.citations[0].source_id == "KB-001"


def test_chat_response_defaults_to_no_citations():
    response = ChatResponse(reply="Try restarting.", request_id=REQUEST_ID)
    assert response.citations == ()


def test_chat_response_rejects_more_than_ten_citations():
    with pytest.raises(ValidationError):
        ChatResponse.model_validate(
            {"reply": "x", "request_id": REQUEST_ID, "citations": [CITATION] * 11}
        )


# ----- errors -----


def test_valid_error_response():
    response = ErrorResponse.model_validate(error_data())
    assert response.code == "not_found"
    assert response.retryable is False


def test_error_codes_cover_the_required_categories():
    required = {
        "validation_error",
        "authentication_required",
        "permission_denied",
        "not_found",
        "unknown_tool",
        "rate_limited",
        "upstream_error",
        "internal_error",
    }
    assert required <= set(get_args(ErrorCode))


def test_unknown_error_code_is_rejected():
    with pytest.raises(ValidationError):
        ErrorResponse.model_validate(error_data(code="oops"))


def test_retryable_must_be_a_real_boolean():
    with pytest.raises(ValidationError):
        ErrorResponse.model_validate(error_data(retryable="true"))


@pytest.mark.parametrize("request_id", ["", "short", "has space!!", "x" * 65])
def test_bad_request_ids_are_rejected(request_id):
    with pytest.raises(ValidationError):
        ErrorResponse.model_validate(error_data(request_id=request_id))


def test_new_request_ids_are_valid_and_unique():
    first, second = new_request_id(), new_request_id()
    assert re.fullmatch(r"req_[0-9a-f]{32}", first)
    assert first != second
    ErrorResponse.model_validate(error_data(request_id=first))


# ----- ticket confirmation -----


def test_confirm_request_accepts_a_preview_id():
    request = ConfirmTicketRequest.model_validate({"preview_id": "prv_" + "b" * 32})
    assert request.preview_id == "prv_" + "b" * 32


def test_confirm_request_rejects_a_bad_preview_id():
    with pytest.raises(ValidationError):
        ConfirmTicketRequest.model_validate({"preview_id": "yes"})


def test_confirm_request_rejects_extra_fields():
    with pytest.raises(ValidationError):
        ConfirmTicketRequest.model_validate(
            {"preview_id": "prv_" + "b" * 32, "employee_id": "E1001"}
        )
