from types import SimpleNamespace

import httpx
import pytest

from app.services import llm_service


def test_mistral_call_uses_configured_api_key_and_messages(monkeypatch):
    settings = llm_service.settings
    monkeypatch.setattr(settings, "MISTRAL_API_KEY", "test-mistral-key")
    monkeypatch.setattr(settings, "LLM_MODEL", "mistral-test-model")
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"choices": [{"message": {"content": " test response "}}]},
        )

    monkeypatch.setattr(llm_service.httpx, "post", fake_post)

    response = llm_service._call_mistral("user prompt", system="system prompt")

    assert response == "test response"
    assert captured["url"] == "https://api.mistral.ai/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-mistral-key"
    assert captured["json"] == {
        "model": "mistral-test-model",
        "messages": [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "user prompt"},
        ],
    }


def test_mistral_call_requires_api_key(monkeypatch):
    monkeypatch.setattr(llm_service.settings, "MISTRAL_API_KEY", "")

    with pytest.raises(llm_service.LLMError, match="MISTRAL_API_KEY is not set"):
        llm_service._call_mistral("user prompt")


def test_mistral_zero_request_limit_has_actionable_error(monkeypatch):
    monkeypatch.setattr(llm_service.settings, "MISTRAL_API_KEY", "test-mistral-key")
    response = httpx.Response(
        429,
        headers={"x-ratelimit-limit-req-minute": "0"},
        request=httpx.Request("POST", "https://api.mistral.ai/v1/chat/completions"),
    )

    def fake_post(*_args, **_kwargs):
        response.raise_for_status()

    monkeypatch.setattr(llm_service.httpx, "post", fake_post)

    with pytest.raises(llm_service.LLMError, match="limit of 0 requests per minute"):
        llm_service._call_mistral("user prompt")
