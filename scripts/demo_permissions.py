"""Demo: python -m scripts.demo_permissions

Runs eight access decisions against the fictional data. It needs no tokens.
"""

from datetime import UTC, datetime

from assistant_app.security.delegation import GrantStore, grant_access

from assistant_app.security.authorization import authorize_read
from assistant_app.security.context import EmployeeContext
from assistant_app.security.errors import ServiceError
from mock_itsm import seed_data
from scripts.demo_wiring import SeedEmployeeDirectory

NOW = datetime(2026, 11, 27, 1, 0, tzinfo=UTC)


def main() -> int:
    directory = SeedEmployeeDirectory()

    def context(employee_id: str) -> EmployeeContext:
        return EmployeeContext.from_record(directory.get_employee(employee_id))

    priya, aisha = context("E1001"), context("E1005")
    tom, daniel = context("E1006"), context("E1008")
    owners = {t.ticket_id: t.requester_id for t in seed_data.TICKETS}
    store = GrantStore()

    def attempt(label, actor, kind, owner_id):
        try:
            result = f"allowed ({authorize_read(actor, kind, owner_id, store, NOW)})"
        except ServiceError as exc:
            result = f"denied: {exc.code}"
        print(f"{label} -> {result}")

    attempt(
        "Priya (employee) reads her own ticket TCK-1001",
        priya,
        "ticket",
        owners.get("TCK-1001"),
    )
    attempt(
        "Priya reads Mei's ticket TCK-1006", priya, "ticket", owners.get("TCK-1006")
    )
    attempt(
        "Priya reads a ticket that does not exist, TCK-9999",
        priya,
        "ticket",
        owners.get("TCK-9999"),
    )
    attempt(
        "Aisha (support agent) reads TCK-1001 with no grant",
        aisha,
        "ticket",
        owners.get("TCK-1001"),
    )

    grant_access(
        tom,
        store,
        directory,
        agent_id="E1005",
        employee_id="E1001",
        scopes=["tickets:read"],
        minutes=15,
        now=NOW,
    )
    attempt(
        "Aisha reads TCK-1001 after a 15-minute grant",
        aisha,
        "ticket",
        owners.get("TCK-1001"),
    )
    attempt(
        "Tom (administrator) reads Mei's ticket TCK-1006",
        tom,
        "ticket",
        owners.get("TCK-1006"),
    )
    attempt(
        "Daniel (inactive employee) reads his own profile", daniel, "profile", "E1008"
    )
    attempt(
        "Nobody is signed in, request for TCK-1001",
        None,
        "ticket",
        owners.get("TCK-1001"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
