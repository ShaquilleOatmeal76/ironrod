"""Shared FastAPI dependencies."""

from fastapi import Request


def get_conn(request: Request):
    # One SQLite connection is opened at startup and shared (see main.py).
    # Fine for a family-sized app; reads run concurrently thanks to WAL mode.
    return request.app.state.conn
