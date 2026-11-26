# Enterprise IT Support Assistant (fictional demo)

A learning project that simulates an Australian enterprise IT service desk.
All employees, devices, tickets, and policies are fictional.

## Status
Stage 5 of 20: trusted identity (demo tokens), role permissions, ownership
checks, and delegated support access.

## Quick start (Windows PowerShell)
    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python -m pytest
    python -m scripts.seed
    python -m scripts.demo_tool_validation
    python -m scripts.demo_permissions
    python -m assistant_app

## Project layout
- `assistant_app/`          the assistant employees talk to
  - `schemas/`              Pydantic models: API bodies, tool arguments, results, errors
  - `security/`             identity, permissions, ownership checks, delegated access
  - `rag/`                  knowledge document loader (more in Stage 9+)
- `mock_itsm/`              the fictional ITSM service and its seed data
- `data/knowledge_base/`    Markdown knowledge documents with front matter
- `scripts/`                helper commands (seed check, demos, demo tokens)
- `tests/`                  pytest tests (no paid API calls or real credentials)

## Configuration
    Copy-Item .env.example .env
    notepad .env      # OPENAI_API_KEY is optional; never commit .env

Without an OpenAI key the assistant runs in rules-only mode. Tests never
need a key or any tokens.

### Demo sign-in tokens
    python -m scripts.make_demo_tokens     # prints 8 DEMO_TOKEN_ lines
Paste them over the blank `DEMO_TOKEN_` lines in `.env`, then check one:
    python -m scripts.whoami E1001

## Roles and permissions
| Capability | Employee | IT Support Agent | IT Administrator |
|---|---|---|---|
| Own tickets, devices, profile | yes | yes | yes |
| Prepare and confirm own tickets | yes | yes | yes |
| Outages in own region | yes | yes | yes |
| Outages in any region | no | yes | yes |
| Other people's tickets, devices, profiles | no | only with a grant | yes |
| Staff-only knowledge documents | no | yes | yes |
| Create and revoke delegated grants | no | no | yes |

Anything not in this table is denied. Inactive accounts are denied everything
except the "is my account active?" check.

## Delegated support access
An agent has no standing access to another person's data. An administrator
creates a grant: one agent, one employee, read-only scopes (`tickets:read`,
`devices:read`, `profile:read`), 1 to 60 minutes, revocable, and recorded with
who created it.

## Errors
- Missing or invalid sign-in: `authentication_required`
- Inactive account or missing capability: `permission_denied`
- Missing resource OR someone else's private resource: `not_found` (identical)

## Identity in production
The demo uses tokens from environment variables. A real deployment would:
- sign employees in through an identity provider (for example OpenID Connect
  with Microsoft Entra ID) and verify a signed, short-lived token (issuer,
  audience, expiry) on every request;
- give the assistant a workload identity (a managed identity, not a shared
  password) to call the ITSM API, with scopes kept separate from employee
  permissions;
- keep any remaining secrets in a managed secret store such as Azure Key Vault
  or AWS Secrets Manager, with rotation.