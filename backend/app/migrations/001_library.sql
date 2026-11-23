-- 001: Library tables (read-only source text)
-- Scripture text comes from the public-domain LDS Documentation Project
-- (https://scriptures.nephi.org/) and is loaded by scripts/import_scriptures.py

CREATE TABLE volumes (
  id          INTEGER PRIMARY KEY,
  slug        TEXT NOT NULL UNIQUE,      -- "bofm", "ot", "nt", "dc-testament", "pgp"
  title       TEXT NOT NULL,             -- "Book of Mormon"
  long_title  TEXT NOT NULL,
  subtitle    TEXT NOT NULL DEFAULT '',
  short_title TEXT NOT NULL,             -- "BoM"
  position    INTEGER NOT NULL
);

CREATE TABLE books (
  id          INTEGER PRIMARY KEY,
  volume_id   INTEGER NOT NULL REFERENCES volumes(id),
  slug        TEXT NOT NULL,             -- "alma", "1-ne"
  title       TEXT NOT NULL,             -- "Alma"
  long_title  TEXT NOT NULL,             -- "The Book of Alma"
  subtitle    TEXT NOT NULL DEFAULT '',
  short_title TEXT NOT NULL,             -- "Alma"
  position    INTEGER NOT NULL,          -- order within the whole canon
  UNIQUE (volume_id, slug)
);

CREATE TABLE chapters (
  id       INTEGER PRIMARY KEY,
  book_id  INTEGER NOT NULL REFERENCES books(id),
  number   INTEGER NOT NULL,
  UNIQUE (book_id, number)
);

-- Verse ids are global and sequential across the canon, which makes
-- verse ranges (e.g. Alma 32:21-28) a simple BETWEEN query later on.
CREATE TABLE verses (
  id          INTEGER PRIMARY KEY,
  chapter_id  INTEGER NOT NULL REFERENCES chapters(id),
  number      INTEGER NOT NULL,
  text        TEXT NOT NULL,
  UNIQUE (chapter_id, number)
);

CREATE INDEX idx_books_volume ON books(volume_id);
CREATE INDEX idx_verses_chapter ON verses(chapter_id);

-- Full-text search over scripture (used by the command palette in phase 3)
CREATE VIRTUAL TABLE verses_fts USING fts5(text, content='verses', content_rowid='id');
