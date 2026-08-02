"""
database.py
Lightweight SQLite persistence layer. No ORM - the schema is small enough
that raw SQL stays readable and dependency-free (sqlite3 is stdlib).
"""

import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Iterable, Optional

from config import settings
from logger import get_logger

log = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_seen INTEGER,
    last_seen INTEGER,
    is_admin INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS command_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    command TEXT,
    ts INTEGER,
    success INTEGER,
    error TEXT
);

CREATE TABLE IF NOT EXISTS quiz_scores (
    user_id INTEGER PRIMARY KEY,
    score INTEGER DEFAULT 0,
    attempts INTEGER DEFAULT 0,
    correct INTEGER DEFAULT 0,
    last_played INTEGER
);

CREATE TABLE IF NOT EXISTS seen_items (
    item_hash TEXT PRIMARY KEY,
    kind TEXT,
    ts INTEGER
);

CREATE TABLE IF NOT EXISTS interview_sessions (
    user_id INTEGER PRIMARY KEY,
    topic TEXT,
    question_num INTEGER DEFAULT 0,
    current_question TEXT,
    score INTEGER DEFAULT 0,
    started_at INTEGER
);
"""


def init_db() -> None:
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    with _connect() as conn:
        conn.executescript(_SCHEMA)
    log.info("Database initialized at %s", settings.DB_PATH)


@contextmanager
def _connect():
    conn = sqlite3.connect(settings.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def upsert_user(user_id: int, username: Optional[str], is_admin: bool = False) -> None:
    now = int(time.time())
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO users (user_id, username, first_seen, last_seen, is_admin)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                last_seen=excluded.last_seen
            """,
            (user_id, username, now, now, int(is_admin)),
        )


def log_command(user_id: int, command: str, success: bool, error: str = "") -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO command_log (user_id, command, ts, success, error) VALUES (?, ?, ?, ?, ?)",
            (user_id, command, int(time.time()), int(success), error[:500]),
        )


def get_all_user_ids() -> Iterable[int]:
    with _connect() as conn:
        rows = conn.execute("SELECT user_id FROM users").fetchall()
    return [r["user_id"] for r in rows]


def get_stats() -> dict:
    with _connect() as conn:
        users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        commands = conn.execute("SELECT COUNT(*) c FROM command_log").fetchone()["c"]
        errors = conn.execute("SELECT COUNT(*) c FROM command_log WHERE success=0").fetchone()["c"]
        top = conn.execute(
            "SELECT command, COUNT(*) c FROM command_log GROUP BY command ORDER BY c DESC LIMIT 5"
        ).fetchall()
    return {
        "users": users,
        "commands_run": commands,
        "errors": errors,
        "top_commands": [(r["command"], r["c"]) for r in top],
    }


def is_item_seen(item_hash: str) -> bool:
    with _connect() as conn:
        row = conn.execute("SELECT 1 FROM seen_items WHERE item_hash=?", (item_hash,)).fetchone()
    return row is not None


def mark_item_seen(item_hash: str, kind: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO seen_items (item_hash, kind, ts) VALUES (?, ?, ?)",
            (item_hash, kind, int(time.time())),
        )


def update_quiz_score(user_id: int, correct: bool) -> dict:
    now = int(time.time())
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO quiz_scores (user_id, score, attempts, correct, last_played)
            VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                score = score + ?,
                attempts = attempts + 1,
                correct = correct + ?,
                last_played = ?
            """,
            (user_id, 1 if correct else 0, 1 if correct else 0, now,
             1 if correct else 0, 1 if correct else 0, now),
        )
        row = conn.execute("SELECT * FROM quiz_scores WHERE user_id=?", (user_id,)).fetchone()
    return dict(row)


def get_leaderboard(limit: int = 10) -> list:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT u.username, q.score, q.attempts FROM quiz_scores q "
            "JOIN users u ON u.user_id = q.user_id "
            "ORDER BY q.score DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def save_interview_session(user_id: int, topic: str, question_num: int,
                            current_question: str, score: int) -> None:
    now = int(time.time())
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO interview_sessions (user_id, topic, question_num, current_question, score, started_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                topic=excluded.topic, question_num=excluded.question_num,
                current_question=excluded.current_question, score=excluded.score
            """,
            (user_id, topic, question_num, current_question, score, now),
        )


def get_interview_session(user_id: int) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM interview_sessions WHERE user_id=?", (user_id,)).fetchone()
    return dict(row) if row else None


def clear_interview_session(user_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM interview_sessions WHERE user_id=?", (user_id,))