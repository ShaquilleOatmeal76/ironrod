"""Markup endpoints: references, highlights, notes, tags and links."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app import notes_html
from app.deps import get_conn, get_refs, get_user_id

router = APIRouter(prefix="/api", tags=["markup"])

COLORS = ("promise", "christ", "doctrine", "question")
MAX_NOTE_HTML = 50_000


# --- helpers -------------------------------------------------------------
def _check_range(conn, start: int | None, end: int | None, required=True):
    if start is None and end is None and not required:
        return None, None
    if start is None or end is None or end < start:
        raise HTTPException(422, "Invalid verse range")
    if conn.execute("SELECT COUNT(*) FROM verses WHERE id IN (?, ?)", (start, end)).fetchone()[0] != (1 if start == end else 2):
        raise HTTPException(422, "Unknown verse")
    return start, end


def _chapter_bounds(conn, volume, book, chapter):
    row = conn.execute(
        "SELECT MIN(vs.id), MAX(vs.id) FROM verses vs JOIN chapters c ON c.id = vs.chapter_id"
        " JOIN books b ON b.id = c.book_id JOIN volumes v ON v.id = b.volume_id"
        " WHERE v.slug = ? AND b.slug = ? AND c.number = ?", (volume, book, chapter)).fetchone()
    if row[0] is None:
        raise HTTPException(404, "Chapter not found")
    return row


def _note_dict(conn, refs, row, relation="on"):
    tags = [r[0] for r in conn.execute(
        "SELECT t.name FROM note_tags nt JOIN tags t ON t.id = nt.tag_id WHERE nt.note_id = ? ORDER BY t.name",
        (row["id"],))]
    mentions = [refs.describe(r[0], r[1]) for r in conn.execute(
        "SELECT start_verse_id, end_verse_id FROM note_refs WHERE note_id = ? ORDER BY start_verse_id",
        (row["id"],))]
    anchor = refs.describe(row["start_verse_id"], row["end_verse_id"]) if row["start_verse_id"] else None
    return {
        "id": row["id"], "html": row["body_html"], "text": row["body_text"], "tags": tags,
        "anchor": anchor, "mentions": mentions, "relation": relation,
        "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


def _save_note_parts(conn, note_id: int, parsed: dict):
    conn.execute("DELETE FROM note_refs WHERE note_id = ?", (note_id,))
    conn.execute("DELETE FROM note_tags WHERE note_id = ?", (note_id,))
    valid_max = conn.execute("SELECT MAX(id) FROM verses").fetchone()[0]
    for start, end in parsed["refs"]:
        if end <= valid_max:
            conn.execute("INSERT OR IGNORE INTO note_refs VALUES (?, ?, ?)", (note_id, start, end))
    for name in parsed["tags"]:
        name = name[:40]
        conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
        tag_id = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()[0]
        conn.execute("INSERT OR IGNORE INTO note_tags VALUES (?, ?)", (note_id, tag_id))


# --- references ------------------------------------------------------------
@router.get("/refs/resolve")
def resolve_ref(q: str, refs=Depends(get_refs)):
    ref = refs.parse(q)
    if not ref:
        raise HTTPException(404, "Couldn't read that reference")
    return refs.describe(ref.start_verse_id, ref.end_verse_id)


@router.get("/refs/suggest")
def suggest_refs(q: str = "", refs=Depends(get_refs)):
    """Autocomplete for @references: a full match, or books to finish typing."""
    ref = refs.parse(q)
    if ref:
        return {"refs": [refs.describe(ref.start_verse_id, ref.end_verse_id)], "books": []}
    books = refs.suggest_books(q.strip()) if q.strip() else []
    return {"refs": [], "books": [{"title": b.title, "slug": b.slug, "chapters": b.chapters} for b in books]}


# --- chapter overview --------------------------------------------------------
@router.get("/annotations/{volume}/{book}/{chapter}")
def chapter_annotations(volume: str, book: str, chapter: int, conn=Depends(get_conn),
                        user_id=Depends(get_user_id)):
    """Per-verse highlight color and note/link counts, keyed by verse number."""
    first, last = _chapter_bounds(conn, volume, book, chapter)
    out: dict[int, dict] = {}

    def slot(verse_id):
        return out.setdefault(verse_id - first + 1, {"highlight": None, "notes": 0, "links": 0})

    for h in conn.execute(
            "SELECT start_verse_id, end_verse_id, color FROM highlights"
            " WHERE owner_id = ? AND start_verse_id <= ? AND end_verse_id >= ? ORDER BY id",
            (user_id, last, first)):
        for vid in range(max(h[0], first), min(h[1], last) + 1):
            slot(vid)["highlight"] = h[2]

    note_ranges = conn.execute(
        "SELECT id, start_verse_id, end_verse_id FROM notes WHERE start_verse_id <= ? AND end_verse_id >= ?"
        " UNION SELECT note_id, start_verse_id, end_verse_id FROM note_refs"
        " WHERE start_verse_id <= ? AND end_verse_id >= ?", (last, first, last, first)).fetchall()
    counted = set()
    for note_id, s, e in note_ranges:
        for vid in range(max(s, first), min(e, last) + 1):
            if (note_id, vid) not in counted:
                counted.add((note_id, vid))
                slot(vid)["notes"] += 1

    for s1, e1, s2, e2 in conn.execute(
            "SELECT a_start_verse_id, a_end_verse_id, b_start_verse_id, b_end_verse_id FROM links"
            " WHERE (a_start_verse_id <= ? AND a_end_verse_id >= ?) OR (b_start_verse_id <= ? AND b_end_verse_id >= ?)",
            (last, first, last, first)):
        touched = set(range(max(s1, first), min(e1, last) + 1)) | set(range(max(s2, first), min(e2, last) + 1))
        for vid in touched:
            slot(vid)["links"] += 1
    return out


# --- one verse in detail -------------------------------------------------------
@router.get("/verses/{verse_id}")
def verse_details(verse_id: int, conn=Depends(get_conn), refs=Depends(get_refs),
                  user_id=Depends(get_user_id)):
    _check_range(conn, verse_id, verse_id)
    hl = conn.execute(
        "SELECT color FROM highlights WHERE owner_id = ? AND start_verse_id <= ? AND end_verse_id >= ?"
        " ORDER BY id DESC LIMIT 1", (user_id, verse_id, verse_id)).fetchone()
    on = conn.execute(
        "SELECT * FROM notes WHERE start_verse_id <= ? AND end_verse_id >= ? ORDER BY created_at DESC",
        (verse_id, verse_id)).fetchall()
    mentioned = conn.execute(
        "SELECT n.* FROM notes n JOIN note_refs r ON r.note_id = n.id"
        " WHERE r.start_verse_id <= ? AND r.end_verse_id >= ? AND n.id NOT IN"
        " (SELECT id FROM notes WHERE start_verse_id <= ? AND end_verse_id >= ?)"
        " GROUP BY n.id ORDER BY n.created_at DESC", (verse_id, verse_id, verse_id, verse_id)).fetchall()
    links = []
    for l in conn.execute(
            "SELECT * FROM links WHERE (a_start_verse_id <= ? AND a_end_verse_id >= ?)"
            " OR (b_start_verse_id <= ? AND b_end_verse_id >= ?) ORDER BY created_at DESC",
            (verse_id, verse_id, verse_id, verse_id)):
        on_a = l["a_start_verse_id"] <= verse_id <= l["a_end_verse_id"]
        other = (l["b_start_verse_id"], l["b_end_verse_id"]) if on_a else (l["a_start_verse_id"], l["a_end_verse_id"])
        links.append({"id": l["id"], "label": l["label"], "other": refs.describe(*other)})
    return {
        "ref": refs.describe(verse_id, verse_id),
        "highlight": hl[0] if hl else None,
        "notes": [_note_dict(conn, refs, n, "on") for n in on]
                 + [_note_dict(conn, refs, n, "mentions") for n in mentioned],
        "links": links,
    }


# --- highlights ----------------------------------------------------------------
class HighlightIn(BaseModel):
    start_verse_id: int
    end_verse_id: int
    color: str | None = None   # None removes the highlight


@router.put("/highlights")
def set_highlight(body: HighlightIn, conn=Depends(get_conn), user_id=Depends(get_user_id)):
    _check_range(conn, body.start_verse_id, body.end_verse_id)
    if body.color is not None and body.color not in COLORS:
        raise HTTPException(422, f"color must be one of {', '.join(COLORS)}")
    with conn:
        conn.execute(
            "DELETE FROM highlights WHERE owner_id = ? AND start_verse_id <= ? AND end_verse_id >= ?",
            (user_id, body.end_verse_id, body.start_verse_id))
        if body.color:
            conn.execute(
                "INSERT INTO highlights (owner_id, start_verse_id, end_verse_id, color) VALUES (?, ?, ?, ?)",
                (user_id, body.start_verse_id, body.end_verse_id, body.color))
    return {"color": body.color}


# --- notes ---------------------------------------------------------------------
class NoteIn(BaseModel):
    body_html: str = Field(max_length=MAX_NOTE_HTML)
    start_verse_id: int | None = None
    end_verse_id: int | None = None


class NotePatch(BaseModel):
    body_html: str = Field(max_length=MAX_NOTE_HTML)


@router.get("/notes")
def list_notes(q: str | None = None, tag: str | None = None, limit: int = Query(50, le=200),
               conn=Depends(get_conn), refs=Depends(get_refs)):
    sql, args = "SELECT n.* FROM notes n", []
    where = []
    if tag:
        sql += " JOIN note_tags nt ON nt.note_id = n.id JOIN tags t ON t.id = nt.tag_id"
        where.append("t.name = ?")
        args.append(tag.lstrip("#"))
    if q and q.strip():
        where.append("n.id IN (SELECT rowid FROM notes_fts WHERE notes_fts MATCH ?)")
        # quote each word so punctuation can't break the FTS query syntax
        args.append(" ".join('"' + w.replace('"', "") + '"*' for w in q.split()))
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY n.updated_at DESC, n.id DESC LIMIT ?"
    args.append(limit)
    return [_note_dict(conn, refs, n) for n in conn.execute(sql, args)]


@router.post("/notes", status_code=201)
def create_note(body: NoteIn, conn=Depends(get_conn), refs=Depends(get_refs),
                user_id=Depends(get_user_id)):
    start, end = _check_range(conn, body.start_verse_id, body.end_verse_id, required=False)
    html = notes_html.sanitize(body.body_html)
    parsed = notes_html.read(html)
    if not parsed["text"]:
        raise HTTPException(422, "Note is empty")
    with conn:
        cur = conn.execute(
            "INSERT INTO notes (owner_id, start_verse_id, end_verse_id, body_html, body_text)"
            " VALUES (?, ?, ?, ?, ?)", (user_id, start, end, html, parsed["text"]))
        _save_note_parts(conn, cur.lastrowid, parsed)
    return _note_dict(conn, refs, conn.execute("SELECT * FROM notes WHERE id = ?", (cur.lastrowid,)).fetchone())


def _own_note(conn, note_id, user_id):
    row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if row is None or row["owner_id"] != user_id:
        raise HTTPException(404, "Note not found")
    return row


@router.patch("/notes/{note_id}")
def update_note(note_id: int, body: NotePatch, conn=Depends(get_conn), refs=Depends(get_refs),
                user_id=Depends(get_user_id)):
    _own_note(conn, note_id, user_id)
    html = notes_html.sanitize(body.body_html)
    parsed = notes_html.read(html)
    if not parsed["text"]:
        raise HTTPException(422, "Note is empty")
    with conn:
        conn.execute("UPDATE notes SET body_html = ?, body_text = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                     (html, parsed["text"], note_id))
        _save_note_parts(conn, note_id, parsed)
    return _note_dict(conn, refs, conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone())


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int, conn=Depends(get_conn), user_id=Depends(get_user_id)):
    _own_note(conn, note_id, user_id)
    with conn:
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))


@router.get("/tags")
def list_tags(q: str = "", conn=Depends(get_conn)):
    return [{"name": r[0], "count": r[1]} for r in conn.execute(
        "SELECT t.name, COUNT(nt.note_id) FROM tags t LEFT JOIN note_tags nt ON nt.tag_id = t.id"
        " WHERE t.name LIKE ? GROUP BY t.id HAVING COUNT(nt.note_id) > 0 ORDER BY COUNT(nt.note_id) DESC, t.name LIMIT 20",
        (q.lstrip("#") + "%",))]


# --- links -----------------------------------------------------------------------
LINK_LABELS = ("related", "same principle", "expands on", "contrast", "fulfillment", "example")


class LinkIn(BaseModel):
    from_start_verse_id: int
    from_end_verse_id: int
    to: str | None = None                 # a typed reference, e.g. "Hebrews 11:1"
    to_start_verse_id: int | None = None  # ...or explicit ids
    to_end_verse_id: int | None = None
    label: str = "related"


@router.get("/links/labels")
def link_labels():
    return LINK_LABELS


@router.post("/links", status_code=201)
def create_link(body: LinkIn, conn=Depends(get_conn), refs=Depends(get_refs),
                user_id=Depends(get_user_id)):
    a = _check_range(conn, body.from_start_verse_id, body.from_end_verse_id)
    if body.to:
        ref = refs.parse(body.to)
        if not ref:
            raise HTTPException(422, "Couldn't read that reference")
        b = (ref.start_verse_id, ref.end_verse_id)
    else:
        b = _check_range(conn, body.to_start_verse_id, body.to_end_verse_id)
    if a == b:
        raise HTTPException(422, "A verse can't link to itself")
    label = body.label.strip().lower()[:40] or "related"
    with conn:
        cur = conn.execute(
            "INSERT INTO links (owner_id, a_start_verse_id, a_end_verse_id, b_start_verse_id, b_end_verse_id, label)"
            " VALUES (?, ?, ?, ?, ?, ?)", (user_id, *a, *b, label))
    return {"id": cur.lastrowid, "label": label, "other": refs.describe(*b)}


@router.delete("/links/{link_id}", status_code=204)
def delete_link(link_id: int, conn=Depends(get_conn), user_id=Depends(get_user_id)):
    row = conn.execute("SELECT owner_id FROM links WHERE id = ?", (link_id,)).fetchone()
    if row is None or row[0] != user_id:
        raise HTTPException(404, "Link not found")
    with conn:
        conn.execute("DELETE FROM links WHERE id = ?", (link_id,))
