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


@dataclass(frozen=True)
class ModelCatalog:
    choices: list[str]
    selected: str | None
    reachable: bool
    warning: str


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


def probe_ollama_models() -> tuple[bool, list[str]]:
    """Return (reachable, installed model names)."""
    request = urllib.request.Request(
        f"{ollama_api_base()}/api/tags",
        headers={"Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=_LIST_MODELS_TIMEOUT) as response:
            payload = json.loads(response.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return False, []

    names: list[str] = []
    for item in payload.get("models") or []:
        name = (item.get("name") or item.get("model") or "").strip()
        if name and _usable_model_name(name):
            names.append(name)
    return True, sorted(set(names), key=str.lower)


def list_ollama_models() -> list[str]:
    """Return locally installed Ollama model names, or [] if Ollama is unreachable."""
    return probe_ollama_models()[1]


def get_model_catalog(
    installed: list[str] | None = None,
    reachable: bool | None = None,
) -> ModelCatalog:
    """Installed models plus a default selection and a user-facing warning if needed."""
    if installed is None:
        reachable, installed = probe_ollama_models()
    elif reachable is None:
        reachable = True

    if not reachable:
        return ModelCatalog(
            choices=[],
            selected=None,
            reachable=False,
            warning=(
                f"Cannot reach Ollama at {ollama_api_base()}. "
                "Start Ollama, then reload this page."
            ),
        )
    if not installed:
        return ModelCatalog(
            choices=[],
            selected=None,
            reachable=True,
            warning=(
                f"No Ollama models installed. Pull the default with: "
                f"ollama pull {config.MODEL}"
            ),
        )

    selected = config.MODEL if config.MODEL in installed else installed[0]
    warning = ""
    if config.MODEL not in installed:
        warning = (
            f"Default model {config.MODEL} is not installed. Using {selected}. "
            f"Pull it with: ollama pull {config.MODEL}"
        )
    return ModelCatalog(
        choices=installed,
        selected=selected,
        reachable=True,
        warning=warning,
    )


def print_model_startup_status() -> None:
    catalog = get_model_catalog()
    if catalog.warning:
        print(f"LocalLingo: {catalog.warning}")
        return
    print(f"LocalLingo: {len(catalog.choices)} Ollama model(s), using {catalog.selected}")


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
