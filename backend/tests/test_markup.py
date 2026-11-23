"""Phase 2 tests: references, highlights, notes (incl. sanitizing), links."""

import pytest

from tests.test_library import client  # noqa: F401  (shared fixture)


def vid(client, ref):
    return client.get("/api/refs/resolve", params={"q": ref}).json()["start_verse_id"]


@pytest.mark.parametrize("text,label", [
    ("alma 32:21", "Alma 32:21"),
    ("Alma 32:21-28", "Alma 32:21–28"),
    ("1 Ne. 3:7", "1 Nephi 3:7"),
    ("1ne 3:7", "1 Nephi 3:7"),
    ("D&C 4:2", "D&C 4:2"),
    ("dc 121:7-8", "D&C 121:7–8"),
    ("Heb 11:1", "Hebrews 11:1"),
    ("moroni 10", "Moroni 10"),
    ("JS-H 1:17", "Joseph Smith—History 1:17"),
])
def test_resolve(client, text, label):
    r = client.get("/api/refs/resolve", params={"q": text})
    assert r.status_code == 200, text
    assert r.json()["label"] == label


@pytest.mark.parametrize("text", ["", "alma", "alma 99:1", "alma 32:999", "nonsense 3:4"])
def test_resolve_rejects(client, text):
    assert client.get("/api/refs/resolve", params={"q": text}).status_code == 404


def test_suggest_books(client):
    titles = [b["title"] for b in client.get("/api/refs/suggest", params={"q": "mo"}).json()["books"]]
    assert "Mosiah" in titles and "Moroni" in titles


def test_highlight_toggle(client):
    v = vid(client, "Alma 32:21")
    assert client.put("/api/highlights", json={"start_verse_id": v, "end_verse_id": v, "color": "promise"}).status_code == 200
    ann = client.get("/api/annotations/bofm/alma/32").json()
    assert ann["21"]["highlight"] == "promise"
    client.put("/api/highlights", json={"start_verse_id": v, "end_verse_id": v, "color": "christ"})
    assert client.get(f"/api/verses/{v}").json()["highlight"] == "christ"
    client.put("/api/highlights", json={"start_verse_id": v, "end_verse_id": v, "color": None})
    assert client.get(f"/api/verses/{v}").json()["highlight"] is None
    assert client.put("/api/highlights", json={"start_verse_id": v, "end_verse_id": v, "color": "red"}).status_code == 422


def test_note_with_refs_and_tags(client):
    v = vid(client, "Alma 32:21")
    heb = client.get("/api/refs/resolve", params={"q": "Hebrews 11:1"}).json()
    html = (f'<p>Faith is hope in things <strong>not seen</strong>. Compare '
            f'<span data-type="verseRef" data-start="{heb["start_verse_id"]}" data-end="{heb["end_verse_id"]}" '
            f'data-label="Hebrews 11:1">Hebrews 11:1</span> '
            f'<span data-type="tag" data-id="Faith" data-label="faith">#faith</span></p>')
    r = client.post("/api/notes", json={"body_html": html, "start_verse_id": v, "end_verse_id": v})
    assert r.status_code == 201
    note = r.json()
    assert note["tags"] == ["faith"]
    assert note["mentions"][0]["label"] == "Hebrews 11:1"
    assert note["anchor"]["label"] == "Alma 32:21"

    # shows on its own verse, and as "mentions" on Hebrews 11:1
    assert any(n["id"] == note["id"] for n in client.get(f"/api/verses/{v}").json()["notes"])
    on_heb = client.get(f"/api/verses/{heb['start_verse_id']}").json()["notes"]
    assert [n["relation"] for n in on_heb if n["id"] == note["id"]] == ["mentions"]

    # searchable and filterable
    assert client.get("/api/notes", params={"q": "faith hope"}).json()[0]["id"] == note["id"]
    assert client.get("/api/notes", params={"tag": "faith"}).json()[0]["id"] == note["id"]
    assert {"name": "faith", "count": 1} in client.get("/api/tags").json()

    # edit, then delete
    r = client.patch(f"/api/notes/{note['id']}", json={"body_html": "<p>Edited</p>"})
    assert r.json()["text"] == "Edited" and r.json()["tags"] == []
    assert client.delete(f"/api/notes/{note['id']}").status_code == 204
    assert client.get("/api/notes", params={"q": "Edited"}).json() == []


def test_note_html_is_sanitized(client):
    evil = '<p>hi<script>alert(1)</script><img src=x onerror="alert(2)"><span data-type="tag" data-id="ok" onclick="x()">#ok</span></p>'
    note = client.post("/api/notes", json={"body_html": evil}).json()
    assert "<script" not in note["html"] and "onerror" not in note["html"]
    assert "<img" not in note["html"] and "onclick" not in note["html"]
    assert note["tags"] == ["ok"]
    client.delete(f"/api/notes/{note['id']}")


def test_empty_note_rejected(client):
    assert client.post("/api/notes", json={"body_html": "<p>  </p>"}).status_code == 422


def test_links_both_directions(client):
    v = vid(client, "Alma 32:21")
    r = client.post("/api/links", json={"from_start_verse_id": v, "from_end_verse_id": v,
                                        "to": "Ether 12:6", "label": "expands on"})
    assert r.status_code == 201
    link = r.json()
    assert link["other"]["label"] == "Ether 12:6"
    ether = link["other"]["start_verse_id"]
    back = client.get(f"/api/verses/{ether}").json()["links"]
    assert back[0]["other"]["label"] == "Alma 32:21" and back[0]["label"] == "expands on"
    assert client.get("/api/annotations/bofm/alma/32").json()["21"]["links"] == 1
    assert client.delete(f"/api/links/{link['id']}").status_code == 204
    assert client.post("/api/links", json={"from_start_verse_id": v, "from_end_verse_id": v,
                                           "to": "not a ref"}).status_code == 422
