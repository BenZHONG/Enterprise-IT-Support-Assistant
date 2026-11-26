"""Request and response bodies for the assistant's HTTP API (used from Stage 6).

None of these has a field for employee ID, role, or region: identity
comes from the server's trusted context, never from the request body.
"""

from pydantic import Field

from assistant_app.schemas.base import (
    PreviewId,
    RequestId,
    StrictModel,
    constrained_str,
)
from assistant_app.schemas.results import Citation

# Must equal assistant_app.cli.MAX_MESSAGE_LENGTH (a test checks this).
MAX_MESSAGE_LENGTH = 500

UserMessage = constrained_str(1, MAX_MESSAGE_LENGTH)
ReplyText = constrained_str(1, 4000)


class ChatRequest(StrictModel):
    message: UserMessage


class ChatResponse(StrictModel):
    reply: ReplyText
    request_id: RequestId
    citations: tuple[Citation, ...] = Field(default=(), max_length=10)


class ConfirmTicketRequest(StrictModel):
    """The employee's explicit confirmation of ONE specific preview."""

    preview_id: PreviewId
