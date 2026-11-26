# Enterprise IT Support Assistant (fictional demo)

A learning project that simulates an Australian enterprise IT service desk.
All employees, devices, tickets, and policies are fictional.

## Status
Stage 4 of 20: Pydantic schemas for API requests and responses, tool
arguments, and tool results, with a safe tool-argument parser.

## Quick start (Windows PowerShell)
    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python -m pytest
    python -m scripts.seed
    python -m scripts.demo_tool_validation
    python -m assistant_app

## Project layout
- `assistant_app/`          the assistant employees talk to
  - `schemas/`              Pydantic models: API bodies, tool arguments, results, errors
  - `rag/`                  knowledge document loader (more in Stage 9+)
- `mock_itsm/`              the fictional ITSM service and its seed data
- `data/knowledge_base/`    Markdown knowledge documents with front matter
- `scripts/`                helper commands (seed check, validation demo)
- `tests/`                  pytest tests (no paid API calls or real credentials)

## Configuration (optional AI mode)
    Copy-Item .env.example .env
    notepad .env      # paste your own OPENAI_API_KEY; never commit .env

Without a key the assistant runs in rules-only mode. Tests never need a key.