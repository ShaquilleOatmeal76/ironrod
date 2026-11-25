-- 005: Reading tracker, plans and goals.

-- Every chapter you mark read, by day. One row per chapter per day.
CREATE TABLE reading_log (
  owner_id    INTEGER NOT NULL REFERENCES users(id),
  chapter_id  INTEGER NOT NULL REFERENCES chapters(id),
  read_on     TEXT NOT NULL,            -- YYYY-MM-DD in the reader's time zone
  created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (owner_id, chapter_id, read_on)
);
CREATE INDEX idx_reading_log_day ON reading_log(owner_id, read_on);

-- A plan is either a run of chapters to finish by a date ("range"),
-- or following a year's Come Follow Me schedule ("cfm").
CREATE TABLE plans (
  id               INTEGER PRIMARY KEY,
  owner_id         INTEGER NOT NULL REFERENCES users(id),
  title            TEXT NOT NULL,
  kind             TEXT NOT NULL CHECK (kind IN ('range','cfm')),
  first_chapter_id INTEGER REFERENCES chapters(id),
  last_chapter_id  INTEGER REFERENCES chapters(id),
  start_date       TEXT NOT NULL,       -- YYYY-MM-DD
  end_date         TEXT,                -- YYYY-MM-DD (range plans)
  days             TEXT NOT NULL DEFAULT '1111111',  -- Mon..Sun reading days
  cfm_year         INTEGER,
  archived         INTEGER NOT NULL DEFAULT 0,
  created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Chapters finished within a plan (a chapter read before the plan started
-- doesn't count toward it).
CREATE TABLE plan_done (
  plan_id     INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  chapter_id  INTEGER NOT NULL REFERENCES chapters(id),
  done_on     TEXT NOT NULL,
  PRIMARY KEY (plan_id, chapter_id)
);

-- Weekly goals: study N days, write N notes, read N chapters.
CREATE TABLE goals (
  id         INTEGER PRIMARY KEY,
  owner_id   INTEGER NOT NULL REFERENCES users(id),
  kind       TEXT NOT NULL CHECK (kind IN ('study_days','notes','chapters')),
  target     INTEGER NOT NULL CHECK (target > 0),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (owner_id, kind)
);
