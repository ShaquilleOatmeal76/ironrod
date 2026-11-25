"""Phase 5 tests: reading log, range plans, goals, streaks."""

from tests.test_library import client  # noqa: F401


def read(client, ch, day, book="1-ne", read=True):
    return client.post("/api/read-log", json={"volume": "bofm", "book": book, "chapter": ch,
                                              "today": day, "read": read}).json()


def test_reading_log_and_status(client):
    s = read(client, 1, "2026-11-02")
    assert s["read_today"] is True and s["times_read"] == 1
    assert client.get("/api/read-log/bofm/1-ne/1", params={"today": "2026-11-03"}).json()["read_today"] is False
    s = read(client, 1, "2026-11-02", read=False)
    assert s["read_today"] is False


def test_range_plan(client):
    body = {"kind": "range", "from_ref": "1 Nephi 1", "to_ref": "1 Nephi 10",
            "start_date": "2026-11-02", "end_date": "2026-11-06", "days": "1111100"}
    prev = client.post("/api/plans/preview", json=body).json()
    assert prev == {"chapters": 10, "days": 5, "per_day": 2.0}
    plan = client.post("/api/plans", json=body).json()
    assert plan["total"] == 10 and plan["title"].startswith("1 Nephi 1")

    plans = client.get("/api/plans", params={"today": "2026-11-02"}).json()
    p = next(x for x in plans if x["id"] == plan["id"])
    assert [c["label"] for c in p["today"]] == ["1 Nephi 1", "1 Nephi 2"]
    assert p["behind"] is False

    read(client, 1, "2026-11-02")
    read(client, 2, "2026-11-02")
    p = next(x for x in client.get("/api/plans", params={"today": "2026-11-02"}).json() if x["id"] == plan["id"])
    assert p["done"] == 2 and all(c["done"] for c in p["today"])

    # skip Tuesday -> behind on Wednesday, and Wednesday's list catches up
    p = next(x for x in client.get("/api/plans", params={"today": "2026-11-04"}).json() if x["id"] == plan["id"])
    assert p["behind"] is True and "behind" in p["status"]
    assert [c["label"] for c in p["today"]] == ["1 Nephi 3", "1 Nephi 4", "1 Nephi 5"]

    # Saturday is not a reading day in this plan
    p = next(x for x in client.get("/api/plans", params={"today": "2026-11-07"}).json() if x["id"] == plan["id"])
    assert p["rest_day"] is True

    assert client.delete(f"/api/plans/{plan['id']}").status_code == 204
    assert all(x["id"] != plan["id"] for x in client.get("/api/plans").json())


def test_plan_validation(client):
    bad = {"kind": "range", "volume": "bofm", "start_date": "2026-11-10", "end_date": "2026-11-01"}
    assert client.post("/api/plans", json=bad).status_code == 422
    assert client.post("/api/plans", json={**bad, "end_date": "2026-12-01", "days": "0000000"}).status_code == 422
    whole = client.post("/api/plans/preview", json={**bad, "end_date": "2027-03-28"}).json()
    assert whole["chapters"] == 239


def test_goals_and_streak(client):
    client.put("/api/goals", json={"kind": "study_days", "target": 6})
    client.put("/api/goals", json={"kind": "chapters", "target": 10})
    for day in ("2026-11-15", "2026-11-16", "2026-11-17"):
        read(client, 20, day)
    s = client.get("/api/stats", params={"today": "2026-11-17"}).json()
    assert s["streak"] == 3
    g = {x["kind"]: x for x in s["goals"]}
    assert g["study_days"]["value"] == 2      # Mon 16 + Tue 17 (week starts Monday)
    assert g["chapters"]["title"] == "Read 10 chapters a week"
    assert s["week"][0]["date"] == "2026-11-16" and s["week"][1]["active"] is True
    # a missed day breaks the streak
    assert client.get("/api/stats", params={"today": "2026-11-19"}).json()["streak"] == 0
    assert client.put("/api/goals", json={"kind": "study_days", "target": 9}).status_code == 422
    client.put("/api/goals", json={"kind": "chapters", "target": 0})
    assert all(x["kind"] != "chapters" for x in client.get("/api/stats").json()["goals"])
