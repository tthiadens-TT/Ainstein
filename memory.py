"""
Persistent conversation memory using SQLite.
Stores message history per Slack thread so conversations survive restarts.
"""

import json
import sqlite3
import sys
from pathlib import Path

import log_setup

logger = log_setup.get_logger("memory")

DB_PATH = Path(__file__).parent / "conversations.db"

# Bump whenever the on-disk message shape changes incompatibly.
SCHEMA_VERSION = 1


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


def _conn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            thread_ts TEXT PRIMARY KEY,
            messages  TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS schema_meta (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    row = con.execute("SELECT value FROM schema_meta WHERE key = 'version'").fetchone()
    if row is None:
        con.execute(
            "INSERT INTO schema_meta (key, value) VALUES ('version', ?)",
            (str(SCHEMA_VERSION),),
        )
    else:
        on_disk = int(row[0])
        if on_disk > SCHEMA_VERSION:
            # Running old code against newer DB — refuse rather than corrupt it
            raise RuntimeError(
                f"conversations.db schema version {on_disk} is newer than code "
                f"({SCHEMA_VERSION}). Upgrade the code or wipe the DB."
            )
        if on_disk < SCHEMA_VERSION:
            # Forward migration hook — for now just log; add steps per bump.
            logger.info("migrating conversations.db from v%d to v%d", on_disk, SCHEMA_VERSION)
            con.execute(
                "UPDATE schema_meta SET value = ? WHERE key = 'version'",
                (str(SCHEMA_VERSION),),
            )
    con.commit()
    return con


def load(thread_ts: str, db_path: Path = DB_PATH) -> list:
    with _conn(db_path) as con:
        row = con.execute(
            "SELECT messages FROM conversations WHERE thread_ts = ?", (thread_ts,)
        ).fetchone()
    if not row:
        return []
    try:
        return json.loads(row[0])
    except json.JSONDecodeError as e:
        logger.error("unreadable row for thread_ts=%s: %s — returning empty history", thread_ts, e)
        return []


def save(thread_ts: str, messages: list, db_path: Path = DB_PATH) -> None:
    with _conn(db_path) as con:
        con.execute(
            """INSERT INTO conversations (thread_ts, messages, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(thread_ts) DO UPDATE SET
                 messages = excluded.messages,
                 updated_at = CURRENT_TIMESTAMP""",
            (thread_ts, json.dumps(_to_jsonable(messages), ensure_ascii=False)),
        )
