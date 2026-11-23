"""Iron Rod API server.

Serves the JSON API under /api and the built web app (SvelteKit) for every
other path, so the whole thing runs as one container on one port.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import db
from app.refs import RefIndex
from app.routers import library, markup, search

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


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Web app -------------------------------------------------------------
# Built files (JS/CSS) are served directly; any other path returns index.html
# so the app's own router can handle URLs like /read/bofm/alma/32.
if STATIC_DIR.exists():
    app.mount("/_app", StaticFiles(directory=STATIC_DIR / "_app"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        file = (STATIC_DIR / path).resolve()
        if path and file.is_file() and STATIC_DIR.resolve() in file.parents:
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")
