import sys
import types as pytypes

from src import genai as inventory_genai


SAMPLE_ROWS = [{
    "sku": "PKG004",
    "material_name": "Bubble Wrap",
    "status": "Restock Priority",
    "current_stock": 8,
    "minimum_stock": 10,
    "usage_30d": 11,
    "lead_time_days": 3,
    "unit": "roll",
}]


class FakeAPIError(Exception):
    def __init__(self, code, message="provider error"):
        super().__init__(message)
        self.code = code


def install_fake_genai(monkeypatch, generate_content):
    fake_types = pytypes.SimpleNamespace(
        HttpOptions=lambda **kwargs: kwargs,
        HttpRetryOptions=lambda **kwargs: kwargs,
        GenerateContentConfig=lambda **kwargs: kwargs,
    )

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.models = pytypes.SimpleNamespace(generate_content=generate_content)

    fake_genai = pytypes.ModuleType("google.genai")
    fake_genai.Client = FakeClient
    fake_genai.types = fake_types
    fake_google = pytypes.ModuleType("google")
    fake_google.genai = fake_genai
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)


def test_fallback_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    summary, source = inventory_genai.generate_inventory_summary(SAMPLE_ROWS)
    assert source == "fallback"
    assert "Bubble Wrap" in summary
    assert "API key Gemini belum dikonfigurasi" in summary


def test_retries_once_after_503_then_succeeds(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-model")
    inventory_genai._summary_cache.clear()
    calls = {"count": 0}

    def generate_content(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise FakeAPIError(503, "temporary unavailable")
        return pytypes.SimpleNamespace(text="Ringkasan dari Gemini")

    install_fake_genai(monkeypatch, generate_content)
    monkeypatch.setattr(inventory_genai.time, "sleep", lambda _: None)
    summary, source = inventory_genai.generate_inventory_summary(SAMPLE_ROWS)
    assert source == "gemini"
    assert summary == "Ringkasan dari Gemini"
    assert calls["count"] == 2


def test_caches_successful_gemini_summary(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-cache")
    inventory_genai._summary_cache.clear()
    calls = {"count": 0}

    def generate_content(**kwargs):
        calls["count"] += 1
        return pytypes.SimpleNamespace(text="Cached Gemini summary")

    install_fake_genai(monkeypatch, generate_content)
    first = inventory_genai.generate_inventory_summary(SAMPLE_ROWS)
    second = inventory_genai.generate_inventory_summary(SAMPLE_ROWS)
    assert first == ("Cached Gemini summary", "gemini")
    assert second == first
    assert calls["count"] == 1


def test_does_not_retry_non_transient_404(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "missing-model")
    inventory_genai._summary_cache.clear()
    calls = {"count": 0}

    def generate_content(**kwargs):
        calls["count"] += 1
        raise FakeAPIError(404, "model not found")

    install_fake_genai(monkeypatch, generate_content)
    summary, source = inventory_genai.generate_inventory_summary(SAMPLE_ROWS)
    assert source == "fallback"
    assert "HTTP 404" in summary
    assert calls["count"] == 1
