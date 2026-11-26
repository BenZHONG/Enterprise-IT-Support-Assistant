"""Role names used by the assistant application.

The mock ITSM keeps its own copy on purpose (see mock_itsm/seed_data.py).
A test checks that the two lists agree.
"""

ROLE_EMPLOYEE = "employee"
ROLE_IT_SUPPORT_AGENT = "it_support_agent"
ROLE_IT_ADMINISTRATOR = "it_administrator"

ALL_ROLES = frozenset({ROLE_EMPLOYEE, ROLE_IT_SUPPORT_AGENT, ROLE_IT_ADMINISTRATOR})
