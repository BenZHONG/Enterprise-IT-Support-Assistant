"""A thin wrapper around the OpenAI SDK.

Everything else in the project depends on the small ChatModel interface,
not on OpenAI directly. Tests use a fake ChatModel, so they need no
network, no key, and no money.
"""

from typing import Protocol

import openai
from openai import OpenAI

Message = dict[str, str]  # {"role": "system" | "user" | "assistant", "content": "..."}


class LLMError(Exception):
    """A safe, employee-presentable failure. Never carries raw API details."""

    def __init__(self, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class ChatModel(Protocol):
    def complete(self, messages: list[Message]) -> str: ...


class OpenAIChatModel:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        timeout_seconds: float = 20.0,
        max_retries: int = 2,
        max_output_tokens: int = 400,
        client=None,
    ) -> None:
        self._model = model
        self._max_output_tokens = max_output_tokens
        # The SDK applies the timeout and retries transient failures
        # (connection errors, 429, 5xx) up to max_retries times.
        self._client = client or OpenAI(
            api_key=api_key, timeout=timeout_seconds, max_retries=max_retries
        )

    def complete(self, messages: list[Message]) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_completion_tokens=self._max_output_tokens,
            )
        # "from None" drops the original exception: SDK messages can
        # contain fragments of the API key.
        except openai.AuthenticationError:
            raise LLMError("The AI service rejected our credentials.", False) from None
        except openai.RateLimitError:
            raise LLMError("The AI service is busy right now.", True) from None
        except openai.APITimeoutError:
            raise LLMError("The AI service took too long to answer.", True) from None
        except openai.APIConnectionError:
            raise LLMError("We could not reach the AI service.", True) from None
        except openai.APIStatusError:
            raise LLMError("The AI service returned an error.", False) from None
        except openai.OpenAIError:
            raise LLMError("The AI service failed unexpectedly.", False) from None

        text = None
        if response.choices:
            text = response.choices[0].message.content
        if not text or not text.strip():
            raise LLMError("The AI service returned an empty answer.", True)
        return text
