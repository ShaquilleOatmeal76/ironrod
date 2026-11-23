"""Turning what someone types into a safe SQLite full-text (FTS5) query.

FTS5 has its own query language (AND, OR, NEAR, quotes, *, column filters...).
If we passed user text straight in, a stray quote or a word like "NOT" would
throw an error or change the meaning. So we rebuild the query ourselves:

    faith hope        ->  "faith" "hope"*        (both words; last one is a prefix)
    "perfect love"    ->  "perfect love"         (exact phrase)
    faith "not seen"  ->  "faith" "not seen"
"""

import re

_TOKEN = re.compile(r'"([^"]+)"|(\S+)')
_WORD = re.compile(r"[\w'’-]+", re.UNICODE)


def fts_query(text: str) -> str | None:
    parts: list[str] = []
    tokens = list(_TOKEN.finditer(text or ""))
    for i, m in enumerate(tokens):
        if m.group(1):  # quoted phrase
            words = _WORD.findall(m.group(1))
            if words:
                parts.append('"' + " ".join(words) + '"')
        else:
            for w in _WORD.findall(m.group(2)):
                w = w.strip("'’-")
                if w:
                    parts.append(f'"{w}"')
            # prefix-match the word still being typed
            if i == len(tokens) - 1 and parts and parts[-1].startswith('"') and " " not in parts[-1]:
                parts[-1] += "*"
    return " ".join(parts) or None


MARK_START, MARK_END = "⁣[[", "]]⁣"   # invisible separator + brackets


def marks_to_parts(snippet: str) -> list[dict]:
    """Split an FTS snippet into [{text, hit}] so the UI can bold matches
    without rendering any HTML."""
    out = []
    for i, chunk in enumerate(re.split(re.escape(MARK_START) + "|" + re.escape(MARK_END), snippet)):
        if chunk:
            out.append({"text": chunk, "hit": i % 2 == 1})
    return out
