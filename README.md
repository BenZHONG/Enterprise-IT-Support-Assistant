# Enterprise IT Support Assistant (fictional demo)

A learning project that simulates an Australian enterprise IT service desk.
All employees, devices, tickets, and policies are fictional.

## Status
Stage 3 of 20: fictional demo data (employees, devices, tickets, outages)
and a knowledge base, with a seed check command.

## Quick start (Windows PowerShell)
    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python -m pytest
    python -m scripts.seed
    python -m assistant_app

## Project layout
- `assistant_app/`   the assistant employees talk to (rules, optional AI, RAG loader)
- `mock_itsm/`       the fictional ITSM service and its seed data
- `data/knowledge_base/`  Markdown knowledge documents with front matter
- `scripts/`         helper commands such as the seed check
- `tests/`           pytest tests (no paid API calls or real credentials)

## Configuration (optional AI mode)
    Copy-Item .env.example .env
    notepad .env      # paste your own OPENAI_API_KEY; never commit .env

Without a key the assistant runs in rules-only mode. Tests never need a key.