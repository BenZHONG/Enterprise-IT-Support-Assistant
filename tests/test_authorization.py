from datetime import UTC, datetime, timedelta

import pytest

from assistant_app.rag.documents import load_documents
from assistant_app.schemas.errors import new_request_id
from assistant_app.security.authorization import (
    authorize_read,
    can_read_document,
    require_permission,
)
from assistant_app.security.context import EmployeeContext
from assistant_app.security.delegation import AccessGrant, GrantStore
from assistant_app.security.errors import ServiceError
from assistant_app.security.permissions import Permission
from mock_itsm.seed_data import TICKETS
from scripts.demo_wiring import SeedEmployeeDirectory

DIRECTORY = SeedEmployeeDirectory()
NOW = datetime(2026, 11, 27, 1, 0, tzinfo=UTC)


def context(employee_id):
    return EmployeeContext.from_record(DIRECTORY.get_employee(employee_id))


PRIYA, MEI = context("E1001"), context("E1003")
AISHA, TOM, DANIEL = context("E1005"), context("E1006"), context("E1008")


def ticket_owner(ticket_id):
    """Stands in for the Stage 8 lookup: owner ID, or None if there is no such ticket."""
    return next((t.requester_id for t in TICKETS if t.ticket_id == ticket_id), None)


def expect_error(code, function, *args, **kwargs):
    with pytest.raises(ServiceError) as info:
        function(*args, **kwargs)
    assert info.value.code == code
    return info.value


def make_grant(agent="E1005", employee="E1001", scopes=("tickets:read",), minutes=15):
    return AccessGrant(
        "grt_test",
        agent,
        employee,
        frozenset(scopes),
        "E1006",
        NOW + timedelta(minutes=minutes),
    )


# ----- capability checks -----


def test_require_permission_needs_a_signed_in_user():
    expect_error(
        "authentication_required", require_permission, None, Permission.TICKETS_READ_OWN
    )


def test_require_permission_refuses_a_missing_capability():
    expect_error(
        "permission_denied", require_permission, PRIYA, Permission.GRANTS_MANAGE
    )


def test_require_permission_allows_a_held_capability():
    assert require_permission(TOM, Permission.GRANTS_MANAGE) is None


def test_inactive_account_is_denied_even_its_own_permissions():
    expect_error(
        "permission_denied", require_permission, DANIEL, Permission.TICKETS_READ_OWN
    )


# ----- resource ownership -----


def test_employee_can_read_their_own_ticket():
    assert authorize_read(PRIYA, "ticket", ticket_owner("TCK-1001")) == "own"


def test_employee_can_read_their_own_device_and_profile():
    assert authorize_read(PRIYA, "device", "E1001") == "own"
    assert authorize_read(PRIYA, "profile", "E1001") == "own"


def test_employee_cannot_read_someone_elses_ticket():
    expect_error("not_found", authorize_read, PRIYA, "ticket", ticket_owner("TCK-1006"))


def test_someone_elses_ticket_looks_exactly_like_a_missing_ticket():
    other_persons = expect_error(
        "not_found", authorize_read, PRIYA, "ticket", ticket_owner("TCK-1006")
    )
    missing = expect_error(
        "not_found", authorize_read, PRIYA, "ticket", ticket_owner("TCK-9999")
    )
    request_id = new_request_id()
    assert other_persons.to_response(request_id) == missing.to_response(request_id)


@pytest.mark.parametrize("kind", ["ticket", "device", "profile"])
def test_employee_cannot_read_another_employees_resources(kind):
    expect_error("not_found", authorize_read, PRIYA, kind, "E1003")


def test_missing_sign_in_is_authentication_required():
    expect_error("authentication_required", authorize_read, None, "ticket", "E1001")


def test_inactive_employee_is_denied_even_for_their_own_resources():
    expect_error("permission_denied", authorize_read, DANIEL, "profile", "E1008")


@pytest.mark.parametrize("kind", ["ticket", "device", "profile"])
def test_administrator_can_read_anyones_resources(kind):
    assert authorize_read(TOM, kind, "E1003") == "admin"


def test_unknown_resource_kind_is_an_internal_error():
    expect_error("internal_error", authorize_read, PRIYA, "spaceship", "E1001")


def test_naive_datetimes_are_rejected():
    with pytest.raises(ValueError):
        authorize_read(PRIYA, "ticket", "E1001", None, datetime(2026, 11, 27))


# ----- delegated access -----


def test_agent_without_a_grant_cannot_read_other_peoples_resources():
    expect_error(
        "not_found", authorize_read, AISHA, "ticket", "E1001", GrantStore(), NOW
    )


def test_agent_with_an_active_grant_can_read():
    store = GrantStore()
    store.add(make_grant())
    assert authorize_read(AISHA, "ticket", "E1001", store, NOW) == "delegation"


def test_grant_for_one_employee_does_not_cover_another():
    store = GrantStore()
    store.add(make_grant(employee="E1001"))
    expect_error("not_found", authorize_read, AISHA, "ticket", "E1003", store, NOW)


def test_grant_scope_limits_what_can_be_read():
    store = GrantStore()
    store.add(make_grant(scopes=("tickets:read",)))
    expect_error("not_found", authorize_read, AISHA, "device", "E1001", store, NOW)


@pytest.mark.parametrize(
    ("offset_seconds", "allowed"),
    [(-1, True), (0, False), (1, False)],  # relative to the expiry instant
)
def test_grant_stops_working_at_its_expiry(offset_seconds, allowed):
    store = GrantStore()
    store.add(make_grant(minutes=15))
    moment = NOW + timedelta(minutes=15, seconds=offset_seconds)
    if allowed:
        assert authorize_read(AISHA, "ticket", "E1001", store, moment) == "delegation"
    else:
        expect_error(
            "not_found", authorize_read, AISHA, "ticket", "E1001", store, moment
        )


def test_revoked_grant_stops_working():
    store = GrantStore()
    store.add(make_grant())
    assert store.revoke("grt_test") is True
    expect_error("not_found", authorize_read, AISHA, "ticket", "E1001", store, NOW)


def test_an_employee_cannot_use_a_grant_even_if_one_names_them():
    store = GrantStore()
    store.add(make_grant(agent="E1001", employee="E1003"))
    expect_error("not_found", authorize_read, PRIYA, "ticket", "E1003", store, NOW)


# ----- document-level access -----


def test_employee_cannot_read_the_staff_only_runbook():
    documents = load_documents()
    visible = {d.doc_id for d in documents if can_read_document(PRIYA, d.allowed_roles)}
    assert "KB-001" in visible
    assert "KB-007" not in visible


def test_support_agent_can_read_the_staff_only_runbook():
    documents = load_documents()
    visible = {d.doc_id for d in documents if can_read_document(AISHA, d.allowed_roles)}
    assert "KB-007" in visible


def test_nobody_reads_documents_when_signed_out_or_inactive():
    documents = load_documents()
    assert not any(can_read_document(None, d.allowed_roles) for d in documents)
    assert not any(can_read_document(DANIEL, d.allowed_roles) for d in documents)


# ----- error shape -----


@pytest.mark.parametrize(
    "code", ["authentication_required", "permission_denied", "not_found"]
)
def test_service_errors_use_the_standard_error_shape(code):
    response = ServiceError(code).to_response(new_request_id())
    assert response.code == code
    assert response.retryable is False
    assert response.message
