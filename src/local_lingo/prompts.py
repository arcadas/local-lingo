import re

_FORMAT_LINE = re.compile(
    r"^(provided text|detected language|corrected|translation(\s*\([^)]*\))?)\s*:",
    re.IGNORECASE,
)
_FORMAT_PHRASE = re.compile(
    r"(?i)reply with exactly these (three|four) lines[^\n]*",
)
_START_PHRASE = re.compile(
    r"(?i)start your reply with (provided text|detected language):?[^\n]*",
)

DEFAULT_SYSTEM_GUIDELINES = """You proofread and translate between {name_a} and {name_b} only.

The user message is the complete task. Do not greet, confirm, explain, or wait for more input.

Rules:
- Detected language is the language the pasted text is written in. Pair order is not the direction.
- Corrected is a natural rewrite of the pasted text in that same language. Never translate in Corrected.
- If Detected language is {name_a}, Translation is {name_b}.
- If Detected language is {name_b}, Translation is {name_a}.
- Never swap Corrected and Translation.
- Keep Corrected approximately the same length as the original. Do not add explanations or extra details."""

DEFAULT_USER_EXTRA = ""

LOCKED_OUTPUT_FORMAT = """Reply with exactly these three lines and nothing else:
Detected language: {name_a} or {name_b}
Corrected: "<rewrite of the pasted text in that same language — not a translation>"
Translation (<the other language>): "<translation of Corrected>"
"""

LOCKED_USER_SUFFIX = "Start your reply with Detected language:"

_ADDON_LIMIT = 4000


def sanitize_prompt_addon(text: str) -> str:
    """Drop output-format lines so user edits cannot break parsing."""
    kept: list[str] = []
    for line in (text or "").splitlines():
        if _FORMAT_LINE.match(line.strip()):
            continue
        kept.append(line)
    cleaned = "\n".join(kept)
    cleaned = _FORMAT_PHRASE.sub("", cleaned)
    cleaned = _START_PHRASE.sub("", cleaned)
    cleaned = cleaned.strip()
    if len(cleaned) > _ADDON_LIMIT:
        cleaned = cleaned[:_ADDON_LIMIT]
    return cleaned


def _fill_names(template: str, name_a: str, name_b: str) -> str:
    return (
        (template or "")
        .replace("{name_a}", name_a)
        .replace("{name_b}", name_b)
    )


def build_system_prompt(
    name_a: str,
    name_b: str,
    guidelines: str | None = None,
) -> str:
    body = sanitize_prompt_addon(guidelines if guidelines is not None else DEFAULT_SYSTEM_GUIDELINES)
    if not body:
        body = DEFAULT_SYSTEM_GUIDELINES
    body = _fill_names(body, name_a, name_b)
    locked = _fill_names(LOCKED_OUTPUT_FORMAT, name_a, name_b)
    return f"{body}\n\n{locked}\n"


def build_user_prompt(
    text: str,
    name_a: str,
    name_b: str,
    extra: str | None = None,
) -> str:
    extra_clean = sanitize_prompt_addon(_fill_names(extra or "", name_a, name_b))
    extra_block = f"{extra_clean}\n\n" if extra_clean else ""
    return f"""{extra_block}Pasted text:
{text}

This text is written in {name_a} or {name_b}. Detect that language first.

{LOCKED_USER_SUFFIX}"""
