from __future__ import annotations

import re

from .languages import CODE_TO_NAME, LANGUAGES

LANGUAGE_PAIR_PATTERN = re.compile(r"^[a-z]{2,3}-[a-z]{2,3}$", re.IGNORECASE)


class ValidationError(ValueError):
    """Raised when user input is invalid."""


def normalize_language_pair(language_pair: str) -> str:
    return (language_pair or "").strip().lower().replace("_", "-")


def resolve_language_code(value: str) -> str:
    """Accept a language code or full name and return a normalized code."""
    raw = (value or "").strip()
    if not raw:
        raise ValidationError("Please select both languages.")

    lower = raw.lower()
    if lower in CODE_TO_NAME:
        return lower

    for name, code in LANGUAGES.items():
        if name.lower() == lower:
            return code

    # Allow typing a code even if not in the curated list
    if re.fullmatch(r"[a-z]{2,3}", lower):
        return lower

    raise ValidationError(f"Unknown language: {raw}. Pick a language from the list.")


def validate_language_pair(language_pair: str) -> str:
    pair = normalize_language_pair(language_pair)
    if not pair:
        raise ValidationError("Please select both languages.")
    if not LANGUAGE_PAIR_PATTERN.fullmatch(pair):
        raise ValidationError(
            "Invalid language pair. Choose two different languages, e.g. English and Hungarian."
        )
    left, right = pair.split("-")
    if left == right:
        raise ValidationError("Please choose two different languages.")
    return pair


def validate_language_selection(lang_a: str, lang_b: str) -> str:
    """Build and validate a pair from two dropdown values (codes or names)."""
    code_a = resolve_language_code(lang_a)
    code_b = resolve_language_code(lang_b)
    if code_a == code_b:
        raise ValidationError("Please choose two different languages.")
    return f"{code_a}-{code_b}"


def validate_text(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValidationError("Please enter some text to proofread and translate.")
    return cleaned


def validate_inputs(text: str, language_pair: str) -> tuple[str, str]:
    """Return cleaned text and normalized language pair, or raise ValidationError."""
    return validate_text(text), validate_language_pair(language_pair)


def validate_inputs_from_languages(
    text: str, lang_a: str, lang_b: str
) -> tuple[str, str]:
    """Return cleaned text and pair built from two language fields."""
    return validate_text(text), validate_language_selection(lang_a, lang_b)
