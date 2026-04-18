"""
Regression tests for memory.py.

Protects the bug that took the bot down on 2026-04-18: Anthropic SDK
content blocks (TextBlock, ToolUseBlock) are pydantic objects and
json.dumps(...) raises TypeError unless we call .model_dump() first.
"""

import json
import sys
from pathlib import Path

import pytest

# Make the project root importable when pytest is invoked from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import memory  # noqa: E402


# --- Fixtures that mimic the Anthropic SDK shape -----------------------------


class _FakeSDKBlock:
    """Stand-in for anthropic.types.TextBlock / ToolUseBlock.

    The real classes are pydantic BaseModel instances exposing .model_dump().
    We only need a .model_dump() method returning a dict — that's what
    memory._to_jsonable looks for.
    """

    def __init__(self, payload: dict):
        self._payload = payload

    def model_dump(self) -> dict:
        return dict(self._payload)


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "conversations.db"


# --- Tests for _to_jsonable --------------------------------------------------


def test_to_jsonable_passes_plain_dicts_through():
    obj = [{"role": "user", "content": "hello"}]
    assert memory._to_jsonable(obj) == obj


def test_to_jsonable_converts_sdk_block():
    block = _FakeSDKBlock({"type": "text", "text": "hi"})
    result = memory._to_jsonable(block)
    assert result == {"type": "text", "text": "hi"}


def test_to_jsonable_walks_nested_list_of_blocks():
    messages = [
        {
            "role": "assistant",
            "content": [
                _FakeSDKBlock({"type": "text", "text": "let me search"}),
                _FakeSDKBlock({
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "search_files",
                    "input": {"query": "futures"},
                }),
            ],
        },
        {"role": "user", "content": "ok"},
    ]
    result = memory._to_jsonable(messages)
    # Whole structure must now be JSON-serialisable without raising
    encoded = json.dumps(result)
    decoded = json.loads(encoded)
    assert decoded[0]["content"][0]["text"] == "let me search"
    assert decoded[0]["content"][1]["name"] == "search_files"
    assert decoded[1]["role"] == "user"


# --- Round-trip save/load ----------------------------------------------------


def test_save_load_roundtrip_with_sdk_blocks(tmp_db: Path):
    thread_ts = "1700000000.000100"
    messages = [
        {"role": "user", "content": "analyse this brief"},
        {
            "role": "assistant",
            "content": [
                _FakeSDKBlock({"type": "text", "text": "searching..."}),
                _FakeSDKBlock({
                    "type": "tool_use",
                    "id": "toolu_abc",
                    "name": "list_folder",
                    "input": {},
                }),
            ],
        },
    ]

    memory.save(thread_ts, messages, db_path=tmp_db)
    loaded = memory.load(thread_ts, db_path=tmp_db)

    assert len(loaded) == 2
    assert loaded[0]["role"] == "user"
    assert loaded[1]["content"][0]["type"] == "text"
    assert loaded[1]["content"][1]["name"] == "list_folder"


def test_load_missing_thread_returns_empty_list(tmp_db: Path):
    assert memory.load("does-not-exist", db_path=tmp_db) == []


def test_schema_version_is_written_on_first_use(tmp_db: Path):
    memory.save("t1", [{"role": "user", "content": "x"}], db_path=tmp_db)

    import sqlite3
    con = sqlite3.connect(tmp_db)
    row = con.execute(
        "SELECT value FROM schema_meta WHERE key = 'version'"
    ).fetchone()
    con.close()
    assert row is not None
    assert int(row[0]) == memory.SCHEMA_VERSION


def test_refuses_newer_schema_on_disk(tmp_db: Path):
    # Bootstrap DB then tamper with version
    memory.save("t1", [{"role": "user", "content": "x"}], db_path=tmp_db)

    import sqlite3
    con = sqlite3.connect(tmp_db)
    con.execute(
        "UPDATE schema_meta SET value = ? WHERE key = 'version'",
        (str(memory.SCHEMA_VERSION + 99),),
    )
    con.commit()
    con.close()

    with pytest.raises(RuntimeError, match="newer than code"):
        memory.load("t1", db_path=tmp_db)


def test_corrupt_row_returns_empty_list_not_crash(tmp_db: Path):
    # Write valid row first so schema is bootstrapped
    memory.save("t1", [{"role": "user", "content": "x"}], db_path=tmp_db)

    # Overwrite payload with invalid JSON
    import sqlite3
    con = sqlite3.connect(tmp_db)
    con.execute(
        "UPDATE conversations SET messages = ? WHERE thread_ts = ?",
        ("{not valid json", "t1"),
    )
    con.commit()
    con.close()

    assert memory.load("t1", db_path=tmp_db) == []
