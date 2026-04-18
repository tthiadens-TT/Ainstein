"""
Persistent conversation memory using SQLite.
Stores message history per Slack thread so conversations survive restarts.
"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "conversations.db"


def _to_jsonable(obj):
    """Convert Anthropic SDK content blocks (pydantic) to plain dicts."""
    if isinstance(obj, list):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    # pydantic / SDK objects expose .model_dump()
    dump = getattr(obj, "model_dump", None)
    if callable(dump):
        return dump()
    return obj


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            thread_ts TEXT PRIMARY KEY,
            messages  TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.commit()
    return con


def load(thread_ts: str) -> list:
    with _conn() as con:
        row = con.execute(
            "SELECT messages FROM conversations WHERE thread_ts = ?", (thread_ts,)
        ).fetchone()
    return json.loads(row[0]) if row else []


def save(thread_ts: str, messages: list) -> None:
    with _conn() as con:
        con.execute(
            """INSERT INTO conversations (thread_ts, messages, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(thread_ts) DO UPDATE SET
                 messages = excluded.messages,
                 updated_at = CURRENT_TIMESTAMP""",
            (thread_ts, json.dumps(_to_jsonable(messages), ensure_ascii=False)),
        )
