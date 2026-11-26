"""Check one demo token: python -m scripts.whoami E1001

Reads DEMO_TOKEN_E1001 from .env, authenticates it, and prints the
trusted context the server built.
"""

import re
import sys

from dotenv import load_dotenv

from assistant_app.security.authn import (
    TOKEN_ENV_PREFIX,
    TokenAuthenticator,
    load_demo_tokens,
)
from assistant_app.security.errors import ServiceError
from scripts.demo_wiring import SeedEmployeeDirectory

_EMPLOYEE_ID_RE = re.compile(r"^E[0-9]{4}$")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or not _EMPLOYEE_ID_RE.match(args[0]):
        print("Usage: python -m scripts.whoami E1001")
        return 2

    load_dotenv()
    try:
        tokens = load_demo_tokens()
        authenticator = TokenAuthenticator(tokens, SeedEmployeeDirectory())
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return 1

    token = tokens.get(args[0])
    if token is None:
        print(
            f"No {TOKEN_ENV_PREFIX}{args[0]} in .env. Run: python -m scripts.make_demo_tokens"
        )
        return 1
    try:
        context = authenticator.authenticate(token)
    except ServiceError as exc:
        print(f"Authentication failed: {exc.message}")
        return 1

    print(
        f"Authenticated: {context.employee_id} role={context.role} "
        f"region={context.region_id} active={context.active}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
