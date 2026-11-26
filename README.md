# Enterprise IT Support Assistant (fictional demo)

A learning project that simulates an Australian enterprise IT service desk.
All employees, devices, tickets, and policies are fictional.

## Status
Stage 2 of 20: command-line assistant with optional OpenAI answers and a
rule-based fallback.

## Quick start (Windows PowerShell)
    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python -m pytest
    python -m assistant_app

## Configuration (optional AI mode)
    Copy-Item .env.example .env
    notepad .env      # paste your own OPENAI_API_KEY; never commit .env

Without a key the assistant runs in rules-only mode. Tests never need a key.