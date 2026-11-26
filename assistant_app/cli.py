"""Command-line chat loop.

input_fn, output_fn, and assistant are parameters so tests can supply
fakes instead of a real keyboard, screen, and AI service.
"""

from collections.abc import Callable
from typing import Protocol

from dotenv import load_dotenv

from assistant_app.assistant import Assistant
from assistant_app.config import ConfigError, Settings, load_settings
from assistant_app.llm_client import OpenAIChatModel

EXIT_WORDS = {"quit", "exit", "bye"}
MAX_MESSAGE_LENGTH = 500

GREETING = (
    "Hello, I am the Example Pty Ltd IT Support Assistant (Stage 2 demo).\n"
    "Ask about Wi-Fi, VPN, passwords, Microsoft 365, hardware, or outages.\n"
    "Type 'quit' to leave."
)

GENERIC_ERROR = (
    "Assistant: Something went wrong on our side. Please try again, "
    "or contact the IT service desk."
)


class Replier(Protocol):
    def reply(self, message: str) -> str: ...


def run_chat(
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    assistant: Replier | None = None,
) -> None:
    """Run the chat loop until the user quits or input ends."""
    if assistant is None:
        assistant = Assistant(model=None)  # rules-only, same as Stage 1
    output_fn(GREETING)
    while True:
        try:
            raw = input_fn("You: ")
        except (EOFError, KeyboardInterrupt):
            output_fn("\nAssistant: Goodbye.")
            return

        message = raw.strip()
        if not message:
            continue
        if message.lower() in EXIT_WORDS:
            output_fn("Assistant: Goodbye.")
            return
        if len(message) > MAX_MESSAGE_LENGTH:
            output_fn(
                f"Assistant: That message is too long. "
                f"Please keep it under {MAX_MESSAGE_LENGTH} characters."
            )
            continue

        try:
            answer = assistant.reply(message)
        except Exception:  # safety net: never show raw errors to employees
            # Stages 16-17 replace this with structured errors and audit logs.
            output_fn(GENERIC_ERROR)
            continue
        output_fn(f"Assistant: {answer}")


def build_assistant(settings: Settings) -> Assistant:
    if settings.openai_api_key is None:
        return Assistant(model=None)
    model = OpenAIChatModel(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        timeout_seconds=settings.timeout_seconds,
        max_retries=settings.max_retries,
    )
    return Assistant(model=model)


def main() -> None:
    load_dotenv()  # reads .env if present; real environment variables win
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"Configuration error: {exc}")
        raise SystemExit(2) from None

    if settings.openai_api_key is None:
        print("Running in rules-only mode (no OPENAI_API_KEY set).")
    else:
        print(f"Running with AI model: {settings.openai_model}")
    run_chat(assistant=build_assistant(settings))
