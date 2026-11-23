"""Shared FastAPI dependencies."""

from fastapi import Request


def get_conn(request: Request):
    # One SQLite connection is opened at startup and shared (see main.py).
    # Fine for a family-sized app; reads run concurrently thanks to WAL mode.
    return request.app.state.conn


def get_refs(request: Request):
    """The scripture reference parser (built once at startup)."""
    return request.app.state.refs


def get_user_id() -> int:
    # Single user for now. When family accounts arrive, this becomes
    # "read the session cookie and return that person's id" -- and every
    # endpoint that already depends on it picks that up automatically.
    return 1
