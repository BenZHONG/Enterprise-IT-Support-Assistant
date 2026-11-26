"""Command-line chat loop.

input_fn and output_fn are parameters so tests can supply fakes
instead of a real keyboard and screen.
"""

from collections.abc import Callable

from assistant_app.responder import get_reply

EXIT_WORDS = {"quit", "exit", "bye"}
MAX_MESSAGE_LENGTH = 500

GREETING = (
    "Hello, I am the Example Pty Ltd IT Support Assistant (Stage 1 demo).\n"
    "Ask about Wi-Fi, VPN, passwords, Microsoft 365, hardware, or outages.\n"
    "Type 'quit' to leave."
)


def run_chat(
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    """Run the chat loop until the user quits or input ends."""
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

        output_fn(f"Assistant: {get_reply(message)}")


def main() -> None:
    run_chat()
