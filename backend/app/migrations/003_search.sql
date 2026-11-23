-- 003: Better search.
-- Rebuild the full-text indexes with the Porter stemmer, so a search for
-- "faith" also finds "faithful", and "believe" finds "believed"/"believing".

DROP TABLE verses_fts;
CREATE VIRTUAL TABLE verses_fts USING fts5(
  text, content='verses', content_rowid='id', tokenize='porter unicode61'
);
INSERT INTO verses_fts(verses_fts) VALUES ('rebuild');

DROP TABLE notes_fts;
CREATE VIRTUAL TABLE notes_fts USING fts5(
  body_text, content='notes', content_rowid='id', tokenize='porter unicode61'
);
INSERT INTO notes_fts(notes_fts) VALUES ('rebuild');
-- (the notes_ai / notes_ad / notes_au triggers from 002 keep working: they
--  look the table up by name each time they fire)
