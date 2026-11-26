"""Demo wiring: connects the assistant's security code to the fictional data.

This is the ONLY place that joins assistant_app to mock_itsm. In Stage 6
the directory lookup becomes a call to the mock ITSM API, and this file
shrinks to configuration.
"""

from assistant_app.security.context import EmployeeRecord
from mock_itsm import seed_data


class SeedEmployeeDirectory:
    def __init__(self, employees=seed_data.EMPLOYEES) -> None:
        self._by_id = {e.employee_id: e for e in employees}

    def get_employee(self, employee_id: str) -> EmployeeRecord | None:
        employee = (
            self._by_id.get(employee_id) if isinstance(employee_id, str) else None
        )
        if employee is None:
            return None
        return EmployeeRecord(
            employee_id=employee.employee_id,
            full_name=employee.full_name,
            role=employee.role,
            region_id=employee.region_id,
            active=employee.active,
        )
