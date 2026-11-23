# Iron Rod

A self-hosted scripture study app: read the standard works, mark them up,
link verses to talks, and keep study plans. It runs on your own server, and your
notes stay on your server.

> Dark, keyboard-friendly, and built to feel like a power tool.

## Status

| Phase | What | State |
|---|---|---|
| 1 | Foundation: repo, scripture data, reader | ✅ done |
| 2 | Markup: highlights, notes (rich editor), links | ⏳ next |
| 3 | Finding things: command palette (⌘K), search, shortcuts | |
| 4 | Talks & more: conference, BYU speeches, Come Follow Me, split view | |
| 5 | Plans & goals: reading plans, tracker | |
| 6 | Polish: graph view, phone layout, remote access | |
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
- **Shared reading state.** `frontend/src/lib/reader.svelte.js` holds what's
  open and selected. The header, sidebar and status bar all read from it.

## API

| Method | Path | Returns |
|---|---|---|
| GET | `/api/volumes` | volumes → books → chapter counts |
| GET | `/api/read/{volume}/{book}/{chapter}` | verses + prev/next chapter |
| GET | `/api/health` | `{"status": "ok"}` |

Interactive docs: `http://<server>:8080/docs`

## Keyboard

| Key | Action |
|---|---|
| `j` / `k` (or ↓ / ↑) | next / previous verse |
| `]` / `[` | next / previous chapter |
| `esc` | clear selection |

## Content & copyright

- **Scripture text** (KJV Bible, Book of Mormon, D&C, Pearl of Great Price)
  comes from the public-domain
  [LDS Documentation Project](https://scriptures.nephi.org/).
- **Conference talks and other Church content** (phase 4) are copyrighted by
  Intellectual Reserve, Inc. Iron Rod will fetch them for personal study on your
  own server. They are stored in `data/` and are **never committed** to this
  repo (see `.gitignore`).

This project is not affiliated with The Church of Jesus Christ of Latter-day Saints.
