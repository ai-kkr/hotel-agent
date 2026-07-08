"""Tests for ``infrastructure.agents.models.build_model`` provider routing."""

from __future__ import annotations

import pytest

from infrastructure.agents.models import build_model
from infrastructure.config import Settings


def _settings(
    *,
    llm_model: str = "gpt-4o-mini",
    zai_api_key: str = "test-zai-key",
    zai_api_base: str = "https://open.bigmodel.cn/api/coding/paas/v4",
) -> Settings:
    return Settings(llm_model=llm_model, zai_api_key=zai_api_key, zai_api_base=zai_api_base)


def _patch_init(monkeypatch) -> list[dict[str, object]]:
    """Replace ``init_chat_model`` with a recorder; return its call list."""
    calls: list[dict[str, object]] = []

    def fake_init(model: str, **kwargs: object):
        calls.append({"model": model, **kwargs})
        return object()

    monkeypatch.setattr("infrastructure.agents.models.init_chat_model", fake_init)
    return calls


def test_bare_model_defaults_to_openai(monkeypatch):
    calls = _patch_init(monkeypatch)
    build_model(_settings(llm_model="gpt-4o-mini"))
    assert calls == [{"model": "gpt-4o-mini", "model_provider": "openai", "temperature": 0}]


def test_openai_prefixed_model(monkeypatch):
    calls = _patch_init(monkeypatch)
    build_model(_settings(llm_model="openai:gpt-4o-mini"))
    assert calls == [{"model": "openai:gpt-4o-mini", "temperature": 0}]


def test_zai_provider_routes_to_openai_compatible_endpoint(monkeypatch):
    calls = _patch_init(monkeypatch)
    build_model(_settings(llm_model="zai:glm-5.2"))
    assert calls == [
        {
            "model": "openai:glm-5.2",
            "temperature": 0,
            "base_url": "https://open.bigmodel.cn/api/coding/paas/v4",
            "api_key": "test-zai-key",
        }
    ]


def test_zai_provider_without_api_key_raises(monkeypatch):
    _patch_init(monkeypatch)
    with pytest.raises(ValueError, match="KKR_ZAI_API_KEY"):
        build_model(Settings(llm_model="zai:glm-5.2", zai_api_key=""))


def test_zai_custom_base_url_is_forwarded(monkeypatch):
    calls = _patch_init(monkeypatch)
    build_model(_settings(llm_model="zai:glm-5.2", zai_api_base="https://custom.example/v1/"))
    assert calls[0]["base_url"] == "https://custom.example/v1/"


def test_unknown_provider_raises(monkeypatch):
    _patch_init(monkeypatch)
    with pytest.raises(ValueError, match="unknown LLM provider"):
        build_model(_settings(llm_model="unknown:foo"))
