from types import SimpleNamespace

import pytest

from cchard_eval.client import EndpointConfig, OpenAIChatClient, SyntheticClient


def _response(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def test_openai_client_retries_then_succeeds(monkeypatch):
    monkeypatch.setenv("CCHARD_TEST_KEY", "secret-value")
    attempts = {"count": 0}

    class Completions:
        def create(self, **kwargs):
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise RuntimeError("temporary")
            assert kwargs["temperature"] == 0
            return _response("成功")

    sdk = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    client = OpenAIChatClient(sdk_factory=lambda **kwargs: sdk, sleep=lambda seconds: None)
    config = EndpointConfig("m", "model-id", "https://example.test/v1", "CCHARD_TEST_KEY")
    result = client.complete([{"role": "user", "content": "hi"}], config)
    assert result.status == "ok"
    assert result.content == "成功"
    assert result.attempts == 3


def test_openai_client_requires_named_environment_key(monkeypatch):
    monkeypatch.delenv("MISSING_CCHARD_KEY", raising=False)
    client = OpenAIChatClient(sdk_factory=lambda **kwargs: None)
    config = EndpointConfig("m", "model-id", "https://example.test/v1", "MISSING_CCHARD_KEY")
    with pytest.raises(ValueError, match="MISSING_CCHARD_KEY"):
        client.complete([{"role": "user", "content": "hi"}], config)


def test_public_config_never_contains_secret_value(monkeypatch):
    monkeypatch.setenv("CCHARD_TEST_KEY", "do-not-serialize")
    config = EndpointConfig("m", "model-id", "https://example.test/v1", "CCHARD_TEST_KEY")
    text = str(config.public_dict())
    assert "CCHARD_TEST_KEY" in text
    assert "do-not-serialize" not in text


def test_synthetic_client_is_deterministic():
    config = EndpointConfig("demo", "synthetic-model", "synthetic://offline", "")
    client = SyntheticClient(lambda messages, endpoint: messages[-1]["content"][:6])
    first = client.complete([{"role": "user", "content": "固定内容"}], config)
    second = client.complete([{"role": "user", "content": "固定内容"}], config)
    assert first.content == second.content == "固定内容"
    assert first.status == "ok"

