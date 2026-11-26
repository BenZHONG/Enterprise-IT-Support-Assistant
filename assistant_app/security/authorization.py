"""Authorization rules, enforced in the service layer.

Error rules (consistent everywhere):
- no valid sign-in                          -> authentication_required
- inactive account, or role lacks the
  capability itself                         -> permission_denied
- resource missing, OR owned by someone
  the caller may not access                 -> not_found (identical text)
Returning not_found for other people's resources means a caller cannot
discover which ticket IDs exist.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Literal, Protocol

from assistant_app.security.context import EmployeeContext
from assistant_app.security.errors import ServiceError
from assistant_app.security.permissions import Permission, permissions_for

ResourceKind = Literal["ticket", "device", "profile"]
AccessBasis = Literal["own", "admin", "delegation"]


@dataclass(frozen=True)
class _Rule:
    own: Permission
    any_: Permission
    scope: str  # the delegation scope that covers this resource


_RULES = MappingProxyType(
    {
        "ticket": _Rule(
            Permission.TICKETS_READ_OWN, Permission.TICKETS_READ_ANY, "tickets:read"
        ),
        "device": _Rule(
            Permission.DEVICES_READ_OWN, Permission.DEVICES_READ_ANY, "devices:read"
        ),
        "profile": _Rule(
            Permission.PROFILE_READ_OWN, Permission.PROFILE_READ_ANY, "profile:read"
        ),
    }
)


class GrantLookup(Protocol):
    def has_active_grant(
        self, agent_id: str, employee_id: str, scope: str, now: datetime
    ) -> bool: ...


def resolve_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return now


def require_permission(ctx: EmployeeContext | None, permission: Permission) -> None:
    """Check a capability that is not about one specific resource."""
    if ctx is None:
        raise ServiceError("authentication_required")
    if not ctx.active or permission not in permissions_for(ctx.role):
        raise ServiceError("permission_denied")


def authorize_read(
    ctx: EmployeeContext | None,
    kind: ResourceKind,
    owner_id: str | None,
    grants: GrantLookup | None = None,
    now: datetime | None = None,
) -> AccessBasis:
    """Decide whether ctx may read one resource.

    owner_id is the owner of the resource, or None if the resource does
    not exist. Returns why access was allowed, which Stage 17 audits."""
    when = resolve_now(now)
    if ctx is None:
        raise ServiceError("authentication_required")
    if not ctx.active:
        raise ServiceError("permission_denied")
    rule = _RULES.get(kind)
    if rule is None:
        raise ServiceError("internal_error")
    if owner_id is None:
        raise ServiceError("not_found")

    permissions = permissions_for(ctx.role)
    if owner_id == ctx.employee_id:
        if rule.own not in permissions:
            raise ServiceError("permission_denied")
        return "own"
    if rule.any_ in permissions:
        return "admin"
    if (
        grants is not None
        and Permission.SUPPORT_DELEGATED_ACCESS in permissions
        and grants.has_active_grant(ctx.employee_id, owner_id, rule.scope, when)
    ):
        return "delegation"
    raise ServiceError("not_found")


def can_read_document(
    ctx: EmployeeContext | None, allowed_roles: Iterable[str]
) -> bool:
    """Document-level rule: the role must be in the document's allowed_roles.
    Stage 10 applies this BEFORE any excerpt reaches the model."""
    return ctx is not None and ctx.active and ctx.role in set(allowed_roles)
