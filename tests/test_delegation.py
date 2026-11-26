from datetime import UTC, datetime, timedelta

import pytest

from assistant_app.security.authorization import authorize_read
from assistant_app.security.context import EmployeeContext
from assistant_app.security.delegation import GrantStore, grant_access, revoke_access
from assistant_app.security.errors import ServiceError
from scripts.demo_wiring import SeedEmployeeDirectory

DIRECTORY = SeedEmployeeDirectory()
NOW = datetime(2026, 11, 27, 1, 0, tzinfo=UTC)


def context(employee_id):
    return EmployeeContext.from_record(DIRECTORY.get_employee(employee_id))


PRIYA, AISHA, TOM = context("E1001"), context("E1005"), context("E1006")


def do_grant(actor=TOM, store=None, **overrides):
    arguments = {
        "agent_id": "E1005",
        "employee_id": "E1001",
        "scopes": ["tickets:read"],
        "minutes": 15,
        "now": NOW,
    }
    arguments.update(overrides)
    return grant_access(
        actor, store if store is not None else GrantStore(), DIRECTORY, **arguments
    )


BAD_REQUESTS = [
    {"minutes": 0},
    {"minutes": 61},
    {"minutes": True},
    {"minutes": "10"},
    {"scopes": []},
    {"scopes": ["tickets:write"]},
    {"agent_id": "E1001"},  # an employee is not a support agent
    {"agent_id": "E1006"},  # an administrator is not a support agent
    {"agent_id": "alice"},
    {"employee_id": "E1005"},  # an agent cannot be granted access to themselves
]


def test_administrator_creates_a_grant():
    store = GrantStore()
    grant = do_grant(store=store)
    assert grant.grant_id.startswith("grt_")
    assert (grant.agent_id, grant.employee_id) == ("E1005", "E1001")
    assert grant.scopes == frozenset({"tickets:read"})
    assert grant.created_by == "E1006"
    assert grant.expires_at == NOW + timedelta(minutes=15)
    assert store.has_active_grant("E1005", "E1001", "tickets:read", NOW)
    assert not store.has_active_grant(
        "E1005", "E1001", "tickets:read", grant.expires_at
    )


@pytest.mark.parametrize("actor", [PRIYA, AISHA])
def test_only_administrators_can_create_grants(actor):
    with pytest.raises(ServiceError) as info:
        do_grant(actor=actor)
    assert info.value.code == "permission_denied"


def test_creating_a_grant_requires_sign_in():
    with pytest.raises(ServiceError) as info:
        do_grant(actor=None)
    assert info.value.code == "authentication_required"


@pytest.mark.parametrize("overrides", BAD_REQUESTS, ids=str)
def test_invalid_grant_requests_are_rejected(overrides):
    with pytest.raises(ServiceError) as info:
        do_grant(**overrides)
    assert info.value.code == "validation_error"


@pytest.mark.parametrize("employee_id", ["E9999", "E1008"])  # missing, inactive
def test_grant_for_a_missing_or_inactive_employee_is_not_found(employee_id):
    with pytest.raises(ServiceError) as info:
        do_grant(employee_id=employee_id)
    assert info.value.code == "not_found"


def test_a_created_grant_lets_the_agent_read_that_employees_ticket():
    store = GrantStore()
    do_grant(store=store)
    assert authorize_read(AISHA, "ticket", "E1001", store, NOW) == "delegation"


def test_revoking_a_grant_removes_access():
    store = GrantStore()
    grant = do_grant(store=store)
    revoke_access(TOM, store, grant.grant_id)
    with pytest.raises(ServiceError) as info:
        authorize_read(AISHA, "ticket", "E1001", store, NOW)
    assert info.value.code == "not_found"


def test_revoking_an_unknown_grant_is_not_found():
    with pytest.raises(ServiceError) as info:
        revoke_access(TOM, GrantStore(), "grt_missing")
    assert info.value.code == "not_found"


def test_only_administrators_can_revoke_grants():
    store = GrantStore()
    grant = do_grant(store=store)
    with pytest.raises(ServiceError) as info:
        revoke_access(AISHA, store, grant.grant_id)
    assert info.value.code == "permission_denied"
