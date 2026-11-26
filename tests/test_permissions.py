from types import MappingProxyType

import pytest

from assistant_app.roles import (
    ALL_ROLES,
    ROLE_EMPLOYEE,
    ROLE_IT_ADMINISTRATOR,
    ROLE_IT_SUPPORT_AGENT,
)
from assistant_app.security.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    permissions_for,
)

P = Permission


def test_every_role_has_a_permission_set_and_unknown_roles_get_nothing():
    assert set(ROLE_PERMISSIONS) == set(ALL_ROLES)
    assert permissions_for("wizard") == frozenset()
    assert permissions_for("") == frozenset()


@pytest.mark.parametrize(
    "permission",
    [
        P.TICKETS_READ_ANY,
        P.DEVICES_READ_ANY,
        P.PROFILE_READ_ANY,
        P.OUTAGES_READ_ANY_REGION,
        P.SUPPORT_DELEGATED_ACCESS,
        P.GRANTS_MANAGE,
    ],
)
def test_employee_has_no_staff_permissions(permission):
    assert permission not in permissions_for(ROLE_EMPLOYEE)


def test_employee_can_use_only_their_own_resources():
    assert permissions_for(ROLE_EMPLOYEE) == {
        P.TICKETS_READ_OWN,
        P.TICKETS_PREVIEW_OWN,
        P.TICKETS_CREATE_OWN,
        P.DEVICES_READ_OWN,
        P.PROFILE_READ_OWN,
        P.OUTAGES_READ_OWN_REGION,
        P.KNOWLEDGE_READ,
    }


@pytest.mark.parametrize(
    "permission",
    [P.TICKETS_READ_ANY, P.DEVICES_READ_ANY, P.PROFILE_READ_ANY, P.GRANTS_MANAGE],
)
def test_agent_has_no_standing_access_to_other_peoples_data(permission):
    assert permission not in permissions_for(ROLE_IT_SUPPORT_AGENT)


def test_agent_can_see_all_regions_and_use_grants():
    agent = permissions_for(ROLE_IT_SUPPORT_AGENT)
    assert {P.OUTAGES_READ_ANY_REGION, P.SUPPORT_DELEGATED_ACCESS} <= agent
    assert permissions_for(ROLE_EMPLOYEE) <= agent


def test_administrator_can_read_anything_and_manage_grants():
    admin = permissions_for(ROLE_IT_ADMINISTRATOR)
    assert {
        P.TICKETS_READ_ANY,
        P.DEVICES_READ_ANY,
        P.PROFILE_READ_ANY,
        P.OUTAGES_READ_ANY_REGION,
        P.GRANTS_MANAGE,
    } <= admin


def test_permission_table_is_read_only():
    assert isinstance(ROLE_PERMISSIONS, MappingProxyType)
    with pytest.raises(TypeError):
        ROLE_PERMISSIONS["employee"] = frozenset()


def test_permission_names_are_stable_strings():
    assert P.TICKETS_READ_OWN == "tickets:read_own"
    assert P.GRANTS_MANAGE == "grants:manage"
