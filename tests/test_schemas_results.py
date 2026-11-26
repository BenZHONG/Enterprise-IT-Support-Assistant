import dataclasses
from typing import get_args

import pytest
from pydantic import ValidationError

from assistant_app.schemas import base
from assistant_app.schemas.results import (
    DeviceResult,
    DeviceTelemetryResult,
    KnowledgeSearchResult,
    OutageCheckResult,
    OutageResult,
    ProfileResult,
    TicketPreview,
    TicketResult,
    TicketStatusResult,
    UserCheckResult,
)
from mock_itsm import seed_data
from mock_itsm.seed_data import DEVICES, EMPLOYEES, OUTAGES, TICKETS

EXCERPT = {
    "source_id": "KB-001",
    "title": "Wi-Fi Troubleshooting",
    "version": "1.2",
    "chunk_id": "KB-001#03",
    "text": "Turn Wi-Fi off and on again.",
}


def pick(record, model, **extra):
    """Build a result model from a seed record, keeping only the fields the
    result model defines. This is how Stage 8 tools will shape their output."""
    data = {
        k: v for k, v in dataclasses.asdict(record).items() if k in model.model_fields
    }
    data.update(extra)
    return model.model_validate(data)


def device_result(device):
    status = "reported" if device.telemetry else "not_reported"
    return pick(device, DeviceResult, telemetry_status=status)


def test_allowed_values_match_the_seed_data():
    assert set(get_args(base.Role)) == set(seed_data.ROLES)
    assert set(get_args(base.TicketStatus)) == set(seed_data.TICKET_STATUSES)
    assert set(get_args(base.TicketPriority)) == set(seed_data.TICKET_PRIORITIES)
    assert set(get_args(base.TicketCategory)) == set(seed_data.TICKET_CATEGORIES)
    assert set(get_args(base.OutageStatus)) == set(seed_data.OUTAGE_STATUSES)
    assert set(get_args(base.OutageSeverity)) == set(seed_data.OUTAGE_SEVERITIES)
    assert set(get_args(base.OutageService)) == set(seed_data.OUTAGE_SERVICES)
    assert set(get_args(base.DeviceStatus)) == set(seed_data.DEVICE_STATUSES)
    assert set(get_args(base.WifiAdapterState)) == set(seed_data.WIFI_ADAPTER_STATES)


# ----- tickets -----


def test_every_seed_ticket_fits_the_result_model():
    results = [pick(t, TicketResult) for t in TICKETS]
    assert len(results) == len(TICKETS)


def test_ticket_result_hides_requester_and_description():
    assert "requester_id" not in TicketResult.model_fields
    assert "description" not in TicketResult.model_fields


# ----- devices -----


def test_every_seed_device_fits_the_result_model():
    results = [device_result(d) for d in DEVICES]
    assert len(results) == len(DEVICES)


def test_missing_telemetry_is_not_reported_as_a_fault():
    by_id = {d.device_id: device_result(d) for d in DEVICES}
    never_reported = by_id["D2002"]
    assert never_reported.telemetry is None
    assert never_reported.telemetry_status == "not_reported"
    faulty = by_id["D2003"]
    assert faulty.telemetry is not None
    assert faulty.telemetry.wifi_adapter == "fault"


def test_telemetry_status_must_match_telemetry():
    healthy = next(d for d in DEVICES if d.telemetry is not None)
    with pytest.raises(ValidationError):
        pick(healthy, DeviceResult, telemetry_status="not_reported")
    never_reported = next(d for d in DEVICES if d.telemetry is None)
    with pytest.raises(ValidationError):
        pick(never_reported, DeviceResult, telemetry_status="reported")


def test_device_result_hides_the_owner():
    assert "owner_id" not in DeviceResult.model_fields


def test_percent_out_of_range_is_rejected():
    data = {
        "last_reported": "2026-11-26T08:45:00Z",
        "wifi_adapter": "ok",
        "wifi_connected": True,
        "signal_percent": 101,
        "battery_health_percent": 90,
    }
    with pytest.raises(ValidationError):
        DeviceTelemetryResult.model_validate(data)


# ----- outages -----


def test_every_seed_outage_fits_the_result_model():
    results = [pick(o, OutageResult) for o in OUTAGES]
    assert len(results) == len(OUTAGES)


