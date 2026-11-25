"""Run imports in the background so the web app stays responsive.

Each job runs in its own thread with its own database connection (SQLite
connections shouldn't be shared across threads for writes). Progress lives in
memory; it's only needed while the job runs.
"""

import itertools
import threading
import time
import traceback

from app import db
from app.importers import sources
from app.refs import RefIndex

_jobs: dict[int, dict] = {}
_ids = itertools.count(1)
_lock = threading.Lock()


def start(kind: str, params: dict) -> dict:
    job = {"id": next(_ids), "kind": kind, "params": params, "state": "running",
           "done": 0, "total": 0, "message": "starting…", "added": 0, "error": None,
           "started": time.time()}
    with _lock:
        _jobs[job["id"]] = job
    threading.Thread(target=_run, args=(job,), daemon=True).start()
    return job


def _run(job):
    conn = db.connect()

    def report(done, total, message):
        job.update(done=done, total=total, message=message)

    try:
        p = job["params"]
        if job["kind"] == "conference":
            job["added"] = sources.conference(conn, p["year"], p["month"], report)
        elif job["kind"] == "cfm":
            job["added"] = sources.come_follow_me(conn, RefIndex(conn), p["year"], report)
        elif job["kind"] == "byu":
            job["added"] = sources.byu_speeches(conn, p["urls"], report)
        job["state"] = "done"
    except sources.fetch.FetchError as e:
        job.update(state="error", error=str(e))
    except Exception as e:  # keep the server alive; show the error in the UI
        traceback.print_exc()
        job.update(state="error", error=f"{type(e).__name__}: {e}")
    finally:
        conn.close()


def running_kinds() -> set[str]:
    return {j["kind"] for j in _jobs.values() if j["state"] == "running"}


def all_jobs() -> list[dict]:
    with _lock:
        return sorted(_jobs.values(), key=lambda j: -j["id"])[:20]
