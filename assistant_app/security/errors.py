"""One error type for authentication, authorization, and lookups.

The default messages are fixed text. In particular, "not found" is the
same message whether a resource is missing or belongs to someone else.
"""

from assistant_app.schemas.errors import ErrorCode, ErrorResponse

_DEFAULT_MESSAGES: dict[str, str] = {
    "authentication_required": "Authentication is required.",
    "permission_denied": "You do not have permission to do that.",
    "not_found": "The requested item was not found.",
    "validation_error": "The request was not valid.",
    "internal_error": "Something went wrong on our side.",
}


class ServiceError(Exception):
    def __init__(self, code: ErrorCode, message: str | None = None) -> None:
        self.code: ErrorCode = code
        self.message = message or _DEFAULT_MESSAGES.get(code, "Something went wrong.")
        super().__init__(self.message)

    def to_response(self, request_id: str) -> ErrorResponse:
        return ErrorResponse(
            code=self.code,
            message=self.message,
            retryable=False,
            request_id=request_id,
        )
