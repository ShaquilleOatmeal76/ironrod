-- 004: Talks, speeches and lessons ("docs"), and markup on their paragraphs.
--
-- Conference talks, BYU speeches and Come Follow Me lessons are all stored the
-- same way: a doc made of numbered paragraphs. They're imported into this
-- database on your own server and never committed to the repo.

CREATE TABLE collections (
  id          INTEGER PRIMARY KEY,
  kind        TEXT NOT NULL CHECK (kind IN ('conference','byu','cfm')),
  slug        TEXT NOT NULL UNIQUE,     -- "conference/2024/10", "cfm/2026", "byu"
  title       TEXT NOT NULL,            -- "October 2024 General Conference"
  sort_key    TEXT NOT NULL,            -- newest first when sorted DESC
  imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE docs (
  id            INTEGER PRIMARY KEY,
  collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
  source_uri    TEXT NOT NULL UNIQUE,   -- where it came from (dedupes re-imports)
  source_url    TEXT NOT NULL,          -- link to read it on the original site
  title         TEXT NOT NULL,
  author        TEXT,
  author_role   TEXT,
  date_label    TEXT,                   -- "October 2024", "September 22, 2026"
  published     TEXT,                   -- YYYY-MM-DD when known (for sorting)
  position      INTEGER NOT NULL DEFAULT 0,
  -- Come Follow Me only:
  week_start    TEXT,                   -- YYYY-MM-DD
  week_end      TEXT,
  reading       TEXT,                   -- "Genesis 1–2; Moses 2–3"
  imported_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_docs_collection ON docs(collection_id, position);
CREATE INDEX idx_docs_week ON docs(week_start);

CREATE TABLE doc_paras (
  id        INTEGER PRIMARY KEY,
  doc_id    INTEGER NOT NULL REFERENCES docs(id) ON DELETE CASCADE,
  position  INTEGER NOT NULL,
  kind      TEXT NOT NULL DEFAULT 'p' CHECK (kind IN ('p','h2','h3','li','quote')),
  text      TEXT NOT NULL,
  UNIQUE (doc_id, position)
);

-- The verses a Come Follow Me lesson covers (parsed from its reading line).
CREATE TABLE doc_readings (
  doc_id          INTEGER NOT NULL REFERENCES docs(id) ON DELETE CASCADE,
  start_verse_id  INTEGER NOT NULL REFERENCES verses(id),
  end_verse_id    INTEGER NOT NULL REFERENCES verses(id),
  PRIMARY KEY (doc_id, start_verse_id, end_verse_id)
);

CREATE VIRTUAL TABLE doc_paras_fts USING fts5(
  text, content='doc_paras', content_rowid='id', tokenize='porter unicode61'
);
CREATE TRIGGER doc_paras_ai AFTER INSERT ON doc_paras BEGIN
  INSERT INTO doc_paras_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER doc_paras_ad AFTER DELETE ON doc_paras BEGIN
  INSERT INTO doc_paras_fts(doc_paras_fts, rowid, text) VALUES ('delete', old.id, old.text);
END;

-- Markup on paragraphs ------------------------------------------------------
CREATE TABLE para_highlights (
  owner_id   INTEGER NOT NULL REFERENCES users(id),
  para_id    INTEGER NOT NULL REFERENCES doc_paras(id) ON DELETE CASCADE,
  color      TEXT NOT NULL CHECK (color IN ('promise','christ','doctrine','question')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (owner_id, para_id)
);

-- A note can sit on a paragraph instead of a verse.
ALTER TABLE notes ADD COLUMN para_id INTEGER REFERENCES doc_paras(id) ON DELETE SET NULL;
CREATE INDEX idx_notes_para ON notes(para_id);

-- A link between a verse range and a talk paragraph (made in split view).
CREATE TABLE para_links (
  id              INTEGER PRIMARY KEY,
  owner_id        INTEGER NOT NULL REFERENCES users(id),
  para_id         INTEGER NOT NULL REFERENCES doc_paras(id) ON DELETE CASCADE,
  start_verse_id  INTEGER NOT NULL REFERENCES verses(id),
  end_verse_id    INTEGER NOT NULL REFERENCES verses(id),
  label           TEXT NOT NULL DEFAULT 'related',
  created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_para_links_para ON para_links(para_id);
CREATE INDEX idx_para_links_verse ON para_links(start_verse_id, end_verse_id);
