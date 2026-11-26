import dataclasses

import pytest

from assistant_app.roles import ALL_ROLES
from mock_itsm import seed_data
from mock_itsm.seed_data import (
    DEVICES,
    EMPLOYEES,
    OUTAGES,
    REGIONS,
    TICKETS,
    SeedDataError,
    validate_seed_data,
)
from scripts.seed import main as seed_main


def test_minimum_counts():
    assert len(EMPLOYEES) >= 5
    assert len(DEVICES) >= 5
    assert len(TICKETS) >= 10
    assert len(REGIONS) >= 3
    assert len(OUTAGES) >= 3


def test_seed_data_passes_validation():
    validate_seed_data()  # raises SeedDataError if anything is wrong


def test_all_emails_use_example_domain():
    assert all(e.email.endswith("@example.com") for e in EMPLOYEES)


def test_all_three_roles_are_present():
    assert {e.role for e in EMPLOYEES} == set(seed_data.ROLES)


def test_there_is_an_inactive_employee():
    assert any(not e.active for e in EMPLOYEES)


def test_every_ticket_has_an_existing_requester():
    employee_ids = {e.employee_id for e in EMPLOYEES}
    assert all(t.requester_id in employee_ids for t in TICKETS)


def test_every_device_has_an_existing_owner():
    employee_ids = {e.employee_id for e in EMPLOYEES}
    assert all(d.owner_id in employee_ids for d in DEVICES)


def test_device_telemetry_covers_healthy_missing_and_faulty():
    missing = [d for d in DEVICES if d.telemetry is None]
    faulty = [d for d in DEVICES if d.telemetry and d.telemetry.wifi_adapter == "fault"]
    healthy = [
        d
        for d in DEVICES
        if d.telemetry
        and d.telemetry.wifi_adapter == "ok"
        and d.telemetry.wifi_connected
    ]
    assert missing and faulty and healthy


def test_wifi_scenario_data_is_consistent():
    priya = next(e for e in EMPLOYEES if e.employee_id == "E1001")
    laptop = next(d for d in DEVICES if d.owner_id == "E1001")
    assert laptop.telemetry is not None
    assert laptop.telemetry.wifi_adapter == "ok"
    assert laptop.telemetry.wifi_connected is False
    assert any(
        o.region_id == priya.region_id
        and o.status == "active"
        and o.service == "corporate_wifi"
        for o in OUTAGES
    )


def test_outages_cover_active_resolved_and_a_clear_region():
    assert any(o.status == "active" for o in OUTAGES)
    assert any(o.status == "resolved" for o in OUTAGES)
    regions_with_active = {o.region_id for o in OUTAGES if o.status == "active"}
    assert {r.region_id for r in REGIONS} - regions_with_active


def test_roles_match_the_assistant_app():
    assert set(seed_data.ROLES) == set(ALL_ROLES)


def test_validation_rejects_unknown_ticket_owner():
    bad = dataclasses.replace(TICKETS[0], requester_id="E9999")
    with pytest.raises(SeedDataError, match="E9999"):
        validate_seed_data(tickets=(bad,) + TICKETS[1:])


def test_validation_rejects_bad_summary_length():
    bad = dataclasses.replace(TICKETS[0], summary="Hi")
    with pytest.raises(SeedDataError, match="summary"):
        validate_seed_data(tickets=(bad,) + TICKETS[1:])


def test_validation_rejects_duplicate_ids():
    with pytest.raises(SeedDataError, match="duplicate"):
        validate_seed_data(tickets=TICKETS + (TICKETS[0],))


def test_validation_rejects_inconsistent_outage_dates():
    active = next(o for o in OUTAGES if o.status == "active")
    bad = dataclasses.replace(active, resolved_at="2026-11-26T10:00:00Z")
    others = tuple(o for o in OUTAGES if o is not active)
    with pytest.raises(SeedDataError, match="resolved_at"):
        validate_seed_data(outages=others + (bad,))


def test_ticket_with_untrusted_instructions_exists():
    # Stage 18 relies on this deliberate prompt-injection test ticket.
    assert any(
        "ignore" in t.description.lower() and "ai assistant" in t.description.lower()
        for t in TICKETS
    )


def test_records_are_immutable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        EMPLOYEES[0].role = "it_administrator"


def test_seed_command_succeeds_and_is_repeatable(capsys):
    assert seed_main() == 0
    first = capsys.readouterr().out
    assert seed_main() == 0
    assert capsys.readouterr().out == first
    assert "passed" in first
