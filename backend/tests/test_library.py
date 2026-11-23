"""API tests. Run from backend/:  IRONROD_SOURCE=/path/to/lds-scriptures-sqlite.db pytest

Needs the source dataset (downloaded once by the importer, or pass a local
copy with IRONROD_SOURCE) and uses a throwaway database.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    os.environ["IRONROD_DB"] = str(tmp_path_factory.mktemp("db") / "test.db")
    os.environ["IRONROD_AUTO_IMPORT"] = "0"
    from app import db
    db.DB_PATH = Path(os.environ["IRONROD_DB"])
    from scripts import import_scriptures
    src = os.environ.get("IRONROD_SOURCE")
    import_scriptures.run(Path(src) if src else None)

    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_volumes(client):
    vols = client.get("/api/volumes").json()
    assert [v["slug"] for v in vols] == ["ot", "nt", "bofm", "dc-testament", "pgp"]
    bom = next(v for v in vols if v["slug"] == "bofm")
    assert len(bom["books"]) == 15
    assert sum(b["chapters"] for b in bom["books"]) == 239


def test_chapter(client):
    ch = client.get("/api/read/bofm/alma/32").json()
    assert ch["book_title"] == "Alma" and len(ch["verses"]) == 43
    assert ch["verses"][20]["text"].startswith("And now as I said concerning faith—faith")
    assert ch["prev"]["chapter"] == 31 and ch["next"]["chapter"] == 33


def test_navigation_crosses_books(client):
    ch = client.get("/api/read/bofm/1-ne/22").json()
    assert ch["next"]["book"] == "2-ne" and ch["next"]["chapter"] == 1
    assert client.get("/api/read/ot/gen/1").json()["prev"] is None


def test_missing_chapter(client):
    assert client.get("/api/read/bofm/alma/999").status_code == 404