def test_outage_status_and_resolved_at_must_agree():
    active = next(o for o in OUTAGES if o.status == "active")
    resolved = next(o for o in OUTAGES if o.status == "resolved")
    with pytest.raises(ValidationError):
        pick(active, OutageResult, resolved_at="2026-11-26T10:00:00Z")
    with pytest.raises(ValidationError):
        pick(resolved, OutageResult, resolved_at=None)


def test_outage_check_flag_must_match_the_outages():
    active = pick(next(o for o in OUTAGES if o.status == "active"), OutageResult)
    with pytest.raises(ValidationError):
        OutageCheckResult(
            region_id=active.region_id, has_active_outage=False, outages=(active,)
        )
    with pytest.raises(ValidationError):
        OutageCheckResult(region_id="sydney", has_active_outage=True, outages=())


def test_wifi_scenario_outage_check_for_parramatta():
    outages = tuple(
        pick(o, OutageResult) for o in OUTAGES if o.region_id == "parramatta"
    )
    result = OutageCheckResult(
        region_id="parramatta",
        has_active_outage=any(o.status == "active" for o in outages),
        outages=outages,
    )
    assert result.has_active_outage is True
    assert any(o.service == "corporate_wifi" for o in result.outages)


# ----- employees -----


def test_every_seed_employee_fits_the_profile_model():
    profiles = [pick(e, ProfileResult) for e in EMPLOYEES]
    assert len(profiles) == len(EMPLOYEES)
    assert "email" not in ProfileResult.model_fields


def test_user_check_covers_inactive_and_missing_accounts():
    assert (
        UserCheckResult(employee_id="E1008", exists=True, active=False).active is False
    )
    with pytest.raises(ValidationError):
        UserCheckResult(employee_id="E1008", exists=False, active=True)


# ----- knowledge excerpts -----


def test_valid_excerpt_is_accepted():
    result = KnowledgeSearchResult.model_validate({"excerpts": [EXCERPT]})
    assert result.excerpts[0].chunk_id == "KB-001#03"


@pytest.mark.parametrize("chunk_id", ["KB-001-3", "KB-1#1", "kb-001#1", "KB-001#"])
def test_bad_chunk_ids_are_rejected(chunk_id):
    with pytest.raises(ValidationError):
        KnowledgeSearchResult.model_validate(
            {"excerpts": [{**EXCERPT, "chunk_id": chunk_id}]}
        )


def test_chunk_must_belong_to_its_source():
    bad = {**EXCERPT, "source_id": "KB-002"}
    with pytest.raises(ValidationError):
        KnowledgeSearchResult.model_validate({"excerpts": [bad]})


def test_at_most_five_excerpts():
    with pytest.raises(ValidationError):
        KnowledgeSearchResult.model_validate({"excerpts": [EXCERPT] * 6})


# ----- ticket preview -----


def preview_data(**changes):
    data = {
        "preview_id": "prv_" + "a" * 32,
        "summary": "Laptop cannot join Wi-Fi",
        "description": "My laptop cannot join the company Wi-Fi.",
        "expires_at": "2026-11-26T09:30:00Z",
    }
    data.update(changes)
    return data


def test_valid_preview_requires_confirmation_by_default():
    assert TicketPreview.model_validate(preview_data()).requires_confirmation is True


def test_preview_cannot_claim_confirmation_is_not_needed():
    with pytest.raises(ValidationError):
        TicketPreview.model_validate(preview_data(requires_confirmation=False))


@pytest.mark.parametrize(
    "preview_id", ["prv_123", "PRV_" + "0" * 32, "prv_" + "g" * 32]
)
def test_bad_preview_ids_are_rejected(preview_id):
    with pytest.raises(ValidationError):
        TicketPreview.model_validate(preview_data(preview_id=preview_id))


# ----- general rules -----


def test_results_are_immutable():
    result = TicketStatusResult(
        ticket_id="TCK-1001", status="open", updated_at="2026-11-19T04:00:00Z"
    )
    with pytest.raises(ValidationError):
        result.status = "closed"


def test_results_reject_extra_fields():
    data = {
        "ticket_id": "TCK-1001",
        "status": "open",
        "updated_at": "2026-11-19T04:00:00Z",
        "requester_id": "E1001",
    }
    with pytest.raises(ValidationError):
        TicketStatusResult.model_validate(data)
