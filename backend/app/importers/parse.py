"""HTML -> paragraphs. Pure functions (no network), so they're easy to test.

Page structure notes (from the sites' current markup and from other
open-source importers that track it):

churchofjesuschrist.org content API
  GET /study/api/v3/language-pages/type/content?lang=eng&uri=<uri>
  -> {"content": {"body": "<html…>"}, "meta": {...}}
  Talk body: <header> with h1, p.author-name, p.author-role, p.kicker;
  paragraphs are <p id="p1"> (older) or <p id="p_aB3dE"> (newer);
  footnote markers are <sup class="marker">; notes live in <footer>.
  A conference page lists its talks as links to
  /study/general-conference/<year>/<month>/<slug>.
  A manual's contents page lists its pages as <a class="list-tile"> with p.title.

speeches.byu.edu
  Static HTML. Transcript in .single-speech__content (older template) or
  .individual-speech__content (2026 template).
"""

import re
from datetime import date, datetime

from bs4 import BeautifulSoup, Tag

MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]

_SKIP_CLASSES = {"author-name", "author-role", "kicker", "title", "title-number",
                 "study-summary", "intro", "figcaption", "caption", "reference",
                 "short-reference", "image-credit", "credit"}
_BLOCK_TAGS = ("h2", "h3", "p", "li", "blockquote")


def _text(el: Tag) -> str:
    for sup in el.select("sup.marker, sup.footnote, sup"):
        sup.decompose()
    t = el.get_text(" ", strip=True).replace("\xa0", " ")
    t = re.sub(r"\s+([,.;:!?”’)])", r"\1", t)   # "word ," -> "word,"
    t = re.sub(r"([“‘(])\s+", r"\1", t)
    return re.sub(r"\s{2,}", " ", t).strip()


def blocks(root: Tag) -> list[tuple[str, str]]:
    """Readable blocks in document order: [(kind, text)] with kind in
    p / h2 / h3 / li / quote. Skips headers, footers, figures and notes."""
    out: list[tuple[str, str]] = []
    for el in root.find_all(_BLOCK_TAGS):
        if el.find_parent(["header", "footer", "figure", "nav", "aside"]):
            continue
        if set(el.get("class") or []) & _SKIP_CLASSES:
            continue
        # don't double-count: a <p> inside an <li>/<blockquote> is emitted by the parent
        if el.name == "p" and el.find_parent(["li", "blockquote"]):
            continue
        if el.name in ("li", "blockquote") and el.find_parent(["li", "blockquote"]):
            continue
        text = _text(el)
        if not text or text.startswith("©"):
            continue
        kind = {"blockquote": "quote"}.get(el.name, el.name)
        out.append((kind, text))
    return out


def _first(soup, selectors: str) -> str | None:
    el = soup.select_one(selectors)
    return _text(el) if el else None


# --- conference ------------------------------------------------------------------
def conference_talk_uris(body_html: str, year: int, month: str) -> list[str]:
    soup = BeautifulSoup(body_html, "html.parser")
    prefix = f"/study/general-conference/{year}/{month}/"
    seen, out = set(), []
    for a in soup.select("a[href]"):
        href = a["href"].split("?")[0].split("#")[0]
        if not href.startswith(prefix):
            continue
        slug = href[len(prefix):]
        if not slug or "/" in slug or slug == "media" or slug.endswith(("session", "meeting")):
            continue
        uri = f"/general-conference/{year}/{month}/{slug}"
        if uri not in seen:
            seen.add(uri)
            out.append(uri)
    return out


def church_page(body_html: str) -> dict:
    """Title, author, role and paragraphs from a content-API body."""
    soup = BeautifulSoup(body_html, "html.parser")
    title = _first(soup, "h1") or ""
    author = _first(soup, ".author-name")
    role = _first(soup, ".author-role")
    kicker = _first(soup, ".kicker")
    root = soup.select_one(".body-block") or soup
    return {"title": title, "author": _clean_author(author), "author_role": role,
            "kicker": kicker, "blocks": blocks(root)}


def _clean_author(name: str | None) -> str | None:
    if not name:
        return None
    return re.sub(r"^By\s+", "", name).strip()


# --- Come Follow Me ---------------------------------------------------------------
def manual_toc(body_html: str) -> list[dict]:
    """Pages listed in a manual's table of contents: [{uri, title, subtitle}]."""
    soup = BeautifulSoup(body_html, "html.parser")
    out, seen = [], set()
    for a in soup.select("a.list-tile, a[href*='/study/manual/']"):
        m = re.search(r"/study(/manual/[^?#\"]+)", a.get("href", ""))
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        title = _first(a, "p.title") or _text(a)
        subtitle = _first(a, "p.subtitle, p.title-number, p.primary-meta")
        out.append({"uri": m.group(1), "title": title, "subtitle": subtitle})
    return out


_DATE_RANGE = re.compile(
    r"^\s*(?P<m1>[A-Z][a-z]+)\s+(?P<d1>\d{1,2})\s*[–—-]\s*"
    r"(?:(?P<m2>[A-Z][a-z]+)\s+)?(?P<d2>\d{1,2})\s*(?::\s*(?P<rest>.*))?$"
)


def parse_week(title: str, manual_year: int, first_lesson: bool = False):
    """'December 29–January 4: Genesis 1' -> (date, date, 'Genesis 1') or None."""
    m = _DATE_RANGE.match(title or "")
    if not m or m["m1"].lower() not in MONTHS:
        return None
    m1 = MONTHS.index(m["m1"].lower()) + 1
    m2 = MONTHS.index(m["m2"].lower()) + 1 if m["m2"] and m["m2"].lower() in MONTHS else m1
    y1 = manual_year - 1 if (m1 == 12 and first_lesson) else manual_year
    y2 = y1 + 1 if m2 < m1 else y1
    try:
        start, end = date(y1, m1, int(m["d1"])), date(y2, m2, int(m["d2"]))
    except ValueError:
        return None
    return start, end, (m["rest"] or "").strip()


# --- BYU speeches -----------------------------------------------------------------
_BYU_CONTENT = ".single-speech__content, .individual-speech__content"
_BYU_DATE_FORMATS = ("%B %d, %Y", "%d %b %Y", "%d %B %Y", "%b %d, %Y")


def byu_speech(html: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one(_BYU_CONTENT)
    if not content:
        return None
    text = content.get_text(" ", strip=True).lower()
    unavailable = "single-speech__unavailable-message" in (content.get("class") or []) or \
        "text for this speech is unavailable" in text or "text of this speech is being edited" in text
    raw_date = _first(soup, ".single-speech__date, .individual-speech__date")
    published = None
    for fmt in _BYU_DATE_FORMATS:
        try:
            published = datetime.strptime(raw_date or "", fmt).date()
            break
        except ValueError:
            continue
    return {
        "title": _first(soup, ".single-speech__title, .individual-speech__title") or "",
        "author": _first(soup, ".single-speech__speaker, .individual-speech__speakers"),
        "author_role": _first(soup, ".single-speech__speaker-position, .individual-speech__position"),
        "date_label": published.strftime("%B %-d, %Y") if published else raw_date,
        "published": published.isoformat() if published else None,
        "blocks": [] if unavailable else blocks(content),
    }
