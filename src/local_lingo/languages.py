"""Supported languages for the translator UI."""

from __future__ import annotations

# Display name -> ISO 639-1 code
LANGUAGES: dict[str, str] = {
    "Afrikaans": "af",
    "Arabic": "ar",
    "Bulgarian": "bg",
    "Catalan": "ca",
    "Chinese (Simplified)": "zh",
    "Croatian": "hr",
    "Czech": "cs",
    "Danish": "da",
    "Dutch": "nl",
    "English": "en",
    "Estonian": "et",
    "Finnish": "fi",
    "French": "fr",
    "German": "de",
    "Greek": "el",
    "Hebrew": "he",
    "Hindi": "hi",
    "Hungarian": "hu",
    "Indonesian": "id",
    "Italian": "it",
    "Japanese": "ja",
    "Korean": "ko",
    "Latvian": "lv",
    "Lithuanian": "lt",
    "Norwegian": "no",
    "Polish": "pl",
    "Portuguese": "pt",
    "Romanian": "ro",
    "Russian": "ru",
    "Slovak": "sk",
    "Slovenian": "sl",
    "Spanish": "es",
    "Swedish": "sv",
    "Thai": "th",
    "Turkish": "tr",
    "Ukrainian": "uk",
    "Vietnamese": "vi",
}

# Dropdown choices: (label shown in UI, value stored)
LANGUAGE_CHOICES: list[tuple[str, str]] = [
    (name, code) for name, code in sorted(LANGUAGES.items(), key=lambda item: item[0])
]

CODE_TO_NAME: dict[str, str] = {code: name for name, code in LANGUAGES.items()}


def name_for_code(code: str) -> str:
    return CODE_TO_NAME.get((code or "").lower(), code or "")


def codes_from_default_pair(pair: str) -> tuple[str, str]:
    left, right = (pair or "en-es").lower().replace("_", "-").split("-", 1)
    return left, right
