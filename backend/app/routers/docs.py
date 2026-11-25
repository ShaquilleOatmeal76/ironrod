"""Talks, speeches and lessons: browse, read, mark up, link, import."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.deps import get_conn, get_refs, get_user_id
from app.importers import jobs

router = APIRouter(prefix="/api", tags=["docs"])

KIND_TITLES = {"conference": "General Conference", "byu": "BYU Speeches", "cfm": "Come Follow Me"}


def doc_summary(row) -> dict:
    return {"id": row["id"], "title": row["title"], "author": row["author"],
            "author_role": row["author_role"], "date_label": row["date_label"],
            "kind": row["kind"], "collection": row["collection_title"],
            "reading": row["reading"], "week_start": row["week_start"], "week_end": row["week_end"]}


DOC_SELECT = ("SELECT d.*, c.kind, c.title AS collection_title FROM docs d"
              " JOIN collections c ON c.id = d.collection_id")


def para_ref(conn, para_id: int) -> dict | None:
    """Everything the UI needs to show and open a talk paragraph."""
    row = conn.execute(
        "SELECT p.id, p.position, p.text, d.id AS doc_id, d.title, d.author, c.kind"
        " FROM doc_paras p JOIN docs d ON d.id = p.doc_id JOIN collections c ON c.id = d.collection_id"
        " WHERE p.id = ?", (para_id,)).fetchone()
    if not row:
        return None
    text = row["text"] if len(row["text"]) <= 240 else row["text"][:237].rsplit(" ", 1)[0] + "…"
    who = f" — {row['author']}" if row["author"] else ""
    return {"para_id": row["id"], "doc_id": row["doc_id"], "position": row["position"],
            "kind": row["kind"], "doc_title": row["title"], "author": row["author"],
            "label": f"{row['title']}{who} ¶{row['position']}", "text": text}


# --- browse ---------------------------------------------------------------------
@router.get("/library")
def library(conn=Depends(get_conn)):
    groups = {k: {"kind": k, "title": t, "collections": []} for k, t in KIND_TITLES.items()}
    for c in conn.execute(
            "SELECT c.id, c.kind, c.slug, c.title, COUNT(d.id) AS docs FROM collections c"
            " LEFT JOIN docs d ON d.collection_id = c.id GROUP BY c.id ORDER BY c.sort_key DESC"):
        groups[c["kind"]]["collections"].append(dict(c))
    return list(groups.values())


@router.get("/collections/{collection_id}")
def collection(collection_id: int, conn=Depends(get_conn)):
    c = conn.execute("SELECT * FROM collections WHERE id = ?", (collection_id,)).fetchone()
    if not c:
        raise HTTPException(404, "Collection not found")
    order = "d.published DESC, d.title" if c["kind"] == "byu" else "d.position"
    docs = [doc_summary(r) for r in conn.execute(
        f"{DOC_SELECT} WHERE d.collection_id = ? ORDER BY {order}", (collection_id,))]
    return {"id": c["id"], "kind": c["kind"], "title": c["title"], "docs": docs}


@router.get("/docs/{doc_id}")
def read_doc(doc_id: int, conn=Depends(get_conn), refs=Depends(get_refs), user_id=Depends(get_user_id)):
    d = conn.execute(f"{DOC_SELECT} WHERE d.id = ?", (doc_id,)).fetchone()
    if not d:
        raise HTTPException(404, "Not found")
    paras = [dict(p) for p in conn.execute(
        "SELECT id, position, kind, text FROM doc_paras WHERE doc_id = ? ORDER BY position", (doc_id,))]
    ids = [p["id"] for p in paras]
    ann: dict[int, dict] = {}
    if ids:
        lo, hi = min(ids), max(ids)
        for pid, color in conn.execute(
                "SELECT para_id, color FROM para_highlights WHERE owner_id = ? AND para_id BETWEEN ? AND ?",
                (user_id, lo, hi)):
            ann.setdefault(pid, {"highlight": None, "notes": 0, "links": 0})["highlight"] = color
        for pid, n in conn.execute(
                "SELECT para_id, COUNT(*) FROM notes WHERE para_id BETWEEN ? AND ? GROUP BY para_id", (lo, hi)):
            ann.setdefault(pid, {"highlight": None, "notes": 0, "links": 0})["notes"] = n
        for pid, n in conn.execute(
                "SELECT para_id, COUNT(*) FROM para_links WHERE para_id BETWEEN ? AND ? GROUP BY para_id", (lo, hi)):
            ann.setdefault(pid, {"highlight": None, "notes": 0, "links": 0})["links"] = n
    for p in paras:
        p.update(ann.get(p["id"], {"highlight": None, "notes": 0, "links": 0}))
    readings = [refs.describe(a, b) for a, b in conn.execute(
        "SELECT start_verse_id, end_verse_id FROM doc_readings WHERE doc_id = ? ORDER BY start_verse_id", (doc_id,))]
    sib = conn.execute(
        "SELECT (SELECT id FROM docs WHERE collection_id = ? AND position < ? AND ? > 0 ORDER BY position DESC LIMIT 1),"
        "       (SELECT id FROM docs WHERE collection_id = ? AND position > ? AND ? > 0 ORDER BY position LIMIT 1)",
        (d["collection_id"], d["position"], d["position"], d["collection_id"], d["position"], d["position"])).fetchone()
    return {**doc_summary(d), "collection_id": d["collection_id"], "source_url": d["source_url"],
            "paras": paras, "readings": readings, "prev_id": sib[0], "next_id": sib[1]}


@router.get("/paras/{para_id}")
def para_details(para_id: int, conn=Depends(get_conn), refs=Depends(get_refs), user_id=Depends(get_user_id)):
    from app.routers.markup import note_dict
    ref = para_ref(conn, para_id)
    if not ref:
        raise HTTPException(404, "Not found")
    hl = conn.execute("SELECT color FROM para_highlights WHERE owner_id = ? AND para_id = ?",
                      (user_id, para_id)).fetchone()
    notes = [note_dict(conn, refs, n) for n in conn.execute(
        "SELECT * FROM notes WHERE para_id = ? ORDER BY created_at DESC", (para_id,))]
    links = [{"id": l["id"], "label": l["label"], "kind": "verse",
              "other": refs.describe(l["start_verse_id"], l["end_verse_id"])}
             for l in conn.execute("SELECT * FROM para_links WHERE para_id = ? ORDER BY created_at DESC", (para_id,))]
    return {"ref": ref, "highlight": hl[0] if hl else None, "notes": notes, "links": links}


# --- markup on paragraphs ---------------------------------------------------------------
class ParaHighlightIn(BaseModel):
    para_id: int
    color: str | None = None


@router.put("/para-highlights")
def set_para_highlight(body: ParaHighlightIn, conn=Depends(get_conn), user_id=Depends(get_user_id)):
    if not conn.execute("SELECT 1 FROM doc_paras WHERE id = ?", (body.para_id,)).fetchone():
        raise HTTPException(422, "Unknown paragraph")
    if body.color is not None and body.color not in ("promise", "christ", "doctrine", "question"):
        raise HTTPException(422, "Invalid color")
    with conn:
        conn.execute("DELETE FROM para_highlights WHERE owner_id = ? AND para_id = ?", (user_id, body.para_id))
        if body.color:
            conn.execute("INSERT INTO para_highlights (owner_id, para_id, color) VALUES (?, ?, ?)",
                         (user_id, body.para_id, body.color))
    return {"color": body.color}


class ParaLinkIn(BaseModel):
    para_id: int
    to: str | None = None
    start_verse_id: int | None = None
    end_verse_id: int | None = None
    label: str = Field("related", max_length=40)


@router.post("/para-links", status_code=201)
def create_para_link(body: ParaLinkIn, conn=Depends(get_conn), refs=Depends(get_refs),
                     user_id=Depends(get_user_id)):
    if not conn.execute("SELECT 1 FROM doc_paras WHERE id = ?", (body.para_id,)).fetchone():
        raise HTTPException(422, "Unknown paragraph")
    if body.to:
        r = refs.parse(body.to)
        if not r:
            raise HTTPException(422, "Couldn't read that reference")
        a, b = r.start_verse_id, r.end_verse_id
    else:
        a, b = body.start_verse_id, body.end_verse_id
        if a is None or b is None or b < a or conn.execute(
                "SELECT COUNT(*) FROM verses WHERE id IN (?, ?)", (a, b)).fetchone()[0] != (1 if a == b else 2):
            raise HTTPException(422, "Invalid verse range")
    label = body.label.strip().lower() or "related"
    with conn:
        cur = conn.execute(
            "INSERT INTO para_links (owner_id, para_id, start_verse_id, end_verse_id, label) VALUES (?, ?, ?, ?, ?)",
            (user_id, body.para_id, a, b, label))
    return {"id": cur.lastrowid, "label": label, "verse": refs.describe(a, b), "para": para_ref(conn, body.para_id)}


@router.delete("/para-links/{link_id}", status_code=204)
def delete_para_link(link_id: int, conn=Depends(get_conn), user_id=Depends(get_user_id)):
    row = conn.execute("SELECT owner_id FROM para_links WHERE id = ?", (link_id,)).fetchone()
    if not row or row[0] != user_id:
        raise HTTPException(404, "Link not found")
    with conn:
        conn.execute("DELETE FROM para_links WHERE id = ?", (link_id,))


# --- Come Follow Me: this week ---------------------------------------------------
@router.get("/cfm/week")
def cfm_week(on: str | None = None, conn=Depends(get_conn), refs=Depends(get_refs)):
    day = on or date.today().isoformat()
    row = conn.execute(f"{DOC_SELECT} WHERE c.kind = 'cfm' AND d.week_start <= ? AND d.week_end >= ?"
                       " ORDER BY d.week_start DESC LIMIT 1", (day, day)).fetchone()
    if not row:
        return None
    readings = [refs.describe(a, b) for a, b in conn.execute(
        "SELECT start_verse_id, end_verse_id FROM doc_readings WHERE doc_id = ? ORDER BY start_verse_id", (row["id"],))]
    return {**doc_summary(row), "readings": readings}


# --- importing ---------------------------------------------------------------------------
class ImportIn(BaseModel):
    kind: str = Field(pattern="^(conference|cfm|byu)$")
    year: int | None = Field(None, ge=1971, le=2100)
    month: int | None = Field(None, ge=1, le=12)
    urls: list[str] = Field(default_factory=list, max_length=200)


@router.post("/import", status_code=202)
def start_import(body: ImportIn):
    if body.kind in jobs.running_kinds():
        raise HTTPException(409, "That kind of import is already running")
    if body.kind == "conference":
        if not body.year or body.month not in (4, 10):
            raise HTTPException(422, "Pick a year and April or October")
        params = {"year": body.year, "month": body.month}
    elif body.kind == "cfm":
        if not body.year or body.year < 2022:
            raise HTTPException(422, "Pick a year from 2022 on")
        params = {"year": body.year}
    else:
        if not body.urls:
            raise HTTPException(422, "Paste at least one speech link")
        params = {"urls": body.urls}
    return jobs.start(body.kind, params)


@router.get("/import/jobs")
def import_jobs():
    return jobs.all_jobs()


@router.delete("/docs/{doc_id}", status_code=204)
def delete_doc(doc_id: int, conn=Depends(get_conn)):
    with conn:
        conn.execute("DELETE FROM docs WHERE id = ?", (doc_id,))
        conn.execute("DELETE FROM collections WHERE id NOT IN (SELECT collection_id FROM docs)")
