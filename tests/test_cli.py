from assistant_app.cli import GENERIC_ERROR, GREETING, MAX_MESSAGE_LENGTH, run_chat


def run_with(inputs: list[str], assistant=None) -> list[str]:
    """Run the chat with scripted inputs and return everything printed."""
    remaining = iter(inputs)
    printed: list[str] = []

    def fake_input(prompt: str) -> str:
        try:
            return next(remaining)
        except StopIteration:
            raise EOFError from None

    run_chat(fake_input, printed.append, assistant)
    return printed


class FixedAssistant:
    def reply(self, message: str) -> str:
        return f"fixed answer to: {message}"


class BrokenAssistant:
    def reply(self, message: str) -> str:
        raise RuntimeError("boom secret detail")


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


def test_injected_assistant_is_used():
    output = run_with(["hello", "quit"], assistant=FixedAssistant())
    assert output[1] == "Assistant: fixed answer to: hello"


def test_unexpected_assistant_failure_shows_only_a_generic_message():
    output = run_with(["hello", "quit"], assistant=BrokenAssistant())
    assert output[1] == GENERIC_ERROR
    assert "boom" not in " ".join(output)
