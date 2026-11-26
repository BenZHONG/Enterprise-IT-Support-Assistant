"""Trusted identity objects.

An EmployeeContext is built ONLY by the server, after a credential has
been verified, from the company directory. Nothing a user or a model
types can change one: it is frozen, and no tool argument model (Stage 4)
has a field for employee ID, role, or region.
"""

from dataclasses import dataclass

from assistant_app.roles import ALL_ROLES


@dataclass(frozen=True)
class EmployeeRecord:
    """What the employee directory returns about one person."""

    employee_id: str
    full_name: str
    role: str
    region_id: str
    active: bool


@dataclass(frozen=True)
class EmployeeContext:
    employee_id: str
    role: str
    region_id: str
    active: bool

    def __post_init__(self) -> None:
        if self.role not in ALL_ROLES:
            raise ValueError("unknown role")

    @classmethod
    def from_record(cls, record: EmployeeRecord) -> "EmployeeContext":
        return cls(record.employee_id, record.role, record.region_id, record.active)
