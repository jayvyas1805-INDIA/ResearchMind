"""
LLM service — configurable provider (ollama | openai | gemini) via env vars.
Default: local Ollama (open-source, no API key needed).
"""
import httpx
from app.core.config import get_settings

settings = get_settings()


class LLMError(Exception):
    pass


def _call_ollama(prompt: str, system: str | None = None) -> str:
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {"model": settings.LLM_MODEL, "prompt": prompt, "system": system or "", "stream": False}
    try:
        resp = httpx.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except httpx.HTTPError as exc:
        raise LLMError(
            f"Could not reach Ollama at {settings.OLLAMA_BASE_URL}. "
            f"Is it running (`ollama serve`) with model '{settings.LLM_MODEL}' pulled? ({exc})"
        ) from exc


def _call_openai(prompt: str, system: str | None = None) -> str:
    if not settings.OPENAI_API_KEY:
        raise LLMError("OPENAI_API_KEY is not set.")
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    try:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            json={"model": settings.LLM_MODEL or "gpt-4o-mini", "messages": messages},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError) as exc:
        raise LLMError(f"OpenAI request failed: {exc}") from exc


def _call_gemini(prompt: str, system: str | None = None) -> str:
    if not settings.GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY is not set.")
    model = settings.LLM_MODEL or "gemini-1.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    try:
        resp = httpx.post(url, json={"contents": [{"parts": [{"text": full_prompt}]}]}, timeout=60)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (httpx.HTTPError, KeyError, IndexError) as exc:
        raise LLMError(f"Gemini request failed: {exc}") from exc


_PROVIDERS = {"ollama": _call_ollama, "openai": _call_openai, "gemini": _call_gemini}


def generate(prompt: str, system: str | None = None) -> str:
    provider = settings.LLM_PROVIDER.lower()
    fn = _PROVIDERS.get(provider)
    if not fn:
        raise LLMError(f"Unknown LLM_PROVIDER '{provider}'. Use one of: {list(_PROVIDERS)}")
    return fn(prompt, system=system)
