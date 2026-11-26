"""Roles and their permissions. Anything not listed here is denied.

Employee           own tickets, devices, profile, own-region outages, knowledge.
IT Support Agent   same as Employee, plus outages in any region, plus the
                   ability to use a delegated grant (see delegation.py).
                   An agent has NO standing access to other people's data.
IT Administrator   same as Employee, plus outages in any region, plus read
                   access to any ticket, device, or profile, plus managing
                   delegated grants.

Document-level rules (allowed_roles in each knowledge document) are
applied separately by can_read_document() in authorization.py.
"""

from enum import StrEnum
from types import MappingProxyType

from assistant_app.roles import (
    ROLE_EMPLOYEE,
    ROLE_IT_ADMINISTRATOR,
    ROLE_IT_SUPPORT_AGENT,
)


class Permission(StrEnum):
    TICKETS_READ_OWN = "tickets:read_own"
    TICKETS_PREVIEW_OWN = "tickets:preview_own"
    TICKETS_CREATE_OWN = "tickets:create_own"
    TICKETS_READ_ANY = "tickets:read_any"
    DEVICES_READ_OWN = "devices:read_own"
    DEVICES_READ_ANY = "devices:read_any"
    PROFILE_READ_OWN = "profile:read_own"
    PROFILE_READ_ANY = "profile:read_any"
    OUTAGES_READ_OWN_REGION = "outages:read_own_region"
    OUTAGES_READ_ANY_REGION = "outages:read_any_region"
    KNOWLEDGE_READ = "knowledge:read"
    SUPPORT_DELEGATED_ACCESS = "support:delegated_access"
    GRANTS_MANAGE = "grants:manage"


_EMPLOYEE = frozenset(
    {
        Permission.TICKETS_READ_OWN,
        Permission.TICKETS_PREVIEW_OWN,
        Permission.TICKETS_CREATE_OWN,
        Permission.DEVICES_READ_OWN,
        Permission.PROFILE_READ_OWN,
        Permission.OUTAGES_READ_OWN_REGION,
        Permission.KNOWLEDGE_READ,
    }
)

_AGENT = _EMPLOYEE | {
    Permission.OUTAGES_READ_ANY_REGION,
    Permission.SUPPORT_DELEGATED_ACCESS,
}

_ADMINISTRATOR = _EMPLOYEE | {
    Permission.OUTAGES_READ_ANY_REGION,
    Permission.TICKETS_READ_ANY,
    Permission.DEVICES_READ_ANY,
    Permission.PROFILE_READ_ANY,
    Permission.GRANTS_MANAGE,
}

# MappingProxyType makes the table read-only at run time.
ROLE_PERMISSIONS = MappingProxyType(
    {
        ROLE_EMPLOYEE: _EMPLOYEE,
        ROLE_IT_SUPPORT_AGENT: frozenset(_AGENT),
        ROLE_IT_ADMINISTRATOR: frozenset(_ADMINISTRATOR),
    }
)


def permissions_for(role: str) -> frozenset[Permission]:
    """Unknown roles get nothing (deny by default)."""
    return ROLE_PERMISSIONS.get(role, frozenset())
