"""Import talks, speeches and lessons from the command line.

    python -m scripts.import_content conference 2024 10
    python -m scripts.import_content conference-range 2020 2024   # every April + October
    python -m scripts.import_content cfm 2026
    python -m scripts.import_content byu https://speeches.byu.edu/talks/<speaker>/<title>/ ...

Inside Docker:
    docker compose exec ironrod python -m scripts.import_content conference 2024 10
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import db  # noqa: E402
from app.importers import sources  # noqa: E402
from app.refs import RefIndex  # noqa: E402


def report(done, total, msg):
    print(f"  [{done}/{total}] {msg}", flush=True)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    conn = db.connect()
    db.migrate(conn)
    kind = argv[1]
    if kind == "conference":
        n = sources.conference(conn, int(argv[2]), int(argv[3]), report)
    elif kind == "conference-range":
        n = 0
        for y in range(int(argv[2]), int(argv[3]) + 1):
            for m in (4, 10):
                print(f"{y}-{m:02d}")
                try:
                    n += sources.conference(conn, y, m, report)
                except sources.fetch.FetchError as e:
                    print(f"  skipped: {e}")
    elif kind == "cfm":
        n = sources.come_follow_me(conn, RefIndex(conn), int(argv[2]), report)
    elif kind == "byu":
        n = sources.byu_speeches(conn, argv[2:], report)
    else:
        print(__doc__)
        return 1
    print(f"Imported {n} new.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
