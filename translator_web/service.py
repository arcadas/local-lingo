from __future__ import annotations

import re
from dataclasses import dataclass

from openai import OpenAI

from . import config
from .prompts import build_system_prompt, build_user_prompt
from .validation import ValidationError, validate_inputs


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
    return OpenAI(
        api_key=config.OLLAMA_API_KEY,
        base_url=config.OLLAMA_BASE_URL,
        timeout=config.REQUEST_TIMEOUT_SECONDS,
    )


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
