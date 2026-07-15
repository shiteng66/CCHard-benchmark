from __future__ import annotations

from dataclasses import asdict, dataclass
import os
import time
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class EndpointConfig:
    label: str
    model: str
    base_url: str
    api_key_env: str
    temperature: float = 0.0
    top_p: float = 1.0
    timeout_s: float = 120.0
    max_retries: int = 3

    def public_dict(self) -> dict[str, Any]:
        """Return configuration metadata without resolving the secret value."""
        return asdict(self)


@dataclass(frozen=True)
class CompletionResult:
    content: str
    status: str
    latency_ms: int
    attempts: int
    error_type: str = ""
    error_message: str = ""


class ChatClient(Protocol):
    def complete(self, messages: list[dict[str, str]], config: EndpointConfig) -> CompletionResult: ...


def _default_sdk_factory(**kwargs: Any) -> Any:
    from openai import OpenAI

    return OpenAI(**kwargs)


class OpenAIChatClient:
    def __init__(
        self,
        *,
        sdk_factory: Callable[..., Any] = _default_sdk_factory,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._sdk_factory = sdk_factory
        self._sleep = sleep

    def complete(self, messages: list[dict[str, str]], config: EndpointConfig) -> CompletionResult:
        if not config.api_key_env:
            raise ValueError("api_key_env is required for a real endpoint")
        api_key = os.getenv(config.api_key_env)
        if not api_key:
            raise ValueError(f"missing API key environment variable: {config.api_key_env}")
        sdk = self._sdk_factory(api_key=api_key, base_url=config.base_url, timeout=config.timeout_s)
        started = time.monotonic()
        last_error: Exception | None = None
        attempts = max(1, int(config.max_retries))
        for attempt in range(1, attempts + 1):
            try:
                response = sdk.chat.completions.create(
                    model=config.model,
                    messages=messages,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    stream=False,
                )
                content = response.choices[0].message.content or ""
                return CompletionResult(
                    content=content,
                    status="ok",
                    latency_ms=round((time.monotonic() - started) * 1000),
                    attempts=attempt,
                )
            except Exception as exc:  # provider-specific exception classes vary
                last_error = exc
                if attempt < attempts:
                    self._sleep(min(2 ** (attempt - 1), 8))
        assert last_error is not None
        return CompletionResult(
            content="",
            status="error",
            latency_ms=round((time.monotonic() - started) * 1000),
            attempts=attempts,
            error_type=type(last_error).__name__,
            error_message=str(last_error)[:500],
        )


class SyntheticClient:
    """Deterministic offline client used only for tests and the labelled demo."""

    def __init__(self, handler: Callable[[list[dict[str, str]], EndpointConfig], str]) -> None:
        self._handler = handler

    def complete(self, messages: list[dict[str, str]], config: EndpointConfig) -> CompletionResult:
        started = time.monotonic()
        try:
            content = self._handler(messages, config)
            return CompletionResult(
                content=str(content),
                status="ok",
                latency_ms=round((time.monotonic() - started) * 1000),
                attempts=1,
            )
        except Exception as exc:
            return CompletionResult(
                content="",
                status="error",
                latency_ms=round((time.monotonic() - started) * 1000),
                attempts=1,
                error_type=type(exc).__name__,
                error_message=str(exc)[:500],
            )

