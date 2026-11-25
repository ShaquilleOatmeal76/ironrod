"""Iron Rod API server.

Serves the JSON API under /api and the built web app (SvelteKit) for every
other path, so the whole thing runs as one container on one port.
"""

import mimetypes
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import db
from app.refs import RefIndex
from app.routers import docs, graph, library, markup, plans, search

STATIC_DIR = Path(os.environ.get("IRONROD_STATIC", Path(__file__).parent / "static"))
AUTO_IMPORT = os.environ.get("IRONROD_AUTO_IMPORT", "1") == "1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = db.connect()
    applied = db.migrate(conn)
    if applied:
        print(f"Applied migrations: {', '.join(applied)}")
    if AUTO_IMPORT and db.library_is_empty(conn):
        from scripts import import_scriptures
        import_scriptures.run(conn=conn)
    app.state.conn = conn
    app.state.refs = RefIndex(conn)
    yield
    conn.close()


app = FastAPI(title="Iron Rod", lifespan=lifespan)
app.include_router(library.router)
app.include_router(markup.router)
app.include_router(search.router)
app.include_router(docs.router)
app.include_router(plans.router)
app.include_router(graph.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Web app -------------------------------------------------------------
# Built files (JS/CSS) are served directly; any other path returns index.html
# so the app's own router can handle URLs like /read/bofm/alma/32.
if STATIC_DIR.exists():
    app.mount("/_app", StaticFiles(directory=STATIC_DIR / "_app"), name="assets")

    mimetypes.add_type("application/manifest+json", ".webmanifest")
    # The page shell and service worker must always be re-checked, so a new
    # version reaches phones right after `docker compose up -d --build`.
    NO_CACHE = {"Cache-Control": "no-cache"}

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        file = (STATIC_DIR / path).resolve()
        if path and file.is_file() and STATIC_DIR.resolve() in file.parents:
            headers = NO_CACHE if file.name in ("service-worker.js", "manifest.webmanifest") else None
            return FileResponse(file, headers=headers)
        return FileResponse(STATIC_DIR / "index.html", headers=NO_CACHE)
