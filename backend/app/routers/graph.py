"""The study graph: verses, talk paragraphs and notes, joined by your links.

Node ids:  v:<start>-<end>  (a verse range)   p:<id> (talk paragraph)   n:<id> (note)
Edges come from links, verse<->paragraph links, where a note sits, and the
@references inside notes.
"""

from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Query

from app.deps import get_conn, get_refs
from app.routers.docs import para_ref

router = APIRouter(prefix="/api", tags=["graph"])


def _edges(conn):
    e = []
    for r in conn.execute("SELECT a_start_verse_id, a_end_verse_id, b_start_verse_id, b_end_verse_id, label FROM links"):
        e.append((f"v:{r[0]}-{r[1]}", f"v:{r[2]}-{r[3]}", r[4]))
    for r in conn.execute("SELECT para_id, start_verse_id, end_verse_id, label FROM para_links"):
        e.append((f"p:{r[0]}", f"v:{r[1]}-{r[2]}", r[3]))
    for r in conn.execute("SELECT id, start_verse_id, end_verse_id, para_id FROM notes"):
        if r[1]:
            e.append((f"n:{r[0]}", f"v:{r[1]}-{r[2]}", "note on"))
        if r[3]:
            e.append((f"n:{r[0]}", f"p:{r[3]}", "note on"))
    for r in conn.execute("SELECT note_id, start_verse_id, end_verse_id FROM note_refs"):
        e.append((f"n:{r[0]}", f"v:{r[1]}-{r[2]}", "mentions"))
    return e


def _contains(node: str, verse_id: int) -> bool:
    if not node.startswith("v:"):
        return False
    a, b = map(int, node[2:].split("-"))
    return a <= verse_id <= b


@router.get("/graph")
def graph(verse_id: int | None = None, para_id: int | None = None, depth: int = Query(2, ge=1, le=4),
          limit: int = Query(300, le=1000), conn=Depends(get_conn), refs=Depends(get_refs)):
    edges = _edges(conn)
    adj = defaultdict(set)
    for a, b, _ in edges:
        adj[a].add(b)
        adj[b].add(a)

    if verse_id is not None or para_id is not None:
        seeds = {n for n in adj if (verse_id is not None and _contains(n, verse_id)) or n == f"p:{para_id}"}
        center = f"v:{verse_id}-{verse_id}" if verse_id is not None else f"p:{para_id}"
        if not seeds:
            seeds = {center}
        keep, q = set(seeds), deque((s, 0) for s in seeds)
        while q and len(keep) < limit:
            n, d = q.popleft()
            if d >= depth:
                continue
            for m in adj[n]:
                if m not in keep:
                    keep.add(m)
                    q.append((m, d + 1))
        if verse_id is not None and center not in keep:
            keep.add(center)
            for s in seeds:
                if s != center:
                    edges.append((center, s, "contains"))
    else:
        keep = set(list(adj)[:limit])

    nodes = []
    for n in keep:
        kind, val = n.split(":", 1)
        if kind == "v":
            a, b = map(int, val.split("-"))
            d = refs.describe(a, b)
            nodes.append({"id": n, "kind": "verse", "label": d["label"], "text": d["text"],
                          "href": f"/read/{d['volume']}/{d['book']}/{d['chapter']}#v{d['verse']}"})
        elif kind == "p":
            r = para_ref(conn, int(val))
            if r:
                nodes.append({"id": n, "kind": "talk", "label": f"{r['doc_title']} ¶{r['position']}",
                              "text": r["text"], "href": f"/doc/{r['doc_id']}#p{r['position']}"})
        else:
            row = conn.execute("SELECT body_text, start_verse_id, para_id FROM notes WHERE id = ?", (int(val),)).fetchone()
            if row:
                t = row[0]
                nodes.append({"id": n, "kind": "note", "label": (t[:40] + "…") if len(t) > 40 else t,
                              "text": t[:280], "href": "/notes"})
    ids = {n["id"] for n in nodes}
    seen, out_edges = set(), []
    for a, b, label in edges:
        k = tuple(sorted((a, b)))
        if a in ids and b in ids and k not in seen:
            seen.add(k)
            out_edges.append({"source": a, "target": b, "label": label})
    return {"nodes": nodes, "edges": out_edges}
