"""Create random demo tokens: python -m scripts.make_demo_tokens

Prints one DEMO_TOKEN_<id>=<token> line per fictional employee. Paste the
lines into your .env file. Nothing is written to disk, and the real
tokens never appear in the repository.
"""

import secrets

from assistant_app.security.authn import TOKEN_ENV_PREFIX
from mock_itsm import seed_data


def generate_lines() -> list[str]:
    return [
        f"{TOKEN_ENV_PREFIX}{employee.employee_id}={secrets.token_urlsafe(24)}"
        for employee in seed_data.EMPLOYEES
    ]


def main() -> int:
    print("# Paste these lines into your .env file (never commit .env).")
    for line in generate_lines():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
