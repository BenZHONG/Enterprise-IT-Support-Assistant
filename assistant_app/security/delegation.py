"""Delegated support access.

Why it exists: an IT Support Agent has no standing access to other
people's tickets, devices, or profiles. To help someone, an agent needs
a grant that an IT Administrator creates. A grant is:
- for one agent and one employee,
- limited to named read scopes (tickets:read, devices:read, profile:read),
- time-limited (1 to 60 minutes),
- revocable at any time, and
- recorded with who created it (audited in Stage 17).
Grants cover reads only. Nothing here lets anyone write as someone else.
"""

import re
import threading
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from assistant_app.security.authn import EmployeeDirectory
from assistant_app.security.authorization import require_permission, resolve_now
from assistant_app.security.context import EmployeeContext
from assistant_app.security.errors import ServiceError
from assistant_app.security.permissions import Permission

DELEGABLE_SCOPES = frozenset({"tickets:read", "devices:read", "profile:read"})
MAX_GRANT_MINUTES = 60
_EMPLOYEE_ID_RE = re.compile(r"^E[0-9]{4}$")


@dataclass(frozen=True)
class AccessGrant:
    grant_id: str
    agent_id: str
    employee_id: str
    scopes: frozenset[str]
    created_by: str
    expires_at: datetime


class GrantStore:
    """In-memory store. A production system would persist grants in a database."""

    def __init__(self) -> None:
        self._grants: dict[str, AccessGrant] = {}
        self._lock = threading.Lock()

    def add(self, grant: AccessGrant) -> None:
        with self._lock:
            self._grants[grant.grant_id] = grant

    def revoke(self, grant_id: str) -> bool:
        with self._lock:
            return self._grants.pop(grant_id, None) is not None

    def has_active_grant(
        self, agent_id: str, employee_id: str, scope: str, now: datetime
    ) -> bool:
        with self._lock:
            return any(
                g.agent_id == agent_id
                and g.employee_id == employee_id
                and scope in g.scopes
                and now < g.expires_at  # a grant is NOT valid at its expiry instant
                for g in self._grants.values()
            )


def grant_access(
    ctx: EmployeeContext | None,
    store: GrantStore,
    directory: EmployeeDirectory,
    *,
    agent_id: str,
    employee_id: str,
    scopes: Iterable[str],
    minutes: int,
    now: datetime | None = None,
) -> AccessGrant:
    """Create a delegated grant. Only IT Administrators may do this."""
    when = resolve_now(now)
    require_permission(ctx, Permission.GRANTS_MANAGE)
    assert ctx is not None  # require_permission raised if it was None

    if (
        not isinstance(agent_id, str)
        or not isinstance(employee_id, str)
        or not _EMPLOYEE_ID_RE.match(agent_id)
        or not _EMPLOYEE_ID_RE.match(employee_id)
        or agent_id == employee_id
    ):
        raise ServiceError("validation_error")
    if (
        isinstance(minutes, bool)
        or not isinstance(minutes, int)
        or not 1 <= minutes <= MAX_GRANT_MINUTES
    ):
        raise ServiceError("validation_error")
    scope_set = frozenset(scopes)
    if not scope_set or not scope_set <= DELEGABLE_SCOPES:
        raise ServiceError("validation_error")

    agent = directory.get_employee(agent_id)
    if agent is None or not agent.active or agent.role != "it_support_agent":
        raise ServiceError("validation_error")
    employee = directory.get_employee(employee_id)
    if employee is None or not employee.active:
        raise ServiceError("not_found")

    grant = AccessGrant(
        grant_id="grt_" + uuid.uuid4().hex,
        agent_id=agent_id,
        employee_id=employee_id,
        scopes=scope_set,
        created_by=ctx.employee_id,
        expires_at=when + timedelta(minutes=minutes),
    )
    store.add(grant)
    return grant


def revoke_access(
    ctx: EmployeeContext | None, store: GrantStore, grant_id: str
) -> None:
    require_permission(ctx, Permission.GRANTS_MANAGE)
    if not store.revoke(grant_id):
        raise ServiceError("not_found")
