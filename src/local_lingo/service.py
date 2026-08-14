from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from openai import OpenAI

from . import config
from .prompts import build_system_prompt, build_user_prompt
from .validation import ValidationError, validate_inputs

_openai_client: OpenAI | None = None
_LIST_MODELS_TIMEOUT = 2.5
_SKIP_MODEL_NAME_PARTS = ("embed", "rerank")


@dataclass
class TranslationResult:
    provided: str
    detected: str
    corrected: str
    target: str
    translation: str
    note: str = ""
    raw: str = ""


def _client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            api_key=config.OLLAMA_API_KEY,
            base_url=config.OLLAMA_BASE_URL,
            timeout=config.REQUEST_TIMEOUT_SECONDS,
        )
    return _openai_client


def ollama_api_base() -> str:
    url = config.OLLAMA_BASE_URL.rstrip("/")
    if url.endswith("/v1"):
        url = url[: -len("/v1")]
    return url.rstrip("/")


def _usable_model_name(name: str) -> bool:
    lower = name.lower()
    return not any(part in lower for part in _SKIP_MODEL_NAME_PARTS)


def list_ollama_models() -> list[str]:
    """Return locally installed Ollama model names, or [] if Ollama is unreachable."""
    request = urllib.request.Request(
        f"{ollama_api_base()}/api/tags",
        headers={"Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=_LIST_MODELS_TIMEOUT) as response:
            payload = json.loads(response.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return []

    names: list[str] = []
    for item in payload.get("models") or []:
        name = (item.get("name") or item.get("model") or "").strip()
        if name and _usable_model_name(name):
            names.append(name)
    return sorted(set(names), key=str.lower)


def resolve_model_choices(installed: list[str] | None = None) -> tuple[list[str], str]:
    """Choices for the UI dropdown and the default selection."""
    names = list(installed if installed is not None else list_ollama_models())
    if not names:
        return [config.MODEL], config.MODEL
    selected = config.MODEL if config.MODEL in names else names[0]
    return names, selected


def parse_fields(content: str, original: str) -> TranslationResult:
    if not content:
        return TranslationResult(
            provided=original,
            detected="?",
            corrected="?",
            target="?",
            translation="?",
            note="Empty response from model.",
            raw="",
        )

    fields: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip().lower()] = value.strip().strip('"')

    translation_key = next((k for k in fields if k.startswith("translation")), None)
    target = "?"
    if translation_key:
        match = re.search(r"\(([^)]+)\)", translation_key)
        if match:
            target = match.group(1).strip().title()

    detected = fields.get("detected language", "?")
    corrected = fields.get("corrected", "?")
    translation = fields.get(translation_key, "?") if translation_key else "?"

    note = ""
    if detected == "?" or corrected == "?":
        note = f"Could not parse model output.\n\nRaw response:\n{content}"

    return TranslationResult(
        provided=fields.get("provided text", original),
        detected=detected,
        corrected=corrected,
        target=target,
        translation=translation,
        note=note,
        raw=content,
    )


def translate_and_correct(
    text: str,
    language_pair: str = config.DEFAULT_LANGUAGE_PAIR,
    model: str = config.MODEL,
) -> TranslationResult:
    try:
        cleaned, pair = validate_inputs(text, language_pair)
    except ValidationError as exc:
        return TranslationResult(
            provided=(text or "").strip(),
            detected="",
            corrected="",
            target="",
            translation="",
            note=str(exc),
        )

    try:
        response = _client().chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": build_system_prompt(pair)},
                {"role": "user", "content": build_user_prompt(cleaned, pair)},
            ],
            temperature=config.TEMPERATURE,
            extra_body={
                "keep_alive": config.KEEP_ALIVE,
                "options": {"num_ctx": config.NUM_CTX},
            },
        )
    except Exception as exc:
        return TranslationResult(
            provided=cleaned,
            detected="?",
            corrected="?",
            target="?",
            translation="?",
            note=f"Error talking to Ollama: {exc}",
        )

    content = (response.choices[0].message.content or "").strip()
    return parse_fields(content, cleaned)
