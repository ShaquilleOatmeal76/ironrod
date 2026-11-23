# Iron Rod

A self-hosted scripture study app: read the standard works, mark them up,
link verses to talks, and keep study plans. It runs on your own server, and your
notes stay on your server.

> Dark, keyboard-friendly, and built to feel like a power tool.

## Status

| Phase | What | State |
|---|---|---|
| 1 | Foundation: repo, scripture data, reader | ✅ done |
| 2 | Markup: highlights, notes (rich editor), links | ✅ done |
| 3 | Finding things: command palette (⌘K), search, shortcuts | ✅ done |
| 4 | Talks & more: conference, BYU speeches, Come Follow Me, split view | ⏳ next |
| 5 | Plans & goals: reading plans, tracker | |
| 6 | Polish: graph view, phone layout, remote access, installable app | |
| 7 | Phone app: Capacitor wrapper, offline reading, notifications | |
| later | Family accounts, groups, private journal | |

## Run it (Docker)

```bash
git clone git@github.com:ShaquilleOatmeal76/ironrod.git
cd ironrod
docker compose up -d --build
```

Open `http://<your-server>:8080`. On first start it downloads the scripture
data (~8 MB) and loads it into `./data/ironrod.db`. That takes a few seconds.

**Back up `./data/`.** That folder is your whole library: notes, highlights,
plans.

To update later:

```bash
git pull && docker compose up -d --build
```

## Develop

You need Python 3.12+ and Node 22+.

```bash
# terminal 1: API on :8000 (first run imports the scriptures)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# terminal 2: web app on :5173 (proxies /api to :8000)
cd frontend
npm install
npm run dev
```

Tests: `cd backend && pip install pytest httpx && pytest`

## How it's built

```
ironrod/
├── backend/                 Python · FastAPI · SQLite
│   ├── app/
│   │   ├── main.py          app setup; serves /api and the built web app
│   │   ├── db.py            connection + migration runner
│   │   ├── migrations/      numbered .sql files, run once each, in order
│   │   └── routers/         API endpoints, grouped by feature
│   ├── scripts/
│   │   └── import_scriptures.py
│   └── tests/
├── frontend/                SvelteKit (Svelte 5) · built as a single-page app
│   └── src/
│       ├── app.css          theme tokens: every color and font lives here
│       ├── lib/             shared state, API client, components
│       └── routes/          pages: /read/[volume]/[book]/[chapter]
├── Dockerfile               builds the web app, then bundles it with the API
└── docker-compose.yml
```

A few ideas worth knowing:

- **One container, one port.** FastAPI answers `/api/*` and serves the built
  web app for everything else, so there's no separate web server to run.
- **Migrations, not edits.** To change the database, add
  `backend/app/migrations/002_something.sql`. It runs once on next start. Never
  edit a migration that has already run.
- **Global verse ids.** Every verse has a sequential id across the whole canon,
  so a range like *Alma 32:21–28* is just `id BETWEEN a AND b`. Highlights,
  notes and links will all point at ranges like this.
- **Notes are sanitized on the server.** Notes are rich text (HTML), and HTML
  from a browser is untrusted. Every note goes through an allowlist sanitizer
  (`backend/app/notes_html.py`) so a `<script>` can never be saved and run in
  someone else's browser (stored XSS). There's a test that tries.
- **A reference parser.** `backend/app/refs.py` turns `1 ne 3:7`, `D&C 4:2-4`
  or `heb 11` into verse id ranges, and back into labels. `@` references in
  notes, the link box, and (soon) the command palette all use it.
- **Search that can't be broken.** SQLite's full-text search has its own query
  language, so `backend/app/search.py` rebuilds every query from plain words
  and "quoted phrases" — a stray `"` or `NOT` can't cause an error. The index
  uses the Porter stemmer, so `believe` also finds `believed` and `believing`.
  Matches come back as `[{text, hit}]` pieces rather than HTML, so the UI
  highlights them without ever rendering markup.
- **Commands register themselves.** `frontend/src/lib/commands.svelte.js` holds
  the palette's command list. The layout adds global ones; the reader adds
  verse commands (highlight, note, copy) while it's open.
- **Shared reading state.** `frontend/src/lib/reader.svelte.js` holds what's
  open and selected. The header, sidebar and status bar all read from it.

## API

| Method | Path | Returns |
|---|---|---|
| GET | `/api/volumes` | volumes → books → chapter counts |
| GET | `/api/read/{volume}/{book}/{chapter}` | verses + prev/next chapter |
| GET | `/api/health` | `{"status": "ok"}` |
| GET | `/api/refs/resolve?q=alma 32:21` | verse range for a typed reference |
| GET | `/api/refs/suggest?q=` | autocomplete for `@` references |
| GET | `/api/annotations/{volume}/{book}/{chapter}` | per-verse highlight + note/link counts |
| GET | `/api/verses/{id}` | one verse: highlight, notes, links |
| PUT | `/api/highlights` | set or clear a highlight |
| GET/POST | `/api/notes` | search/filter notes · create a note |
| PATCH/DELETE | `/api/notes/{id}` | edit · delete |
| GET | `/api/tags` | tags with counts |
| POST/DELETE | `/api/links`, `/api/links/{id}` | link two verses · remove |
| GET | `/api/search?q=&scope=&kinds=&limit=&offset=` | reference, books, verses, notes and tags in one call |

Interactive docs: `http://<server>:8080/docs`

## Keyboard

Press `?` in the app for the full list.

| Key | Action |
|---|---|
| `⌘K` / `Ctrl K` or `/` | command palette: go to a verse, search, run commands |
| `j` / `k` (or ↓ / ↑) | next / previous verse |
| `]` / `[` | next / previous chapter |
| `esc` | clear selection |
| `1` `2` `3` `4` | highlight: promise · Christ · doctrine · question (press again to clear) |
| `n` | write a note on the selected verse |
| `l` | link the selected verse to another |
| `y` | copy the verse with its reference |
| `g` then `n` | all notes |
| `g` then `s` | search page |
| `g` then `r` | back to reading |
| `⌘/Ctrl + Enter` | save a note |

In the palette, start with `>` for commands only or `#` for tags; `tab` switches between all · verses · notes · commands.

In a note, type `@` for a verse (`@heb 11:1`) and `#` for a tag (`#faith`).

## Content & copyright

- **Scripture text** (KJV Bible, Book of Mormon, D&C, Pearl of Great Price)
  comes from the public-domain
  [LDS Documentation Project](https://scriptures.nephi.org/).
- **Conference talks and other Church content** (phase 4) are copyrighted by
  Intellectual Reserve, Inc. Iron Rod will fetch them for personal study on your
  own server. They are stored in `data/` and are **never committed** to this
  repo (see `.gitignore`).

This project is not affiliated with The Church of Jesus Christ of Latter-day Saints.
