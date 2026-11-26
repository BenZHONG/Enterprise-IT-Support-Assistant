"""Simulated authentication for the local demo.

Each fictional employee has a demo token in an environment variable
(DEMO_TOKEN_E1001=...). The server keeps only SHA-256 digests of the
tokens, compares them in constant time, and then builds the trusted
EmployeeContext from the DIRECTORY record. Role and region are never
taken from the token or from anything the user or model sends.

Production: replace this with an identity provider (for example
OpenID Connect sign-in through Microsoft Entra ID). The server would
verify a signed, short-lived token (issuer, audience, expiry) and then
load the employee record. See the README section "Identity in production".
"""

import hashlib
import hmac
import os
import re
from collections.abc import Mapping
from typing import Protocol

from assistant_app.security.context import EmployeeContext, EmployeeRecord
from assistant_app.security.errors import ServiceError

TOKEN_ENV_PREFIX = "DEMO_TOKEN_"
MIN_TOKEN_LENGTH = 16
MAX_TOKEN_LENGTH = 256
_EMPLOYEE_ID_RE = re.compile(r"^E[0-9]{4}$")


class EmployeeDirectory(Protocol):
    def get_employee(self, employee_id: str) -> EmployeeRecord | None: ...


def load_demo_tokens(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Read DEMO_TOKEN_<employee id> variables. Blank values are skipped.
    Error messages name the variable, never its value."""
    source = os.environ if env is None else env
    tokens: dict[str, str] = {}
    for key, value in source.items():
        if not key.startswith(TOKEN_ENV_PREFIX):
            continue
        employee_id = key[len(TOKEN_ENV_PREFIX) :]
        if not _EMPLOYEE_ID_RE.match(employee_id):
            raise ValueError(f"{key} must look like {TOKEN_ENV_PREFIX}E1001")
        token = value.strip()
        if token:
            tokens[employee_id] = token
    return tokens


def _digest(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


class TokenAuthenticator:
    def __init__(self, tokens: Mapping[str, str], directory: EmployeeDirectory) -> None:
        entries: list[tuple[bytes, str]] = []
        seen: set[bytes] = set()
        for employee_id, token in tokens.items():
            if not _EMPLOYEE_ID_RE.match(employee_id):
                raise ValueError("invalid employee id in the token table")
            if (
                not isinstance(token, str)
                or not MIN_TOKEN_LENGTH <= len(token) <= MAX_TOKEN_LENGTH
            ):
                raise ValueError(
                    f"demo tokens must be {MIN_TOKEN_LENGTH}-{MAX_TOKEN_LENGTH} characters"
                )
            digest = _digest(token)
            if digest in seen:
                raise ValueError("demo tokens must be unique")
            seen.add(digest)
            entries.append((digest, employee_id))
        self._entries = tuple(entries)  # digests only: plain tokens are not kept
        self._directory = directory

    def authenticate(self, token: object) -> EmployeeContext:
        """Return the trusted context, or raise authentication_required.

        Every failure gives the same error, so an attacker cannot tell a
        wrong token from a token for an unknown employee."""
        if not isinstance(token, str) or not token or len(token) > MAX_TOKEN_LENGTH:
            raise ServiceError("authentication_required")
        try:
            presented = _digest(token)
        except UnicodeEncodeError:
            raise ServiceError("authentication_required") from None

        matched: str | None = None
        for digest, employee_id in self._entries:  # no early exit
            if hmac.compare_digest(digest, presented):
                matched = employee_id
        if matched is None:
            raise ServiceError("authentication_required")

        record = self._directory.get_employee(matched)
        if record is None:
            raise ServiceError("authentication_required")
        return EmployeeContext.from_record(record)
