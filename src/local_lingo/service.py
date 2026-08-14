from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from . import config
from .languages import name_for_code
from .prompts import build_system_prompt, build_user_prompt
from .validation import ValidationError, validate_inputs

_LIST_MODELS_TIMEOUT = 2.5
_SKIP_MODEL_NAME_PARTS = ("embed", "rerank")
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)


def _strip_thinking(content: str) -> str:
    return _THINK_BLOCK.sub("", content or "").strip()


@dataclass
class RunMetrics:
    model: str = ""
    wall_seconds: float = 0.0
    total_duration_ns: int = 0
    load_duration_ns: int = 0
    prompt_eval_count: int = 0
    prompt_eval_duration_ns: int = 0
    eval_count: int = 0
    eval_duration_ns: int = 0

    def tokens_per_sec(self, count: int, duration_ns: int) -> float | None:
        seconds = duration_ns / 1_000_000_000
        if seconds <= 0 or count <= 0:
            return None
        return count / seconds

    @property
    def prompt_eval_rate(self) -> float | None:
        return self.tokens_per_sec(self.prompt_eval_count, self.prompt_eval_duration_ns)

    @property
    def eval_rate(self) -> float | None:
        """Ollama eval rate: generated tokens / eval_duration."""
        return self.tokens_per_sec(self.eval_count, self.eval_duration_ns)

    @property
    def wall_tokens_per_sec(self) -> float | None:
        if self.wall_seconds <= 0 or self.eval_count <= 0:
            return None
        return self.eval_count / self.wall_seconds


@dataclass
class TranslationResult:
    provided: str
    detected: str
    corrected: str
    target: str
    translation: str
    note: str = ""
    raw: str = ""
    metrics: RunMetrics = field(default_factory=RunMetrics)


@dataclass(frozen=True)
class ModelCatalog:
    choices: list[str]
    selected: str | None
    reachable: bool
    warning: str


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


def _int_field(payload: dict, key: str) -> int:
    try:
        return int(payload.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def metrics_from_ollama(payload: dict, model: str, wall_seconds: float = 0.0) -> RunMetrics:
    return RunMetrics(
        model=model,
        wall_seconds=wall_seconds,
        total_duration_ns=_int_field(payload, "total_duration"),
        load_duration_ns=_int_field(payload, "load_duration"),
        prompt_eval_count=_int_field(payload, "prompt_eval_count"),
        prompt_eval_duration_ns=_int_field(payload, "prompt_eval_duration"),
        eval_count=_int_field(payload, "eval_count"),
        eval_duration_ns=_int_field(payload, "eval_duration"),
    )


def ollama_chat(
    model: str,
    messages: list[dict[str, str]],
) -> tuple[str, dict]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "keep_alive": config.KEEP_ALIVE,
        "options": {
            "temperature": config.TEMPERATURE,
            "num_ctx": config.NUM_CTX,
        },
    }
    request = urllib.request.Request(
        f"{ollama_api_base()}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=config.REQUEST_TIMEOUT_SECONDS) as response:
        body = json.loads(response.read().decode())
    content = _strip_thinking(((body.get("message") or {}).get("content") or "").strip())
    return content, body if isinstance(body, dict) else {}


def print_model_startup_status() -> None:
    catalog = get_model_catalog()
    if catalog.warning:
        print(f"LocalLingo: {catalog.warning}")
        return
    print(f"LocalLingo: {len(catalog.choices)} Ollama model(s), using {catalog.selected}")


def parse_fields(content: str, original: str) -> TranslationResult:
    content = _strip_thinking(content)
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
    system_guidelines: str | None = None,
    user_extra: str | None = None,
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

    left, right = pair.split("-", 1)
    name_a = name_for_code(left)
    name_b = name_for_code(right)
    messages = [
        {
            "role": "system",
            "content": build_system_prompt(name_a, name_b, system_guidelines),
        },
        {
            "role": "user",
            "content": build_user_prompt(cleaned, name_a, name_b, user_extra),
        },
    ]

    try:
        content, payload = ollama_chat(model, messages)
    except Exception as exc:
        return TranslationResult(
            provided=cleaned,
            detected="?",
            corrected="?",
            target="?",
            translation="?",
            note=f"Error talking to Ollama: {exc}",
            metrics=RunMetrics(model=model),
        )

    result = parse_fields(content, cleaned)
    result.metrics = metrics_from_ollama(payload, model)
    return result
