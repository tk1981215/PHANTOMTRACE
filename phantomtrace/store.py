"""Tiny SQLite history so past investigations survive restarts."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from .models import Anomaly, Event

DEFAULT_DB = "phantomtrace.db"


def _conn(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE IF NOT EXISTS runs ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, created TEXT, events TEXT, anomalies TEXT)"
    )
    return con


def save_run(name: str, events: list[Event], anomalies: list[Anomaly], path: str = DEFAULT_DB) -> int:
    with closing(_conn(path)) as con:
        cur = con.execute(
            "INSERT INTO runs (name, created, events, anomalies) VALUES (?,?,?,?)",
            (
                name,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                json.dumps([e.model_dump(mode="json") for e in events]),
                json.dumps([a.model_dump(mode="json") for a in anomalies]),
            ),
        )
        con.commit()
        return int(cur.lastrowid)


def list_runs(path: str = DEFAULT_DB) -> list[tuple[int, str, str]]:
    with closing(_conn(path)) as con:
        return con.execute("SELECT id, name, created FROM runs ORDER BY id DESC LIMIT 50").fetchall()


def load_run(run_id: int, path: str = DEFAULT_DB) -> tuple[str, list[Event], list[Anomaly]]:
    with closing(_conn(path)) as con:
        name, ev, an = con.execute("SELECT name, events, anomalies FROM runs WHERE id=?", (run_id,)).fetchone()
    return (
        name,
        [Event.model_validate(x) for x in json.loads(ev)],
        [Anomaly.model_validate(x) for x in json.loads(an)],
    )
