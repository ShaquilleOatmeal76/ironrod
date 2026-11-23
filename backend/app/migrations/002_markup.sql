-- 002: Markup -- highlights, notes, tags and links.
--
-- Everything points at a verse RANGE (start_verse_id..end_verse_id). Because
-- verse ids are sequential across the canon, "does this note touch verse X?"
-- is just: start_verse_id <= X AND end_verse_id >= X.
--
-- owner_id is here from day one so family accounts can slot in later.
-- Until then everything belongs to user 1.

CREATE TABLE users (
  id            INTEGER PRIMARY KEY,
  username      TEXT NOT NULL UNIQUE,
  display_name  TEXT NOT NULL,
  created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO users (id, username, display_name) VALUES (1, 'me', 'Me');

CREATE TABLE highlights (
  id              INTEGER PRIMARY KEY,
  owner_id        INTEGER NOT NULL REFERENCES users(id),
  start_verse_id  INTEGER NOT NULL REFERENCES verses(id),
  end_verse_id    INTEGER NOT NULL REFERENCES verses(id),
  color           TEXT NOT NULL CHECK (color IN ('promise','christ','doctrine','question')),
  created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (end_verse_id >= start_verse_id)
);
CREATE INDEX idx_highlights_range ON highlights(owner_id, start_verse_id, end_verse_id);

CREATE TABLE notes (
  id              INTEGER PRIMARY KEY,
  owner_id        INTEGER NOT NULL REFERENCES users(id),
  start_verse_id  INTEGER REFERENCES verses(id),   -- NULL = free-standing note
  end_verse_id    INTEGER REFERENCES verses(id),
  body_html       TEXT NOT NULL,                   -- sanitized on the server
  body_text       TEXT NOT NULL,                   -- plain text, for search
  visibility      TEXT NOT NULL DEFAULT 'household'
                  CHECK (visibility IN ('private','household','selected')),
  created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_notes_range ON notes(start_verse_id, end_verse_id);

-- Verse references written inside a note with @ (e.g. "@Hebrews 11:1").
-- They make the note show up on those verses too, as "mentioned in".
CREATE TABLE note_refs (
  note_id         INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
  start_verse_id  INTEGER NOT NULL REFERENCES verses(id),
  end_verse_id    INTEGER NOT NULL REFERENCES verses(id),
  PRIMARY KEY (note_id, start_verse_id, end_verse_id)
);
CREATE INDEX idx_note_refs_range ON note_refs(start_verse_id, end_verse_id);

CREATE TABLE tags (
  id    INTEGER PRIMARY KEY,
  name  TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE note_tags (
  note_id  INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
  tag_id   INTEGER NOT NULL REFERENCES tags(id),
  PRIMARY KEY (note_id, tag_id)
);

-- A link connects two verse ranges. Stored once; shown from both ends.
CREATE TABLE links (
  id               INTEGER PRIMARY KEY,
  owner_id         INTEGER NOT NULL REFERENCES users(id),
  a_start_verse_id INTEGER NOT NULL REFERENCES verses(id),
  a_end_verse_id   INTEGER NOT NULL REFERENCES verses(id),
  b_start_verse_id INTEGER NOT NULL REFERENCES verses(id),
  b_end_verse_id   INTEGER NOT NULL REFERENCES verses(id),
  label            TEXT NOT NULL DEFAULT 'related',
  created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_links_a ON links(a_start_verse_id, a_end_verse_id);
CREATE INDEX idx_links_b ON links(b_start_verse_id, b_end_verse_id);

-- Search over notes (command palette, phase 3). Kept in sync by triggers.
CREATE VIRTUAL TABLE notes_fts USING fts5(body_text, content='notes', content_rowid='id');
CREATE TRIGGER notes_ai AFTER INSERT ON notes BEGIN
  INSERT INTO notes_fts(rowid, body_text) VALUES (new.id, new.body_text);
END;
CREATE TRIGGER notes_ad AFTER DELETE ON notes BEGIN
  INSERT INTO notes_fts(notes_fts, rowid, body_text) VALUES ('delete', old.id, old.body_text);
END;
CREATE TRIGGER notes_au AFTER UPDATE OF body_text ON notes BEGIN
  INSERT INTO notes_fts(notes_fts, rowid, body_text) VALUES ('delete', old.id, old.body_text);
  INSERT INTO notes_fts(rowid, body_text) VALUES (new.id, new.body_text);
END;

-- Clean up "--" left in a few book titles by the source dataset.
UPDATE books SET title = REPLACE(title, '--', '—'), long_title = REPLACE(long_title, '--', '—');
