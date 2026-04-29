"""SQLite-backed session snapshots for the LearnGuard MVP."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / ".learnguard_runtime"
DB_PATH = RUNTIME_ROOT / "learnguard.db"


class SessionStore:
    """Persist session dictionaries without adding a third-party dependency."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save_session(self, session: dict[str, Any]) -> None:
        session_id = session["session_id"]
        payload = json.dumps(session, ensure_ascii=True, sort_keys=True)
        problem_id = str(session.get("problem_id") or session.get("task_id") or "")
        with self._connect() as connection:
            connection.execute(
                """
                insert into learning_sessions(session_id, problem_id, payload, updated_at)
                values(?, ?, ?, current_timestamp)
                on conflict(session_id) do update set
                    problem_id=excluded.problem_id,
                    payload=excluded.payload,
                    updated_at=current_timestamp
                """,
                (session_id, problem_id, payload),
            )

    def load_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "select payload from learning_sessions where session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(str(row["payload"]))

    def list_sessions(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select session_id, problem_id, payload, created_at, updated_at
                from learning_sessions
                order by updated_at desc
                """
            ).fetchall()
        return [
            {
                "session_id": str(row["session_id"]),
                "problem_id": str(row["problem_id"]),
                "payload": json.loads(str(row["payload"])),
                "created_at": str(row["created_at"]),
                "updated_at": str(row["updated_at"]),
            }
            for row in rows
        ]

    def list_session_ids(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "select session_id from learning_sessions order by updated_at desc"
            ).fetchall()
        return [str(row["session_id"]) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                create table if not exists learning_sessions (
                    session_id text primary key,
                    problem_id text not null,
                    payload text not null,
                    created_at text not null default current_timestamp,
                    updated_at text not null default current_timestamp
                )
                """
            )
