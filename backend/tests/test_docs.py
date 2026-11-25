"""Phase 4 tests: parsing, importing (with the network faked), doc reading,
paragraph markup, verse<->paragraph links, search, graph."""

from datetime import date

import pytest

from app.importers import fetch, parse, sources
from tests.test_library import client  # noqa: F401

TALK_HTML = """
<header><p class="kicker">Faith is a principle of action.</p>
<h1 id="title1">The Seed of Faith</h1>
<p class="author-name">By Elder Example Speaker</p>
<p class="author-role">Of the Quorum of the Twelve Apostles</p></header>
<div class="body-block">
<p id="p1">Alma taught that faith is not a perfect knowledge.<sup class="marker" data-value="1">1</sup></p>
<h2 id="title2">Planting the Word</h2>
<p id="p_aB3dE">We compare the word unto a seed , and it begins to swell .</p>
<figure><p class="figcaption">A photo caption</p></figure>
<blockquote><p>A quoted line of scripture.</p></blockquote>
<ul><li><p>First point</p></li><li>Second point</li></ul>
</div>
<footer class="notes"><p id="note1">1. Alma 32:21.</p></footer>
"""

CONF_TOC = """
<a href="/study/general-conference/2024/10/saturday-morning-session?lang=eng">Saturday Morning</a>
<a href="/study/general-conference/2024/10/11example?lang=eng">Talk one</a>
<a href="/study/general-conference/2024/10/12other?lang=eng#p1">Talk two</a>
<a href="/study/general-conference/2024/10/11example?lang=eng">dupe</a>
<a href="/study/general-conference/2024/10/media">media</a>
<a href="/study/scriptures/bofm/alma/32">not a talk</a>
"""

CFM_TOC = """
<a class="list-tile" href="/study/manual/come-follow-me-for-home-and-church-old-testament-2026/title-page?lang=eng"><p class="title">Title Page</p></a>
<a class="list-tile" href="/study/manual/come-follow-me-for-home-and-church-old-testament-2026/01?lang=eng"><p class="title">December 29–January 4: Introduction</p></a>
<a class="list-tile" href="/study/manual/come-follow-me-for-home-and-church-old-testament-2026/02?lang=eng"><p class="title">January 5–11: Moses 1; Abraham 3</p></a>
<a class="list-tile" href="/study/manual/come-follow-me-for-home-and-church-old-testament-2026/03?lang=eng"><p class="title">January 12–18: Genesis 1–2; Moses 2–3</p></a>
"""

LESSON_HTML = """<header><h1>January 12–18: Genesis 1–2; Moses 2–3</h1>
<p class="title-number">“In the Beginning God Created the Heaven and the Earth”</p></header>
<p id="p1">The Creation testifies of God.</p><h2>Ideas for Learning at Home</h2><p id="p2">Read Genesis 1.</p>"""

BYU_HTML = """<html><body>
<h1 class="single-speech__title">Learning by Faith</h1>
<p class="single-speech__speaker">Example Person</p>
<p class="single-speech__speaker-position">Professor of Things</p>
<p class="single-speech__date">September 22, 2026</p>
<div class="single-speech__content"><p>First paragraph of the speech.</p><p>Second paragraph.</p>
<p>© by Intellectual Reserve, Inc. All rights reserved.</p></div></body></html>"""


def test_church_page_parsing():
    page = parse.church_page(TALK_HTML)
    assert page["title"] == "The Seed of Faith"
    assert page["author"] == "Elder Example Speaker"
    assert page["author_role"].startswith("Of the Quorum")
    assert page["blocks"] == [
        ("p", "Alma taught that faith is not a perfect knowledge."),
        ("h2", "Planting the Word"),
        ("p", "We compare the word unto a seed, and it begins to swell."),
        ("quote", "A quoted line of scripture."),
        ("li", "First point"),
        ("li", "Second point"),
    ]


def test_conference_toc():
    assert parse.conference_talk_uris(CONF_TOC, 2024, "10") == [
        "/general-conference/2024/10/11example", "/general-conference/2024/10/12other"]


@pytest.mark.parametrize("title,first,expected", [
    ("January 5–11: Moses 1; Abraham 3", False, (date(2026, 1, 5), date(2026, 1, 11), "Moses 1; Abraham 3")),
    ("December 29–January 4: Introduction", True, (date(2025, 12, 29), date(2026, 1, 4), "Introduction")),
    ("March 30–April 5: Easter", False, (date(2026, 3, 30), date(2026, 4, 5), "Easter")),
    ("Title Page", False, None),
])
def test_parse_week(title, first, expected):
    assert parse.parse_week(title, 2026, first_lesson=first) == expected


def test_byu_parsing():
    s = parse.byu_speech(BYU_HTML)
    assert s["title"] == "Learning by Faith" and s["author"] == "Example Person"
    assert s["published"] == "2026-09-22"
    assert [t for _, t in s["blocks"]] == ["First paragraph of the speech.", "Second paragraph."]


