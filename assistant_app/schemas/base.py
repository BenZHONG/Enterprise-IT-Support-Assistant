"""Shared base class and constrained field types for every schema.

Rules every model follows:
- extra="forbid": unexpected fields are rejected, never silently ignored.
- frozen=True: a validated object cannot be changed afterwards.
- Strict text fields: the number 123 (or bytes) is NOT accepted as text.
- Whitespace is trimmed before length and pattern checks.
- Patterns use [0-9], never the regex shortcut for digits, because that
  shortcut also matches digits from other scripts (for example full-width
  digits) and would let look-alike IDs through.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def constrained_str(min_length: int, max_length: int, pattern: str | None = None):
    """Build a strict, trimmed string type with length (and optional pattern) limits."""
    return Annotated[
        str,
        StringConstraints(
            strict=True,
            strip_whitespace=True,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
        ),
    ]


# Allowed values. tests/test_schemas_results.py checks these match the seed data.
Role = Literal["employee", "it_support_agent", "it_administrator"]
TicketStatus = Literal["open", "in_progress", "resolved", "closed"]
TicketPriority = Literal["low", "medium", "high"]
TicketCategory = Literal[
    "wifi", "vpn", "password", "microsoft365", "hardware", "network"
]
OutageStatus = Literal["active", "resolved"]
OutageSeverity = Literal["minor", "major"]
OutageService = Literal["corporate_wifi", "vpn", "internet"]
DeviceStatus = Literal["in_service", "awaiting_return", "in_repair"]
WifiAdapterState = Literal["ok", "disabled", "fault"]
TelemetryStatus = Literal["reported", "not_reported"]

# Identifier formats.
EmployeeId = constrained_str(5, 5, r"^E[0-9]{4}$")
DeviceId = constrained_str(5, 5, r"^D[0-9]{4}$")
TicketId = constrained_str(8, 8, r"^TCK-[0-9]{4}$")
OutageId = constrained_str(7, 7, r"^OUT-[0-9]{3}$")
RegionId = constrained_str(2, 30, r"^[a-z][a-z-]*$")
DocumentId = constrained_str(6, 6, r"^KB-[0-9]{3}$")
DocumentVersion = constrained_str(3, 10, r"^[0-9]+[.][0-9]+$")
ChunkId = constrained_str(8, 10, r"^KB-[0-9]{3}#[0-9]{1,3}$")
PreviewId = constrained_str(36, 36, r"^prv_[0-9a-f]{32}$")
RequestId = constrained_str(8, 64, r"^[A-Za-z0-9_-]+$")
UtcTimestamp = constrained_str(
    20, 20, r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)

# Ticket text limits from the project brief.
TicketSummary = constrained_str(5, 120)
TicketDescription = constrained_str(10, 2000)

Percent = Annotated[int, Field(strict=True, ge=0, le=100)]
