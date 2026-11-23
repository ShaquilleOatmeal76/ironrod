"""Phase 3 tests: query building and the unified search endpoint."""

import pytest

from app.search import fts_query, marks_to_parts, MARK_START, MARK_END
from tests.test_library import client  # noqa: F401  (shared fixture)


@pytest.mark.parametrize("text,expected", [
    ("faith", '"faith"*'),
    ("faith hope", '"faith" "hope"*'),
    ('"perfect love"', '"perfect love"'),
    ('faith "not seen"', '"faith" "not seen"'),
    ("NOT OR AND", '"NOT" "OR" "AND"*'),
    ('weird"quote', '"weird" "quote"*'),
    ("", None),
    ("!!!", None),
])
def test_fts_query(text, expected):
    assert fts_query(text) == expected


def test_marks_to_parts():
    s = f"a {MARK_START}faith{MARK_END} b"
    assert marks_to_parts(s) == [{"text": "a ", "hit": False}, {"text": "faith", "hit": True},
                                 {"text": " b", "hit": False}]


def test_search_reference(client):
    r = client.get("/api/search", params={"q": "alma 32:21"}).json()
    assert r["ref"]["label"] == "Alma 32:21"


def test_search_books(client):
    titles = [b["title"] for b in client.get("/api/search", params={"q": "mor"}).json()["books"]]
    assert "Moroni" in titles and "Mormon" in titles


def test_search_verses_ranked_and_scoped(client):
    r = client.get("/api/search", params={"q": "faith is not to have a perfect knowledge"}).json()
    assert r["verses"]["items"][0]["label"] == "Alma 32:21"
    assert any(p["hit"] for p in r["verses"]["items"][0]["parts"])

    nt = client.get("/api/search", params={"q": "substance of things hoped", "scope": "nt"}).json()
    assert nt["verses"]["items"][0]["label"] == "Hebrews 11:1"
    assert all(i["volume"] == "nt" for i in nt["verses"]["items"])


def test_search_stemming(client):
    # porter stemmer: "believing" also matches "believe"/"believed"
    r = client.get("/api/search", params={"q": "believing", "kinds": "verses", "limit": 50}).json()
    words = " ".join(p["text"] for i in r["verses"]["items"] for p in i["parts"] if p["hit"]).lower()
    assert r["verses"]["total"] > 100 and ("believe" in words or "believed" in words)


def test_search_paging(client):
    a = client.get("/api/search", params={"q": "faith", "kinds": "verses", "limit": 5}).json()["verses"]
    b = client.get("/api/search", params={"q": "faith", "kinds": "verses", "limit": 5, "offset": 5}).json()["verses"]
    assert a["total"] == b["total"] > 10
    assert {i["start_verse_id"] for i in a["items"]}.isdisjoint({i["start_verse_id"] for i in b["items"]})


def test_search_notes_and_tags(client):
    note = client.post("/api/notes", json={
        "body_html": '<p>The seed grows when nourished <span data-type="tag" data-id="growth">#growth</span></p>'}).json()
    r = client.get("/api/search", params={"q": "nourish"}).json()
    assert r["notes"]["items"][0]["id"] == note["id"]
    assert any(p["hit"] for p in r["notes"]["items"][0]["parts"])
    assert client.get("/api/search", params={"q": "#gro"}).json()["tags"][0]["name"] == "growth"
    client.delete(f"/api/notes/{note['id']}")


@pytest.mark.parametrize("q", ['"', "*", "NEAR(", "a OR", "-", "col:faith", "))"])
def test_search_never_errors(client, q):
    assert client.get("/api/search", params={"q": q}).status_code == 200


def test_bad_scope(client):
    assert client.get("/api/search", params={"q": "x", "scope": "nope"}).status_code == 422
