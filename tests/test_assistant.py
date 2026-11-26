import pytest

from assistant_app.assistant import (
    AI_UNAVAILABLE_NOTICE,
    MAX_REPLY_CHARS,
    SECRET_WARNING,
    SYSTEM_PROMPT,
    Assistant,
)
from assistant_app.llm_client import LLMError
from assistant_app.responder import get_reply


class FakeModel:
    """Test double: returns scripted text or raises, and records calls."""

    def __init__(self, reply="Fake AI answer", error=None):
        self.reply = reply
        self.error = error
        self.calls = []

    def complete(self, messages):
        self.calls.append(list(messages))
        if self.error is not None:
            raise self.error
        return self.reply


def test_without_a_model_uses_the_rule_based_reply():
    assistant = Assistant(model=None)
    assert assistant.reply("my wifi is down") == get_reply("my wifi is down")


def test_model_reply_is_returned():
    assistant = Assistant(FakeModel(reply="Try restarting."))
    assert assistant.reply("my wifi is down") == "Try restarting."


def test_system_prompt_comes_first_and_history_is_included():
    model = FakeModel(reply="Try X")
    assistant = Assistant(model)
    assistant.reply("my wifi is down")
    assistant.reply("still down")
    second_call = model.calls[1]
    assert [m["role"] for m in second_call] == ["system", "user", "assistant", "user"]
    assert second_call[0]["content"] == SYSTEM_PROMPT
    assert second_call[-1]["content"] == "still down"


def test_history_is_bounded():
    model = FakeModel()
    assistant = Assistant(model, max_history_messages=4)
    for i in range(5):
        assistant.reply(f"question {i}")
    assert len(model.calls[-1]) == 6  # system + 4 history + new user message


def test_model_failure_falls_back_to_rules_and_skips_history():
    model = FakeModel(error=LLMError("down", retryable=True))
    assistant = Assistant(model)
    answer = assistant.reply("my wifi is down")
    assert answer == AI_UNAVAILABLE_NOTICE + get_reply("my wifi is down")

    model.error = None
    assistant.reply("hello again")
    roles = [m["role"] for m in model.calls[-1]]
    assert roles == ["system", "user"]  # failed turn was not remembered


@pytest.mark.parametrize(
    "message",
    [
        "my password is Hunter2",
        "password: abc123",
        "here is my key sk-abcdefghijklmnop1234",
    ],
)
def test_secret_looking_messages_are_never_sent_to_the_model(message):
    model = FakeModel()
    assistant = Assistant(model)
    assert assistant.reply(message) == SECRET_WARNING
    assert model.calls == []


def test_normal_password_complaint_is_not_blocked():
    model = FakeModel()
    Assistant(model).reply("my password is not working")
    assert len(model.calls) == 1


def test_overlong_model_reply_is_truncated():
    assistant = Assistant(FakeModel(reply="a" * 5000))
    assert len(assistant.reply("hello")) <= MAX_REPLY_CHARS
