"""One search endpoint behind the command palette and the search page.

A single query is tried several ways at once:
  - as a scripture reference  ("alma 32:21" -> go straight there)
  - as book names              ("mos" -> Mosiah, Moses, Moroni...)
  - full-text over scripture   (ranked with bm25)
  - full-text over your notes
  - against tag names
"""

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.deps import get_conn, get_refs
from app.search import MARK_END, MARK_START, fts_query, marks_to_parts

router = APIRouter(prefix="/api", tags=["search"])

SCOPES = ("all", "ot", "nt", "bofm", "dc-testament", "pgp")


def _verses(conn, match, scope, limit, offset):
    where, args = "verses_fts MATCH ?", [match]
    if scope != "all":
        where += " AND vo.slug = ?"
        args.append(scope)
    base = (" FROM verses_fts JOIN verses v ON v.id = verses_fts.rowid"
            " JOIN chapters c ON c.id = v.chapter_id JOIN books b ON b.id = c.book_id"
            " JOIN volumes vo ON vo.id = b.volume_id WHERE " + where)
    total = conn.execute("SELECT COUNT(*)" + base, args).fetchone()[0]
    rows = conn.execute(
        "SELECT v.id, v.number, c.number AS chapter, b.slug AS book, b.title, vo.slug AS volume,"
        f" snippet(verses_fts, 0, '{MARK_START}', '{MARK_END}', '…', 18) AS snip"
        + base + " ORDER BY bm25(verses_fts), v.id LIMIT ? OFFSET ?",
        args + [limit, offset]).fetchall()
    items = []
    for r in rows:
        title = "D&C" if r["title"] == "Doctrine and Covenants" else r["title"]
        items.append({
            "start_verse_id": r["id"], "end_verse_id": r["id"],
            "label": f"{title} {r['chapter']}:{r['number']}",
            "volume": r["volume"], "book": r["book"], "chapter": r["chapter"], "verse": r["number"],
            "parts": marks_to_parts(r["snip"]),
        })
    return {"total": total, "items": items}


def _notes(conn, refs, match, limit, offset):
    total = conn.execute("SELECT COUNT(*) FROM notes_fts WHERE notes_fts MATCH ?", (match,)).fetchone()[0]
    rows = conn.execute(
        "SELECT n.id, n.start_verse_id, n.end_verse_id, n.updated_at,"
        f" snippet(notes_fts, 0, '{MARK_START}', '{MARK_END}', '…', 14) AS snip"
        " FROM notes_fts JOIN notes n ON n.id = notes_fts.rowid WHERE notes_fts MATCH ?"
        " ORDER BY bm25(notes_fts), n.updated_at DESC LIMIT ? OFFSET ?",
        (match, limit, offset)).fetchall()
    items = []
    for r in rows:
        tags = [t[0] for t in conn.execute(
            "SELECT t.name FROM note_tags nt JOIN tags t ON t.id = nt.tag_id WHERE nt.note_id = ?", (r["id"],))]
        items.append({
            "id": r["id"], "parts": marks_to_parts(r["snip"]), "tags": tags, "updated_at": r["updated_at"],
            "anchor": refs.describe(r["start_verse_id"], r["end_verse_id"]) if r["start_verse_id"] else None,
        })
    return {"total": total, "items": items}


@router.get("/search")
def search(
    q: str = "",
    scope: str = Query("all", pattern="^(" + "|".join(SCOPES) + ")$"),
    kinds: str = "ref,books,verses,notes,tags",
    limit: int = Query(6, ge=1, le=100),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_conn),
    refs=Depends(get_refs),
):
    want = set(kinds.split(","))
    q = q.strip()
    out: dict = {"q": q, "ref": None, "books": [], "verses": {"total": 0, "items": []},
                 "notes": {"total": 0, "items": []}, "tags": []}
    if not q:
        return out

    if "ref" in want:
        ref = refs.parse(q)
        if ref:
            out["ref"] = refs.describe(ref.start_verse_id, ref.end_verse_id)

    if "books" in want and not out["ref"] and len(q) >= 2 and not any(ch.isdigit() for ch in q[1:]):
        out["books"] = [{"title": b.title, "volume": b.volume, "book": b.slug, "chapters": b.chapters}
                        for b in refs.suggest_books(q, limit=4)]

    if "tags" in want:
        name = q.lstrip("#")
        if name:
            out["tags"] = [{"name": r[0], "count": r[1]} for r in conn.execute(
                "SELECT t.name, COUNT(nt.note_id) FROM tags t JOIN note_tags nt ON nt.tag_id = t.id"
                " WHERE t.name LIKE ? GROUP BY t.id ORDER BY COUNT(nt.note_id) DESC LIMIT 5", (name + "%",))]

    match = fts_query(q.lstrip("#"))
    if match:
        try:
            if "verses" in want:
                out["verses"] = _verses(conn, match, scope, limit, offset)
            if "notes" in want:
                out["notes"] = _notes(conn, refs, match, limit, offset)
        except sqlite3.OperationalError:
            pass  # a query FTS still can't parse just returns no text matches
    return out
