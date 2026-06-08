from __future__ import annotations

import json
import re

from .config import Settings


class LLMUnavailable(RuntimeError):
    """Raised when an online LLM is requested but cannot be used."""


class OpenAICompatibleLLM:
    """Thin wrapper over the OpenAI SDK.

    Works with any OpenAI-compatible endpoint via ``base_url`` (OpenAI,
    DeepSeek, Together, Groq, local vLLM/Ollama, ...). System and user roles
    are kept separate so the stable instruction/schema part can be cached by
    the provider, while only the variable evidence goes in the user turn.
    """

    def __init__(self, settings: Settings):
        if not settings.api_key:
            raise LLMUnavailable("OPENAI_API_KEY is not set.")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise LLMUnavailable("Install `openai` or run in offline mode.") from exc
        self.settings = settings
        self._client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)

    def complete_json(self, system: str, user: str) -> dict:
        resp = self._client.chat.completions.create(
            model=self.settings.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
            response_format={"type": "json_object"},
        )
        return safe_json(resp.choices[0].message.content or "{}")


def build_llm(settings: Settings) -> OpenAICompatibleLLM | None:
    """Return a client, or ``None`` when offline / no key (caller falls back)."""
    if not settings.can_use_llm:
        return None
    try:
        return OpenAICompatibleLLM(settings)
    except LLMUnavailable:
        return None


def safe_json(text: str) -> dict:
    """Best-effort JSON extraction from a model response."""
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    # strip ```json fences
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except Exception:
            pass
    # first balanced-looking object
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group(0))
        except Exception:
            pass
    return {}
