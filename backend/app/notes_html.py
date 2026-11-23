"""Cleaning and reading the HTML that the note editor sends.

Notes are rich text, so they arrive as HTML. HTML from a browser is untrusted:
someone could send <script> or <img onerror=...> and it would run for anyone
who views the note (stored XSS). So every note goes through an allowlist
sanitizer (nh3) before it is saved: only the tags and attributes the editor
actually produces survive. Everything else is stripped.
"""

from html.parser import HTMLParser

import nh3

ALLOWED_TAGS = {"p", "br", "strong", "em", "s", "code", "h2", "h3",
                "ul", "ol", "li", "blockquote", "span"}
ALLOWED_ATTRS = {"span": {"data-type", "data-id", "data-label", "data-start", "data-end"}}


def sanitize(html: str) -> str:
    return nh3.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, link_rel=None)


class _Reader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text: list[str] = []
        self.refs: list[tuple[int, int]] = []
        self.tags: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("p", "li", "h2", "h3", "blockquote", "br") and self.text:
            self.text.append("\n")
        if tag != "span":
            return
        if a.get("data-type") == "verseRef":
            try:
                start, end = int(a.get("data-start", "")), int(a.get("data-end", ""))
            except ValueError:
                return
            if 0 < start <= end:
                self.refs.append((start, end))
        elif a.get("data-type") == "tag" and a.get("data-id"):
            self.tags.append(a["data-id"])

    def handle_data(self, data):
        self.text.append(data)


def read(html: str) -> dict:
    """Plain text, @verse references and #tags found in sanitized note HTML."""
    r = _Reader()
    r.feed(html)
    text = "".join(r.text).strip()
    tags = sorted({t.strip().lstrip("#").lower() for t in r.tags if t.strip().lstrip("#")})
    return {"text": text, "refs": sorted(set(r.refs)), "tags": tags}
