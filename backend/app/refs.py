"""Scripture reference parsing and formatting.

Turns what people type -- "alma 32:21", "1 Ne. 3:7", "D&C 4:2-4", "Heb 11" --
into verse id ranges, and turns verse id ranges back into labels.

The book lookup table is built once from the database, so every title, short
title and URL slug works as a name, plus a few common extras below.
"""

import re
import sqlite3
from dataclasses import dataclass

EXTRA_ALIASES = {
    "dc": "dc", "d&c": "dc", "doctrine&covenants": "dc",
    "psalm": "ps", "psa": "ps", "songofsongs": "song",
    "jsh": "js-h", "jsm": "js-m", "aoff": "a-of-f", "wofm": "w-of-m",
    "1nep": "1-ne", "2nep": "2-ne", "3nep": "3-ne", "4nep": "4-ne",
}

# "<book> <chapter>[:<verse>[-<verse>]]"
REF_RE = re.compile(
    r"^\s*(?P<book>\d?\s*[^\d].*?)\s*(?P<ch>\d+)"
    r"(?:\s*:\s*(?P<v1>\d+)(?:\s*[-–—]\s*(?P<v2>\d+))?)?\s*$"
)


def key(name: str) -> str:
    """Normalize a book name for lookup: '1 Ne.' -> '1ne', 'D&C' -> 'd&c'."""
    return re.sub(r"[^a-z0-9&]", "", name.lower().replace("—", ""))


def display_title(title: str) -> str:
    return "D&C" if title == "Doctrine and Covenants" else title


@dataclass
class Book:
    id: int
    slug: str
    volume: str
    title: str
    chapters: int


@dataclass
class Ref:
    start_verse_id: int
    end_verse_id: int
    label: str
    volume: str
    book: str
    chapter: int
    verse: int | None


class RefIndex:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.books: dict[int, Book] = {}
        self.by_key: dict[str, Book] = {}
        rows = conn.execute(
            "SELECT b.id, b.slug, b.title, b.short_title, v.slug AS volume,"
            "       (SELECT COUNT(*) FROM chapters c WHERE c.book_id = b.id) AS chapters"
            " FROM books b JOIN volumes v ON v.id = b.volume_id ORDER BY b.position")
        slug_to_book = {}
        for r in rows:
            b = Book(r["id"], r["slug"], r["volume"], r["title"], r["chapters"])
            self.books[b.id] = b
            slug_to_book[b.slug] = b
            for name in (r["title"], r["short_title"], r["slug"]):
                self.by_key.setdefault(key(name), b)
        for alias, slug in EXTRA_ALIASES.items():
            if slug in slug_to_book:
                self.by_key.setdefault(alias, slug_to_book[slug])
        self._ordered_keys = sorted(self.by_key)

    # -- lookups ------------------------------------------------------------
    def find_book(self, name: str) -> Book | None:
        k = key(name)
        if not k:
            return None
        if k in self.by_key:
            return self.by_key[k]
        matches = {self.by_key[x].id: self.by_key[x] for x in self._ordered_keys if x.startswith(k)}
        return next(iter(matches.values())) if len(matches) == 1 else None

    def suggest_books(self, prefix: str, limit: int = 8) -> list[Book]:
        k = key(prefix)
        starts, contains = [], []
        for b in self.books.values():  # canon order
            names = [key(b.title), b.slug.replace("-", "")]
            if any(n.startswith(k) for n in names):
                starts.append(b)
            elif k and k in key(b.title):
                contains.append(b)
        return (starts + contains)[:limit]

    # -- parsing ------------------------------------------------------------
    def parse(self, text: str) -> Ref | None:
        m = REF_RE.match(text or "")
        if not m:
            return None
        book = self.find_book(m["book"])
        if not book:
            return None
        ch = int(m["ch"])
        v1 = int(m["v1"]) if m["v1"] else None
        v2 = int(m["v2"]) if m["v2"] else None
        rows = self.conn.execute(
            "SELECT MIN(v.id), MAX(v.id), MAX(v.number) FROM verses v"
            " JOIN chapters c ON c.id = v.chapter_id WHERE c.book_id = ? AND c.number = ?",
            (book.id, ch)).fetchone()
        first_id, last_id, last_num = rows
        if first_id is None:
            return None
        if v1 is None:
            start, end = first_id, last_id
        else:
            if not 1 <= v1 <= last_num:
                return None
            v2 = min(v2 or v1, last_num)
            if v2 < v1:
                v1, v2 = v2, v1
            start, end = first_id + v1 - 1, first_id + v2 - 1
        return Ref(start, end, self.label(start, end), book.volume, book.slug, ch, v1)

    # -- formatting ---------------------------------------------------------
    def _where(self, verse_id: int):
        return self.conn.execute(
            "SELECT c.book_id, c.number AS ch, v.number AS vs,"
            " (SELECT MAX(number) FROM verses WHERE chapter_id = c.id) AS last"
            " FROM verses v JOIN chapters c ON c.id = v.chapter_id WHERE v.id = ?",
            (verse_id,)).fetchone()

    def label(self, start_id: int, end_id: int) -> str:
        a, b = self._where(start_id), self._where(end_id)
        title = display_title(self.books[a["book_id"]].title)
        if a["book_id"] == b["book_id"] and a["ch"] == b["ch"]:
            if a["vs"] == 1 and b["vs"] == b["last"] and start_id != end_id:
                return f"{title} {a['ch']}"
            if start_id == end_id:
                return f"{title} {a['ch']}:{a['vs']}"
            return f"{title} {a['ch']}:{a['vs']}–{b['vs']}"
        end_title = display_title(self.books[b["book_id"]].title)
        if a["book_id"] == b["book_id"]:
            return f"{title} {a['ch']}:{a['vs']}–{b['ch']}:{b['vs']}"
        return f"{title} {a['ch']}:{a['vs']} – {end_title} {b['ch']}:{b['vs']}"

    def describe(self, start_id: int, end_id: int) -> dict:
        """Everything the UI needs to show and open a range."""
        a = self._where(start_id)
        book = self.books[a["book_id"]]
        text = " ".join(r[0] for r in self.conn.execute(
            "SELECT text FROM verses WHERE id BETWEEN ? AND ? ORDER BY id LIMIT 4",
            (start_id, end_id)))
        return {
            "start_verse_id": start_id, "end_verse_id": end_id,
            "label": self.label(start_id, end_id),
            "volume": book.volume, "book": book.slug, "chapter": a["ch"], "verse": a["vs"],
            "text": text if len(text) <= 280 else text[:277].rsplit(" ", 1)[0] + "…",
        }
