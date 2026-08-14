"""Highlight edits between original and corrected text."""

from __future__ import annotations

import html
import re
from difflib import SequenceMatcher

_TOKEN = re.compile(r"\s+|\w+|[^\s\w]", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text or "")


def highlight_corrections(original: str, corrected: str) -> str:
    """Return HTML for corrected text, with changed tokens wrapped in a highlight span."""
    corrected = corrected or ""
    if not corrected:
        return ""
    if (original or "") == corrected:
        return html.escape(corrected)

    original_tokens = tokenize(original)
    corrected_tokens = tokenize(corrected)
    matcher = SequenceMatcher(a=original_tokens, b=corrected_tokens, autojunk=False)

    parts: list[str] = []
    pending: list[str] = []
    pending_mark = False

    def flush() -> None:
        nonlocal pending_mark
        if not pending:
            return
        chunk = html.escape("".join(pending))
        if pending_mark:
            parts.append(f'<span class="diff-chg">{chunk}</span>')
        else:
            parts.append(chunk)
        pending.clear()
        pending_mark = False

    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        chunk = "".join(corrected_tokens[j1:j2])
        if not chunk:
            continue
        is_mark = tag != "equal" and not chunk.isspace()
        if pending and is_mark != pending_mark:
            flush()
        pending.append(chunk)
        pending_mark = is_mark
    flush()
    return "".join(parts)
