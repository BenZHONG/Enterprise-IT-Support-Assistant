from types import SimpleNamespace

import httpx
import openai
import pytest

from assistant_app.llm_client import LLMError, OpenAIChatModel

REQUEST = httpx.Request("POST", "https://api.example.com/v1/chat/completions")
MESSAGES = [{"role": "user", "content": "hello"}]


def make_client(result=None, error=None):
    def create(**kwargs):
        if error is not None:
            raise error
        return result

    completions = SimpleNamespace(create=create)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def response_with(content):
    message = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def status_error(error_class, status_code):
    return error_class(
        "secret detail sk-LEAK",
        response=httpx.Response(status_code, request=REQUEST),
        body=None,
    )


def test_returns_text_from_a_successful_response():
    model = OpenAIChatModel(client=make_client(result=response_with("Hi there")))
    assert model.complete(MESSAGES) == "Hi there"


def test_empty_answer_is_an_error():
    model = OpenAIChatModel(client=make_client(result=response_with("  ")))
    with pytest.raises(LLMError) as info:
        model.complete(MESSAGES)
    assert info.value.retryable is True


def test_timeout_becomes_a_retryable_safe_error():
    error = openai.APITimeoutError(REQUEST)
    model = OpenAIChatModel(client=make_client(error=error))
    with pytest.raises(LLMError) as info:
        model.complete(MESSAGES)
    assert info.value.retryable is True


def test_rate_limit_becomes_a_retryable_error_without_leaking_details():
    error = status_error(openai.RateLimitError, 429)
    model = OpenAIChatModel(client=make_client(error=error))
    with pytest.raises(LLMError) as info:
        model.complete(MESSAGES)
    assert info.value.retryable is True
    assert "sk-LEAK" not in str(info.value)


def test_auth_error_is_not_retryable_and_does_not_leak_details():
    error = status_error(openai.AuthenticationError, 401)
    model = OpenAIChatModel(client=make_client(error=error))
    with pytest.raises(LLMError) as info:
        model.complete(MESSAGES)
    assert info.value.retryable is False
    assert "sk-LEAK" not in str(info.value)
