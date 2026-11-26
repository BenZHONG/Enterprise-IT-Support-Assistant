"""What tools return. Each model carries only the fields a caller needs.

Deliberately absent:
- TicketResult has no requester ID and no description (ticket text is
  untrusted; list views show the summary only).
- DeviceResult has no owner ID.
- ProfileResult has no email address.
"""

from typing import Literal

from pydantic import Field, model_validator

from assistant_app.schemas.base import (
    ChunkId,
    DeviceId,
    DeviceStatus,
    DocumentId,
    DocumentVersion,
    EmployeeId,
    OutageId,
    OutageService,
    OutageSeverity,
    OutageStatus,
    Percent,
    PreviewId,
    RegionId,
    Role,
    StrictModel,
    TelemetryStatus,
    TicketCategory,
    TicketDescription,
    TicketId,
    TicketPriority,
    TicketStatus,
    TicketSummary,
    UtcTimestamp,
    WifiAdapterState,
    constrained_str,
)

# ----- identity and profile -----


class UserCheckResult(StrictModel):
    employee_id: EmployeeId
    exists: bool
    active: bool

    @model_validator(mode="after")
    def _active_needs_existing_account(self):
        if self.active and not self.exists:
            raise ValueError("an account that does not exist cannot be active")
        return self


class ProfileResult(StrictModel):
    employee_id: EmployeeId
    full_name: constrained_str(1, 100)
    department: constrained_str(1, 60)
    region_id: RegionId
    role: Role


# ----- devices -----


class DeviceTelemetryResult(StrictModel):
    last_reported: UtcTimestamp
    wifi_adapter: WifiAdapterState
    wifi_connected: bool
    signal_percent: Percent | None
    battery_health_percent: Percent | None


class DeviceResult(StrictModel):
    device_id: DeviceId
    asset_tag: constrained_str(1, 30)
    device_type: constrained_str(1, 30)
    model: constrained_str(1, 60)
    os: constrained_str(1, 40)
    status: DeviceStatus
    # "not_reported" means we have no data. It does NOT mean the device is broken.
    telemetry_status: TelemetryStatus
    telemetry: DeviceTelemetryResult | None

    @model_validator(mode="after")
    def _status_matches_telemetry(self):
        if (self.telemetry is None) != (self.telemetry_status == "not_reported"):
            raise ValueError("telemetry_status does not match telemetry")
        return self


class DeviceCheckResult(StrictModel):
    devices: tuple[DeviceResult, ...] = Field(default=(), max_length=10)


# ----- tickets -----


class TicketResult(StrictModel):
    ticket_id: TicketId
    summary: TicketSummary
    status: TicketStatus
    priority: TicketPriority
    category: TicketCategory
    created_at: UtcTimestamp
    updated_at: UtcTimestamp


class TicketListResult(StrictModel):
    status_filter: TicketStatus | None = None
    tickets: tuple[TicketResult, ...] = Field(default=(), max_length=50)


class TicketStatusResult(StrictModel):
    ticket_id: TicketId
    status: TicketStatus
    updated_at: UtcTimestamp


class TicketPreview(StrictModel):
    """A proposed ticket. Showing a preview never writes anything."""

    preview_id: PreviewId
    summary: TicketSummary
    description: TicketDescription
    expires_at: UtcTimestamp
    requires_confirmation: Literal[True] = True


# ----- outages -----


class OutageResult(StrictModel):
    outage_id: OutageId
    region_id: RegionId
    service: OutageService
    severity: OutageSeverity
    status: OutageStatus
    title: constrained_str(1, 120)
    message: constrained_str(1, 500)
    started_at: UtcTimestamp
    resolved_at: UtcTimestamp | None

    @model_validator(mode="after")
    def _resolved_at_matches_status(self):
        if self.status == "active" and self.resolved_at is not None:
            raise ValueError("an active outage cannot have resolved_at")
        if self.status == "resolved" and self.resolved_at is None:
            raise ValueError("a resolved outage needs resolved_at")
        return self


class OutageCheckResult(StrictModel):
    region_id: RegionId
    has_active_outage: bool
    outages: tuple[OutageResult, ...] = Field(default=(), max_length=20)

    @model_validator(mode="after")
    def _flag_matches_outages(self):
        if self.has_active_outage != any(o.status == "active" for o in self.outages):
            raise ValueError("has_active_outage does not match the outages")
        return self


# ----- knowledge base -----


class Citation(StrictModel):
    """Where a piece of advice came from. Carried through retrieval in Stage 9+."""

    source_id: DocumentId
    title: constrained_str(1, 100)
    version: DocumentVersion
    chunk_id: ChunkId

    @model_validator(mode="after")
    def _chunk_belongs_to_source(self):
        if not self.chunk_id.startswith(self.source_id + "#"):
            raise ValueError("chunk_id does not belong to source_id")
        return self


class KnowledgeExcerpt(Citation):
    text: constrained_str(1, 1500)


class KnowledgeSearchResult(StrictModel):
    excerpts: tuple[KnowledgeExcerpt, ...] = Field(default=(), max_length=5)
