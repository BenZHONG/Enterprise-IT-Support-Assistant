from assistant_app.cli import GREETING, MAX_MESSAGE_LENGTH, run_chat


def run_with(inputs: list[str]) -> list[str]:
    """Run the chat with scripted inputs and return everything printed."""
    remaining = iter(inputs)
    printed: list[str] = []

    def fake_input(prompt: str) -> str:
        try:
            return next(remaining)
        except StopIteration:
            raise EOFError from None

    run_chat(fake_input, printed.append)
    return printed


def test_quit_ends_the_chat():
    output = run_with(["quit"])
    assert output[0] == GREETING
    assert output[-1] == "Assistant: Goodbye."


def test_blank_lines_are_ignored():
    output = run_with(["", "   ", "quit"])
    assert len(output) == 2  # greeting + goodbye only


def test_wifi_question_gets_wifi_advice():
    output = run_with(["my wifi is down", "quit"])
    assert output[1].startswith("Assistant:")
    assert "Wi-Fi" in output[1]


def test_end_of_input_exits_cleanly():
    output = run_with([])  # no input at all: simulates Ctrl+Z / Ctrl+C
    assert "Goodbye" in output[-1]


def test_overlong_message_is_rejected():
    output = run_with(["x" * (MAX_MESSAGE_LENGTH + 1), "quit"])
    assert "too long" in output[1]
