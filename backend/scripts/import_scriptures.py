"""Load the standard works into Iron Rod's database.

Source: LDS Documentation Project (https://scriptures.nephi.org/), a
public-domain dataset of the KJV Bible, Book of Mormon, D&C and Pearl of
Great Price. We download its SQLite file once and copy it into our own schema.

Usage:
    python -m scripts.import_scriptures                 # download + import
    python -m scripts.import_scriptures --source FILE   # use a local copy
"""

import argparse
import sqlite3
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import db  # noqa: E402

SOURCE_URL = (
    "https://raw.githubusercontent.com/beandog/lds-scriptures/master/"
    "sqlite/lds-scriptures-sqlite.db"
)


def clean(text: str) -> str:
    # The dataset writes em-dashes as "--"; show real ones in the reader.
    return text.replace("--", "—").strip()


def download(dest: Path) -> Path:
    print(f"Downloading scripture data from {SOURCE_URL} ...")
    urllib.request.urlretrieve(SOURCE_URL, dest)
    return dest


def import_from(source: Path, conn: sqlite3.Connection) -> int:
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row

    with conn:
        for v in src.execute("SELECT * FROM volumes ORDER BY id"):
            conn.execute(
                "INSERT INTO volumes (id, slug, title, long_title, subtitle, short_title, position)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (v["id"], v["volume_lds_url"], v["volume_title"], v["volume_long_title"],
                 v["volume_subtitle"] or "", v["volume_short_title"], v["id"]),
            )
        for b in src.execute("SELECT * FROM books ORDER BY id"):
            conn.execute(
                "INSERT INTO books (id, volume_id, slug, title, long_title, subtitle, short_title, position)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (b["id"], b["volume_id"], b["book_lds_url"], clean(b["book_title"]), clean(b["book_long_title"]),
                 b["book_subtitle"] or "", b["book_short_title"], b["id"]),
            )
        conn.executemany(
            "INSERT INTO chapters (id, book_id, number) VALUES (?, ?, ?)",
            src.execute("SELECT id, book_id, chapter_number FROM chapters ORDER BY id"),
        )
        conn.executemany(
            "INSERT INTO verses (id, chapter_id, number, text) VALUES (?, ?, ?, ?)",
            ((r[0], r[1], r[2], clean(r[3])) for r in src.execute(
                "SELECT id, chapter_id, verse_number, scripture_text FROM verses ORDER BY id")),
        )
        conn.execute("INSERT INTO verses_fts(verses_fts) VALUES ('rebuild')")

    src.close()
    return conn.execute("SELECT COUNT(*) FROM verses").fetchone()[0]


def run(source: Path | None = None, conn: sqlite3.Connection | None = None) -> int:
    conn = conn or db.connect()
    db.migrate(conn)
    if not db.library_is_empty(conn):
        print("Library already loaded; nothing to do.")
        return 0
    if source is None:
        tmp = Path(tempfile.mkdtemp()) / "lds-scriptures.db"
        source = download(tmp)
    count = import_from(source, conn)
    print(f"Imported {count:,} verses.")
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, help="path to lds-scriptures-sqlite.db")
    args = parser.parse_args()
    run(args.source)
