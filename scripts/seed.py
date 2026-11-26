"""Seed command: python -m scripts.seed

Stage 3 validates the fictional data in memory and prints a summary.
Stage 6 extends this same command to write the data into SQLite.
Running it repeatedly always gives the same result.
"""

from assistant_app.rag.documents import KnowledgeBaseError, load_documents
from assistant_app.roles import ROLE_EMPLOYEE
from mock_itsm import seed_data
from mock_itsm.seed_data import SeedDataError, validate_seed_data


def main() -> int:
    try:
        validate_seed_data()
        documents = load_documents()
    except (SeedDataError, KnowledgeBaseError) as exc:
        print(f"Seed check failed:\n{exc}")
        return 1

    restricted = sum(1 for d in documents if ROLE_EMPLOYEE not in d.allowed_roles)
    print(
        "Seed data check passed (Stage 3 checks the data in memory; Stage 6 will write it to SQLite)."
    )
    print(f"  regions:   {len(seed_data.REGIONS)}")
    print(f"  employees: {len(seed_data.EMPLOYEES)}")
    print(f"  devices:   {len(seed_data.DEVICES)}")
    print(f"  tickets:   {len(seed_data.TICKETS)}")
    print(f"  outages:   {len(seed_data.OUTAGES)}")
    print(
        f"  knowledge documents: {len(documents)} ({restricted} restricted to IT staff)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