@pytest.fixture(scope="module")
def imported(client, monkeypatch_module):
    """Run the real importers against canned pages."""
    pages = {
        "/general-conference/2024/10": CONF_TOC,
        "/general-conference/2024/10/11example": TALK_HTML,
        "/general-conference/2024/10/12other": TALK_HTML.replace("The Seed of Faith", "Second Talk"),
        sources.cfm_manual_uri(2026): CFM_TOC,
        sources.cfm_manual_uri(2026) + "/01": "<h1>December 29–January 4: Introduction</h1><p>Welcome.</p>",
        sources.cfm_manual_uri(2026) + "/02": "<h1>January 5–11: Moses 1; Abraham 3</h1><p>Moses saw God.</p>",
        sources.cfm_manual_uri(2026) + "/03": LESSON_HTML,
    }

    def fake_json(url):
        uri = url.split("uri=", 1)[1]
        return {"content": {"body": pages[uri]}} if uri in pages else None

    monkeypatch_module.setattr(fetch, "get_json", fake_json)
    monkeypatch_module.setattr(fetch, "get", lambda url, **kw: BYU_HTML)
    conn = client.app.state.conn
    refs = client.app.state.refs
    assert sources.conference(conn, 2024, 10) == 2
    assert sources.conference(conn, 2024, 10) == 0          # re-running is safe
    assert sources.come_follow_me(conn, refs, 2026) == 3
    assert sources.byu_speeches(conn, ["https://speeches.byu.edu/talks/example-person/learning-by-faith"]) == 1
    return client


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def test_library_and_doc(imported):
    lib = {g["kind"]: g for g in imported.get("/api/library").json()}
    conf = lib["conference"]["collections"][0]
    assert conf["title"] == "October 2024 General Conference" and conf["docs"] == 2
    docs = imported.get(f"/api/collections/{conf['id']}").json()["docs"]
    d = imported.get(f"/api/docs/{docs[0]['id']}").json()
    assert d["title"] == "The Seed of Faith" and d["author"] == "Elder Example Speaker"
    assert [p["kind"] for p in d["paras"]][:2] == ["p", "h2"]
    assert d["next_id"] == docs[1]["id"] and d["prev_id"] is None


def test_cfm_week_and_readings(imported):
    wk = imported.get("/api/cfm/week", params={"on": "2026-01-14"}).json()
    assert wk["title"] == "Genesis 1–2; Moses 2–3"
    assert [r["label"] for r in wk["readings"]] == ["Genesis 1–2", "Moses 2–3"]
    assert imported.get("/api/cfm/week", params={"on": "2030-01-01"}).json() is None


def test_para_markup_links_and_search(imported):
    lib = {g["kind"]: g for g in imported.get("/api/library").json()}
    cid = lib["conference"]["collections"][0]["id"]
    doc = imported.get(f"/api/docs/{imported.get(f'/api/collections/{cid}').json()['docs'][0]['id']}").json()
    para = doc["paras"][0]["id"]

    assert imported.put("/api/para-highlights", json={"para_id": para, "color": "doctrine"}).status_code == 200
    note = imported.post("/api/notes", json={"body_html": "<p>Good talk paragraph</p>", "para_id": para}).json()
    assert note["para"]["doc_title"] == "The Seed of Faith"
    link = imported.post("/api/para-links", json={"para_id": para, "to": "Alma 32:21", "label": "quotes"}).json()
    assert link["verse"]["label"] == "Alma 32:21"

    d = imported.get(f"/api/paras/{para}").json()
    assert d["highlight"] == "doctrine" and len(d["notes"]) == 1 and d["links"][0]["other"]["label"] == "Alma 32:21"
    doc2 = imported.get(f"/api/docs/{doc['id']}").json()
    assert doc2["paras"][0]["links"] == 1 and doc2["paras"][0]["notes"] == 1

    # visible from the verse side too
    v = link["verse"]["start_verse_id"]
    talk_links = [l for l in imported.get(f"/api/verses/{v}").json()["links"] if l["kind"] == "para"]
    assert talk_links[0]["other"]["doc_title"] == "The Seed of Faith"
    assert imported.get("/api/annotations/bofm/alma/32").json()["21"]["links"] >= 1

    # search finds talk paragraphs
    hits = imported.get("/api/search", params={"q": "perfect knowledge"}).json()["talks"]["items"]
    assert hits and hits[0]["title"] in ("The Seed of Faith", "Second Talk")

    # graph around the verse includes the paragraph and the note
    g = imported.get("/api/graph", params={"verse_id": v}).json()
    kinds = {n["kind"] for n in g["nodes"]}
    assert {"verse", "talk", "note"} <= kinds and g["edges"]

    assert imported.delete(f"/api/para-links/{link['id']}").status_code == 204
    imported.delete(f"/api/notes/{note['id']}")


def test_import_validation(client):
    assert client.post("/api/import", json={"kind": "conference", "year": 2024, "month": 5}).status_code == 422
    assert client.post("/api/import", json={"kind": "byu"}).status_code == 422
    assert client.post("/api/import", json={"kind": "nope"}).status_code == 422
