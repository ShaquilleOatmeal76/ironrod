"""Reading tracker, plans and goals.

Dates come from the browser (`today=YYYY-MM-DD`) because "today" depends on
where you are, and the server's clock is usually UTC.
"""

import math
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.deps import get_conn, get_refs, get_user_id

router = APIRouter(prefix="/api", tags=["plans"])

DAY = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$")


def _day(s: str | None) -> date:
    return date.fromisoformat(s) if s else date.today()


def reading_days(start: date, end: date, mask: str) -> int:
    if end < start:
        return 0
    n = 0
    d = start
    while d <= end:
        n += mask[d.weekday()] == "1"
        d += timedelta(days=1)
    return n


def _chapter_info(conn, ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    q = ",".join("?" * len(ids))
    rows = conn.execute(
        "SELECT c.id, c.number, b.slug AS book, b.title, v.slug AS volume FROM chapters c"
        f" JOIN books b ON b.id = c.book_id JOIN volumes v ON v.id = b.volume_id WHERE c.id IN ({q})", ids)
    out = {}
    for r in rows:
        title = "D&C" if r["title"] == "Doctrine and Covenants" else r["title"]
        out[r["id"]] = {"chapter_id": r["id"], "label": f"{title} {r['number']}", "volume": r["volume"],
                        "book": r["book"], "chapter": r["number"]}
    return out


def _chapter_id(conn, volume, book, chapter) -> int:
    row = conn.execute(
        "SELECT c.id FROM chapters c JOIN books b ON b.id = c.book_id JOIN volumes v ON v.id = b.volume_id"
        " WHERE v.slug = ? AND b.slug = ? AND c.number = ?", (volume, book, chapter)).fetchone()
    if not row:
        raise HTTPException(404, "Chapter not found")
    return row[0]


def _verse_chapters(conn, start_verse: int, end_verse: int) -> list[int]:
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT chapter_id FROM verses WHERE id BETWEEN ? AND ? ORDER BY chapter_id", (start_verse, end_verse))]


def _cfm_lessons(conn, year: int) -> list:
    return conn.execute(
        "SELECT d.* FROM docs d JOIN collections c ON c.id = d.collection_id"
        " WHERE c.slug = ? AND d.week_start IS NOT NULL ORDER BY d.week_start", (f"cfm/{year}",)).fetchall()


def _lesson_chapters(conn, doc_id: int) -> list[int]:
    ids: list[int] = []
    for a, b in conn.execute("SELECT start_verse_id, end_verse_id FROM doc_readings WHERE doc_id = ? ORDER BY start_verse_id", (doc_id,)):
        ids += [c for c in _verse_chapters(conn, a, b) if c not in ids]
    return ids


# --- reading log --------------------------------------------------------------------
class ReadIn(BaseModel):
    volume: str
    book: str
    chapter: int
    read: bool = True
    today: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


@router.post("/read-log")
def mark_read(body: ReadIn, conn=Depends(get_conn), user_id=Depends(get_user_id)):
    cid = _chapter_id(conn, body.volume, body.book, body.chapter)
    with conn:
        if body.read:
            conn.execute("INSERT OR IGNORE INTO reading_log (owner_id, chapter_id, read_on) VALUES (?, ?, ?)",
                         (user_id, cid, body.today))
            for p in conn.execute("SELECT * FROM plans WHERE owner_id = ? AND archived = 0 AND start_date <= ?",
                                  (user_id, body.today)).fetchall():
                in_plan = (p["kind"] == "range" and p["first_chapter_id"] <= cid <= p["last_chapter_id"]) or (
                    p["kind"] == "cfm" and any(cid in _lesson_chapters(conn, l["id"]) for l in _cfm_lessons(conn, p["cfm_year"])))
                if in_plan:
                    conn.execute("INSERT OR IGNORE INTO plan_done VALUES (?, ?, ?)", (p["id"], cid, body.today))
        else:
            conn.execute("DELETE FROM reading_log WHERE owner_id = ? AND chapter_id = ? AND read_on = ?",
                         (user_id, cid, body.today))
            conn.execute("DELETE FROM plan_done WHERE chapter_id = ? AND done_on = ? AND plan_id IN"
                         " (SELECT id FROM plans WHERE owner_id = ?)", (cid, body.today, user_id))
    return chapter_status(body.volume, body.book, body.chapter, body.today, conn, user_id)


@router.get("/read-log/{volume}/{book}/{chapter}")
def chapter_status(volume: str, book: str, chapter: int, today: str | None = DAY,
                   conn=Depends(get_conn), user_id=Depends(get_user_id)):
    cid = _chapter_id(conn, volume, book, chapter)
    t = _day(today).isoformat()
    last = conn.execute("SELECT MAX(read_on), COUNT(*) FROM reading_log WHERE owner_id = ? AND chapter_id = ?",
                        (user_id, cid)).fetchone()
    today_read = conn.execute("SELECT 1 FROM reading_log WHERE owner_id = ? AND chapter_id = ? AND read_on = ?",
                              (user_id, cid, t)).fetchone() is not None
    return {"chapter_id": cid, "read_today": today_read, "last_read": last[0], "times_read": last[1]}


# --- plans ------------------------------------------------------------------------------
def plan_status(conn, p, today: date) -> dict:
    done = {r[0]: r[1] for r in conn.execute("SELECT chapter_id, done_on FROM plan_done WHERE plan_id = ?", (p["id"],))}
    base = {"id": p["id"], "title": p["title"], "kind": p["kind"], "start_date": p["start_date"],
            "end_date": p["end_date"], "days": p["days"], "cfm_year": p["cfm_year"]}
    reading_day = p["days"][today.weekday()] == "1"

    if p["kind"] == "range":
        chapters = list(range(p["first_chapter_id"], p["last_chapter_id"] + 1))
        start, end = date.fromisoformat(p["start_date"]), date.fromisoformat(p["end_date"])
        total_days = max(reading_days(start, end, p["days"]), 1)
        before = {c for c, d in done.items() if d < today.isoformat()}
        days_left = reading_days(max(today, start), end, p["days"])
        remaining = len(chapters) - len(before)
        quota = math.ceil(remaining / days_left) if days_left else remaining
        todo = [c for c in chapters if c not in before]
        today_ids = todo[:quota] if (reading_day or days_left == 0) and today >= start else []
        # what should be done by the end of yesterday (today's reading isn't late yet)
        elapsed = reading_days(start, min(today - timedelta(days=1), end), p["days"])
        expected = math.ceil(len(chapters) * elapsed / total_days)
        diff = len(done) - expected
        info = _chapter_info(conn, today_ids)
        per_day = remaining / days_left if days_left else remaining
        if len(done) >= len(chapters):
            status = "finished"
        elif today < start:
            status = f"starts {start:%b} {start.day}"
        elif diff >= 0:
            status = "on track" if diff <= quota else f"{diff - quota} ahead"
        else:
            status = f"{-diff} behind"
        return {**base, "total": len(chapters), "done": len(done), "status": status,
                "behind": diff < 0 and len(done) < len(chapters),
                "pace": f"≈ {per_day:.1f} ch/day to finish {end:%b} {end.day}" if days_left else "",
                "today": [{**info[c], "done": c in done} for c in today_ids],
                "rest_day": not reading_day and today >= start}

    # Come Follow Me
    lessons = _cfm_lessons(conn, p["cfm_year"])
    if not lessons:
        return {**base, "total": 0, "done": 0, "status": f"import Come Follow Me {p['cfm_year']}",
                "behind": False, "pace": "", "today": [], "needs_import": True, "rest_day": False}
    t = today.isoformat()
    week = next((l for l in lessons if l["week_start"] <= t <= l["week_end"]), None)
    idx = sum(1 for l in lessons if l["week_start"] <= t)
    ids = _lesson_chapters(conn, week["id"]) if week else []
    info = _chapter_info(conn, ids)
    items = [{**info[c], "done": c in done} for c in ids]
    n_done = sum(i["done"] for i in items)
    return {**base, "total": len(lessons), "done": idx, "status": f"week {idx} of {len(lessons)}",
            "behind": False, "pace": f"this week: {week['reading'] or week['title']}" if week else "between lessons",
            "today": items, "week": {"doc_id": week["id"], "title": week["title"], "reading": week["reading"],
                                    "week_done": n_done, "week_total": len(items)} if week else None,
            "rest_day": False}


@router.get("/plans")
def list_plans(today: str | None = DAY, conn=Depends(get_conn), user_id=Depends(get_user_id)):
    t = _day(today)
    return [plan_status(conn, p, t) for p in conn.execute(
        "SELECT * FROM plans WHERE owner_id = ? AND archived = 0 ORDER BY id", (user_id,)).fetchall()]


VOLUME_PRESETS = {"ot": "Old Testament", "nt": "New Testament", "bofm": "Book of Mormon",
                  "dc-testament": "Doctrine and Covenants", "pgp": "Pearl of Great Price"}


class PlanIn(BaseModel):
    kind: str = Field(pattern="^(range|cfm)$")
    title: str | None = Field(None, max_length=80)
    volume: str | None = None          # preset: a whole volume
    from_ref: str | None = None        # or a custom range, e.g. "1 Nephi 1" .. "Moroni 10"
    to_ref: str | None = None
    start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    days: str = Field("1111111", pattern="^[01]{7}$")
    cfm_year: int | None = None


def _range_for(conn, refs, body: PlanIn):
    if body.volume:
        row = conn.execute(
            "SELECT MIN(c.id), MAX(c.id) FROM chapters c JOIN books b ON b.id = c.book_id"
            " JOIN volumes v ON v.id = b.volume_id WHERE v.slug = ?", (body.volume,)).fetchone()
        if row[0] is None:
            raise HTTPException(422, "Unknown volume")
        return row[0], row[1], VOLUME_PRESETS.get(body.volume, body.volume)
    a, b = refs.parse(body.from_ref or ""), refs.parse(body.to_ref or body.from_ref or "")
    if not a or not b:
        raise HTTPException(422, "Couldn't read the start or end chapter")
    first = conn.execute("SELECT chapter_id FROM verses WHERE id = ?", (a.start_verse_id,)).fetchone()[0]
    last = conn.execute("SELECT chapter_id FROM verses WHERE id = ?", (b.end_verse_id,)).fetchone()[0]
    if last < first:
        raise HTTPException(422, "The end comes before the start")
    return first, last, f"{refs.label(a.start_verse_id, a.start_verse_id).rsplit(':', 1)[0]} → {refs.label(b.end_verse_id, b.end_verse_id).rsplit(':', 1)[0]}"


@router.post("/plans/preview")
def preview_plan(body: PlanIn, conn=Depends(get_conn), refs=Depends(get_refs)):
    if body.kind == "cfm":
        n = len(_cfm_lessons(conn, body.cfm_year or 0))
        return {"chapters": 0, "days": 0, "per_day": 0, "lessons": n}
    if not body.end_date:
        raise HTTPException(422, "Pick a finish date")
    first, last, _ = _range_for(conn, refs, body)
    days = reading_days(date.fromisoformat(body.start_date), date.fromisoformat(body.end_date), body.days)
    n = last - first + 1
    return {"chapters": n, "days": days, "per_day": round(n / days, 2) if days else n}


@router.post("/plans", status_code=201)
def create_plan(body: PlanIn, conn=Depends(get_conn), refs=Depends(get_refs), user_id=Depends(get_user_id)):
    if body.kind == "cfm":
        year = body.cfm_year or date.fromisoformat(body.start_date).year
        values = (user_id, body.title or f"Come Follow Me {year}", "cfm", None, None, body.start_date, None, "1111111", year)
    else:
        if not body.end_date or body.end_date < body.start_date:
            raise HTTPException(422, "Pick a finish date after the start")
        if "1" not in body.days:
            raise HTTPException(422, "Pick at least one reading day")
        first, last, name = _range_for(conn, refs, body)
        end = date.fromisoformat(body.end_date)
        values = (user_id, body.title or f"{name} by {end:%b} {end.day}", "range", first, last,
                  body.start_date, body.end_date, body.days, None)
    with conn:
        cur = conn.execute(
            "INSERT INTO plans (owner_id, title, kind, first_chapter_id, last_chapter_id, start_date, end_date, days, cfm_year)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
        # chapters already read since the plan's start count toward it
        p = conn.execute("SELECT * FROM plans WHERE id = ?", (cur.lastrowid,)).fetchone()
        if p["kind"] == "range":
            conn.execute(
                "INSERT OR IGNORE INTO plan_done SELECT ?, chapter_id, MIN(read_on) FROM reading_log"
                " WHERE owner_id = ? AND read_on >= ? AND chapter_id BETWEEN ? AND ? GROUP BY chapter_id",
                (p["id"], user_id, p["start_date"], p["first_chapter_id"], p["last_chapter_id"]))
    return plan_status(conn, p, date.fromisoformat(body.start_date) if body.start_date > date.today().isoformat() else date.today())


@router.delete("/plans/{plan_id}", status_code=204)
def archive_plan(plan_id: int, conn=Depends(get_conn), user_id=Depends(get_user_id)):
    with conn:
        n = conn.execute("UPDATE plans SET archived = 1 WHERE id = ? AND owner_id = ?", (plan_id, user_id)).rowcount
    if not n:
        raise HTTPException(404, "Plan not found")


# --- goals & stats ---------------------------------------------------------------------
GOAL_LABELS = {"study_days": "Study {n} days a week", "notes": "Write {n} notes a week",
               "chapters": "Read {n} chapters a week"}


def _active_days(conn, user_id) -> set[str]:
    days = {r[0] for r in conn.execute("SELECT DISTINCT read_on FROM reading_log WHERE owner_id = ?", (user_id,))}
    days |= {r[0] for r in conn.execute("SELECT DISTINCT date(created_at, 'localtime') FROM notes WHERE owner_id = ?", (user_id,))}
    return days


@router.get("/stats")
def stats(today: str | None = DAY, conn=Depends(get_conn), user_id=Depends(get_user_id)):
    t = _day(today)
    active = _active_days(conn, user_id)
    d = t if t.isoformat() in active else t - timedelta(days=1)
    streak = 0
    while d.isoformat() in active:
        streak += 1
        d -= timedelta(days=1)
    monday = t - timedelta(days=t.weekday())
    week = [monday + timedelta(days=i) for i in range(7)]
    wk = (week[0].isoformat(), week[-1].isoformat())
    ch_by_day = dict(conn.execute(
        "SELECT read_on, COUNT(*) FROM reading_log WHERE owner_id = ? AND read_on BETWEEN ? AND ? GROUP BY read_on",
        (user_id, *wk)).fetchall())
    notes_by_day = dict(conn.execute(
        "SELECT date(created_at, 'localtime'), COUNT(*) FROM notes WHERE owner_id = ?"
        " AND date(created_at, 'localtime') BETWEEN ? AND ? GROUP BY 1", (user_id, *wk)).fetchall())
    days = [{"date": x.isoformat(), "label": "mtwtfss"[i], "chapters": ch_by_day.get(x.isoformat(), 0),
             "notes": notes_by_day.get(x.isoformat(), 0), "active": x.isoformat() in active,
             "future": x > t} for i, x in enumerate(week)]
    totals = {"study_days": sum(d["active"] for d in days), "notes": sum(d["notes"] for d in days),
              "chapters": sum(d["chapters"] for d in days)}
    goals = []
    for g in conn.execute("SELECT kind, target FROM goals WHERE owner_id = ? ORDER BY id", (user_id,)):
        goals.append({"kind": g["kind"], "target": g["target"], "value": totals[g["kind"]],
                      "title": GOAL_LABELS[g["kind"]].format(n=g["target"])})
    # 26-week heatmap of chapters read per day
    since = (t - timedelta(days=7 * 26 + t.weekday())).isoformat()
    heat = dict(conn.execute(
        "SELECT read_on, COUNT(*) FROM reading_log WHERE owner_id = ? AND read_on >= ? GROUP BY read_on",
        (user_id, since)).fetchall())
    return {"streak": streak, "today_chapters": ch_by_day.get(t.isoformat(), 0), "week": days,
            "totals": totals, "goals": goals, "heatmap": heat, "heat_since": since,
            "chapters_all_time": conn.execute("SELECT COUNT(DISTINCT chapter_id) FROM reading_log WHERE owner_id = ?",
                                              (user_id,)).fetchone()[0]}


class GoalIn(BaseModel):
    kind: str = Field(pattern="^(study_days|notes|chapters)$")
    target: int = Field(ge=0, le=500)


@router.put("/goals")
def set_goal(body: GoalIn, conn=Depends(get_conn), user_id=Depends(get_user_id)):
    if body.kind == "study_days" and body.target > 7:
        raise HTTPException(422, "A week has 7 days")
    with conn:
        if body.target == 0:
            conn.execute("DELETE FROM goals WHERE owner_id = ? AND kind = ?", (user_id, body.kind))
        else:
            conn.execute("INSERT INTO goals (owner_id, kind, target) VALUES (?, ?, ?)"
                         " ON CONFLICT(owner_id, kind) DO UPDATE SET target = excluded.target",
                         (user_id, body.kind, body.target))
    return {"kind": body.kind, "target": body.target}
