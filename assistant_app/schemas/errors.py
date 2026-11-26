"""The one error shape returned everywhere."""

import uuid
from typing import Literal, get_args

from pydantic import StrictBool

from assistant_app.schemas.base import RequestId, StrictModel, constrained_str

ErrorCode = Literal[
    "validation_error",
    "authentication_required",
    "permission_denied",
    "not_found",
    "unknown_tool",
    "rate_limited",
    "upstream_error",
    "upstream_timeout",
    "internal_error",
]
ERROR_CODES = get_args(ErrorCode)

ErrorMessage = constrained_str(1, 300)


class ErrorResponse(StrictModel):
    code: ErrorCode
    message: ErrorMessage
    retryable: StrictBool
    request_id: RequestId


def new_request_id() -> str:
    """A fresh, unguessable request ID, for example req_3f9a..."""
    return "req_" + uuid.uuid4().hex
