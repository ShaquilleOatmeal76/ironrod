"""Read-only library endpoints: the table of contents and chapter text."""

from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_conn

router = APIRouter(prefix="/api", tags=["library"])


@router.get("/volumes")
def list_volumes(conn=Depends(get_conn)):
    """Every volume with its books and chapter counts -- the sidebar's TOC."""
    volumes = [dict(v) for v in conn.execute(
        "SELECT id, slug, title, long_title, subtitle, short_title FROM volumes ORDER BY position")]
    books = conn.execute(
        "SELECT b.id, b.volume_id, b.slug, b.title, b.short_title, COUNT(c.id) AS chapters"
        " FROM books b JOIN chapters c ON c.book_id = b.id"
        " GROUP BY b.id ORDER BY b.position")
    by_volume: dict[int, list] = {v["id"]: [] for v in volumes}
    for b in books:
        by_volume[b["volume_id"]].append(
            {"slug": b["slug"], "title": b["title"], "short_title": b["short_title"],
             "chapters": b["chapters"]})
    for v in volumes:
        v["books"] = by_volume[v.pop("id")]
    return volumes


def _chapter_ref(row):
    if row is None:
        return None
    return {"volume": row["volume"], "book": row["book"], "book_title": row["title"],
            "chapter": row["number"]}


@router.get("/read/{volume}/{book}/{chapter}")
def read_chapter(volume: str, book: str, chapter: int, conn=Depends(get_conn)):
    """One chapter's verses, plus the previous/next chapter for navigation."""
    row = conn.execute(
        "SELECT c.id AS chapter_id, c.number, b.title, b.long_title, b.subtitle,"
        "       b.slug AS book, v.slug AS volume, v.title AS volume_title"
        " FROM chapters c JOIN books b ON b.id = c.book_id JOIN volumes v ON v.id = b.volume_id"
        " WHERE v.slug = ? AND b.slug = ? AND c.number = ?",
        (volume, book, chapter)).fetchone()
    if row is None:
        raise HTTPException(404, "Chapter not found")

    verses = [dict(v) for v in conn.execute(
        "SELECT id, number, text FROM verses WHERE chapter_id = ? ORDER BY number",
        (row["chapter_id"],))]

    nav_sql = ("SELECT c.number, b.title, b.slug AS book, v.slug AS volume"
               " FROM chapters c JOIN books b ON b.id = c.book_id JOIN volumes v ON v.id = b.volume_id"
               " WHERE c.id = ?")
    prev_row = conn.execute(nav_sql, (row["chapter_id"] - 1,)).fetchone()
    next_row = conn.execute(nav_sql, (row["chapter_id"] + 1,)).fetchone()

    return {
        "volume": row["volume"], "volume_title": row["volume_title"],
        "book": row["book"], "book_title": row["title"],
        "book_long_title": row["long_title"], "book_subtitle": row["subtitle"],
        "chapter": row["number"], "verses": verses,
        "prev": _chapter_ref(prev_row), "next": _chapter_ref(next_row),
    }
