"""Gemini-backed inventory summaries with bounded retries and safe fallback."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# Successful summaries are cached in-process for five minutes. Failed calls are
# deliberately not cached, so a temporary provider outage can recover quickly.
_CACHE_TTL_SECONDS = 300
_CACHE_MAX_ITEMS = 64
_summary_cache: dict[str, tuple[float, str]] = {}
_cache_lock = threading.Lock()


def fallback_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Belum ada data inventaris untuk dianalisis."

    priority = sorted(
        [r for r in rows if r["status"] == "Restock Priority"],
        key=lambda x: x["current_stock"] / max(x["minimum_stock"], 1),
    )
    attention = [r for r in rows if r["status"] == "Need Attention"]
    safe = [r for r in rows if r["status"] == "Safe"]

    output = [
        "### Ringkasan kondisi inventaris\n"
        f"Dari {len(rows)} material yang dianalisis, {len(safe)} berstatus Safe, "
        f"{len(attention)} Need Attention, dan {len(priority)} Restock Priority."
    ]
    if priority:
        output.append(
            "### Prioritas restock\n"
            + "\n".join(
                [
                    f"- **{r['material_name']} ({r['sku']})**: stok "
                    f"{r['current_stock']} {r['unit']}, minimum "
                    f"{r['minimum_stock']} {r['unit']}, pemakaian 30 hari "
                    f"{r['usage_30d']} {r['unit']}, lead time "
                    f"{r['lead_time_days']} hari."
                    for r in priority[:5]
                ]
            )
        )
    if attention:
        output.append(
            "### Perlu dipantau\n"
            + ", ".join(r["material_name"] for r in attention[:5])
            + "."
        )
    output.append(
        "### Tindakan yang disarankan\n"
        "Validasi stok fisik dan rencana pesanan, lalu konfirmasi jumlah "
        "pembelian serta lead time dengan pemasok sebelum melakukan restock."
    )
    return "\n\n".join(output)


def _cache_key(rows: list[dict[str, Any]], model: str) -> str:
    payload = json.dumps(rows, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(f"{model}\n{payload}".encode("utf-8")).hexdigest()


def _get_cached_summary(key: str) -> str | None:
    now = time.monotonic()
    with _cache_lock:
        item = _summary_cache.get(key)
        if item is None:
            return None
        created_at, summary = item
        if now - created_at >= _CACHE_TTL_SECONDS:
            _summary_cache.pop(key, None)
            return None
        return summary


def _store_cached_summary(key: str, summary: str) -> None:
    with _cache_lock:
        # Remove expired entries and keep the cache bounded.
        now = time.monotonic()
        expired = [k for k, (created, _) in _summary_cache.items()
                   if now - created >= _CACHE_TTL_SECONDS]
        for old_key in expired:
            _summary_cache.pop(old_key, None)
        if len(_summary_cache) >= _CACHE_MAX_ITEMS:
            oldest = min(_summary_cache, key=lambda k: _summary_cache[k][0])
            _summary_cache.pop(oldest, None)
        _summary_cache[key] = (now, summary)


def _http_status(exc: Exception) -> int | None:
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    try:
        if code is not None:
            return int(code)
    except (TypeError, ValueError):
        pass
    match = re.search(r"\b(400|401|403|404|408|429|500|502|503|504)\b", str(exc))
    return int(match.group(1)) if match else None


def _friendly_error(exc: Exception) -> str:
    status = _http_status(exc)
    if status == 503:
        return "Gemini sedang padat (HTTP 503). Ringkasan lokal ditampilkan."
    if status == 429:
        return "Kuota atau rate limit Gemini tercapai (HTTP 429). Ringkasan lokal ditampilkan."
    if status == 404:
        return "Model Gemini tidak ditemukan atau tidak dapat diakses (HTTP 404). Periksa GEMINI_MODEL."
    if status in (401, 403):
        return "Autentikasi atau izin Gemini ditolak. Periksa API key dan akses API."
    if status in (500, 502, 504):
        return f"Layanan Gemini mengalami gangguan sementara (HTTP {status}). Ringkasan lokal ditampilkan."
    if status == 400:
        return "Request Gemini ditolak (HTTP 400). Periksa format request atau konfigurasi model."
    if "timeout" in type(exc).__name__.lower() or "timed out" in str(exc).lower():
        return "Koneksi ke Gemini melewati batas waktu. Ringkasan lokal ditampilkan."
    return f"Gemini tidak dapat diakses ({type(exc).__name__}). Ringkasan lokal ditampilkan."


def generate_inventory_summary(rows: list[dict[str, Any]]) -> tuple[str, str]:
    """Return (summary, source); source is either 'gemini' or 'fallback'."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

    if not key:
        return fallback_summary(rows) + "\n\n_Catatan: API key Gemini belum dikonfigurasi._", "fallback"

    cache_key = _cache_key(rows, model)
    cached = _get_cached_summary(cache_key)
    if cached is not None:
        return cached, "gemini"

    prompt = (
        "Anda adalah asisten inventory Firaza. Analisis hanya data JSON berikut. "
        "Jangan mengarang angka atau menyatakan tindakan telah dilakukan. "
        "Tulis dalam Bahasa Indonesia dengan bagian: kondisi umum, prioritas "
        "restock, alasan berbasis stok/minimum/pemakaian/lead time, dan tindakan "
        "yang disarankan. Bedakan fakta dan rekomendasi. Data: "
        + json.dumps(rows, ensure_ascii=False, default=str)
    )

    try:
        from google import genai
        from google.genai import types

        # Disable the SDK's own multi-attempt retry loop. We apply one explicit,
        # bounded retry below so Streamlit cannot appear to hang for minutes.
        client = genai.Client(
            api_key=key,
            http_options=types.HttpOptions(
                timeout=15_000,  # milliseconds in google-genai HttpOptions
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

        response = None
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        max_output_tokens=700,
                    ),
                )
                break
            except Exception as exc:
                status = _http_status(exc)
                retryable = status in (500, 502, 503, 504) or (
                    status is None
                    and ("timeout" in type(exc).__name__.lower()
                         or "connection" in type(exc).__name__.lower())
                )
                if attempt == 0 and retryable:
                    time.sleep(1.2)
                    continue
                raise

        summary = getattr(response, "text", None)
        if not summary or not summary.strip():
            raise ValueError("Gemini returned an empty response")

        summary = summary.strip()
        _store_cached_summary(cache_key, summary)
        return summary, "gemini"

    except Exception as exc:
        return (
            fallback_summary(rows)
            + f"\n\n_Catatan: {_friendly_error(exc)}_",
            "fallback",
        )
