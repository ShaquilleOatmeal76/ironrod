"""Importers: fetch a source, parse it, save it.

Each importer takes a `report(done, total, message)` callback so the web app
can show progress, and skips anything already imported (re-running is safe).
"""

import calendar
import re
import sqlite3
from typing import Callable

from app.importers import fetch, parse
from app.refs import RefIndex, parse_many

CHURCH = "https://www.churchofjesuschrist.org"
CONTENT_API = CHURCH + "/study/api/v3/language-pages/type/content?lang=eng&uri="
BYU = "https://speeches.byu.edu"

# Come Follow Me rotates through the standard works every four years.
CFM_CYCLE = {0: "old-testament", 1: "new-testament", 2: "book-of-mormon", 3: "doctrine-and-covenants"}

Report = Callable[[int, int, str], None]


def _noop(done, total, msg):
    pass


def _church(uri: str) -> dict | None:
    return fetch.get_json(CONTENT_API + uri)


def _collection(conn, kind, slug, title, sort_key) -> int:
    conn.execute(
        "INSERT INTO collections (kind, slug, title, sort_key) VALUES (?, ?, ?, ?)"
        " ON CONFLICT(slug) DO UPDATE SET title = excluded.title, sort_key = excluded.sort_key",
        (kind, slug, title, sort_key))
    return conn.execute("SELECT id FROM collections WHERE slug = ?", (slug,)).fetchone()[0]


def _exists(conn, source_uri) -> bool:
    return conn.execute("SELECT 1 FROM docs WHERE source_uri = ?", (source_uri,)).fetchone() is not None


def save_doc(conn: sqlite3.Connection, collection_id: int, source_uri: str, source_url: str,
             page: dict, position: int, **extra) -> int:
    cols = {"collection_id": collection_id, "source_uri": source_uri, "source_url": source_url,
            "title": page.get("title") or "Untitled", "author": page.get("author"),
            "author_role": page.get("author_role"), "date_label": page.get("date_label"),
            "published": page.get("published"), "position": position, **extra}
    with conn:
        cur = conn.execute(
            f"INSERT INTO docs ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            list(cols.values()))
        doc_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO doc_paras (doc_id, position, kind, text) VALUES (?, ?, ?, ?)",
            [(doc_id, i + 1, k, t) for i, (k, t) in enumerate(page["blocks"])])
    return doc_id


# --- General Conference -------------------------------------------------------------
def conference(conn, year: int, month: int, report: Report = _noop) -> int:
    mm = f"{month:02d}"
    toc = _church(f"/general-conference/{year}/{mm}")
    if not toc:
        raise fetch.FetchError(f"No {calendar.month_name[month]} {year} conference found")
    uris = parse.conference_talk_uris(toc["content"]["body"], year, mm)
    if not uris:
        raise fetch.FetchError("Couldn't find any talks on the conference page")
    label = f"{calendar.month_name[month]} {year}"
    cid = _collection(conn, "conference", f"conference/{year}/{mm}", f"{label} General Conference", f"{year}-{mm}")
    added = 0
    for i, uri in enumerate(uris):
        report(i, len(uris), uri.rsplit("/", 1)[-1].replace("-", " "))
        if _exists(conn, uri):
            continue
        data = _church(uri)
        if not data:
            continue
        page = parse.church_page(data["content"]["body"])
        if not page["blocks"]:
            continue
        page["date_label"] = label
        page["published"] = f"{year}-{mm}-01"
        save_doc(conn, cid, uri, f"{CHURCH}/study{uri}?lang=eng", page, i + 1)
        added += 1
    report(len(uris), len(uris), f"{added} new talks")
    return added


# --- Come Follow Me -----------------------------------------------------------------
def cfm_manual_uri(year: int) -> str:
    return f"/manual/come-follow-me-for-home-and-church-{CFM_CYCLE[(year - 2022) % 4]}-{year}"


def come_follow_me(conn, refs: RefIndex, year: int, report: Report = _noop) -> int:
    manual = cfm_manual_uri(year)
    toc = _church(manual)
    if not toc:
        raise fetch.FetchError(f"No Come Follow Me manual found for {year}")
    entries = [e for e in parse.manual_toc(toc["content"]["body"]) if e["uri"].startswith(manual + "/")]
    lessons = []
    for e in entries:
        wk = parse.parse_week(e["title"], year, first_lesson=not lessons)
        if wk:
            lessons.append((e, wk))
    if not lessons:
        raise fetch.FetchError("Couldn't find the weekly lessons in the manual")
    book = CFM_CYCLE[(year - 2022) % 4].replace("-", " ").title()
    cid = _collection(conn, "cfm", f"cfm/{year}", f"Come Follow Me {year} — {book}", f"{year}")
    added = 0
    for i, (e, (start, end, rest)) in enumerate(lessons):
        report(i, len(lessons), e["title"][:60])
        if _exists(conn, e["uri"]):
            continue
        data = _church(e["uri"])
        if not data:
            continue
        page = parse.church_page(data["content"]["body"])
        reading, ranges = _reading(refs, [rest, e.get("subtitle"), page.get("kicker"), page["title"],
                                          *[t for _, t in page["blocks"][:4]]])
        page["title"] = _lesson_title(page["title"], e["title"])
        page["date_label"] = f"{start:%b} {start.day}–{end:%b} {end.day}"
        page["published"] = start.isoformat()
        doc_id = save_doc(conn, cid, e["uri"], f"{CHURCH}/study{e['uri']}?lang=eng", page, i + 1,
                          week_start=start.isoformat(), week_end=end.isoformat(), reading=reading)
        with conn:
            conn.executemany("INSERT OR IGNORE INTO doc_readings VALUES (?, ?, ?)",
                             [(doc_id, a, b) for a, b in ranges])
        added += 1
    report(len(lessons), len(lessons), f"{added} new lessons")
    return added


_WEEK_PREFIX = re.compile(r"^[A-Z][a-z]+ \d{1,2}\s*[\u2013\u2014-]\s*(?:[A-Z][a-z]+ )?\d{1,2}\s*:\s*")


def _reading(refs, candidates):
    """The first short line that reads entirely as scripture references."""
    for c in candidates:
        c = _WEEK_PREFIX.sub("", c or "").strip()
        if c and len(c) < 160:
            ranges = parse_many(refs, c)
            if ranges:
                return c, ranges
    return None, []


def _lesson_title(page_title: str, toc_title: str) -> str:
    return _WEEK_PREFIX.sub("", page_title or toc_title).strip() or toc_title


# --- BYU Speeches -------------------------------------------------------------------
_BYU_PATH = re.compile(r"^https://speeches\.byu\.edu/talks/[^/]+/[^/]+/?$")


def byu_speeches(conn, urls: list[str], report: Report = _noop) -> int:
    cid = _collection(conn, "byu", "byu", "BYU Speeches", "0000")
    clean = []
    for u in urls:
        u = u.strip().split("?")[0].split("#")[0]
        if u and not u.endswith("/"):
            u += "/"
        if _BYU_PATH.match(u):
            clean.append(u)
    if not clean:
        raise fetch.FetchError("Paste links like https://speeches.byu.edu/talks/<speaker>/<title>/")
    added = 0
    for i, url in enumerate(clean):
        report(i, len(clean), url.rstrip("/").rsplit("/", 1)[-1].replace("-", " "))
        if _exists(conn, url):
            continue
        html = fetch.get(url, accept="text/html")
        page = parse.byu_speech(html) if html else None
        if not page or not page["blocks"]:
            continue
        save_doc(conn, cid, url, url, page, 0)
        added += 1
    report(len(clean), len(clean), f"{added} new speeches")
    return added
