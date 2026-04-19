"""
Feedback capture loop.

Flow:
  1. User reacts 👎 on a bot message in Slack
  2. Bot posts a thread follow-up: "what could be better?"
  3. User's next thread message is captured and appended to 07_Feedback/gaps.md
  4. search_files picks up that file automatically on future retrievals

Storage is markdown on purpose — transparent, greppable, editable, goes through git.
In-memory pending state resets on bot restart; acceptable loss (user just reacts again).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

FEEDBACK_DIR = Path(__file__).parent / "07_Feedback"
GAPS_FILE = FEEDBACK_DIR / "gaps.md"

_lock = Lock()

# Keyed by (channel, user_id) — one pending slot per user per channel.
# A new 👎 from the same user overwrites the previous pending slot.
_pending: dict[tuple[str, str], dict] = {}


def register_pending(
    channel: str,
    user_id: str,
    thread_ts: str,
    bot_message_ts: str,
    bot_excerpt: str,
) -> None:
    """Record that we are waiting for a feedback reply from this user in this thread."""
    with _lock:
        _pending[(channel, user_id)] = {
            "thread_ts": thread_ts,
            "bot_message_ts": bot_message_ts,
            "bot_excerpt": bot_excerpt[:1000],
            "asked_at": datetime.now(timezone.utc).isoformat(),
        }


def has_pending(channel: str, user_id: str, thread_ts: str) -> bool:
    with _lock:
        state = _pending.get((channel, user_id))
        return bool(state and state["thread_ts"] == thread_ts)


def pop_pending(channel: str, user_id: str, thread_ts: str) -> dict | None:
    """Return + clear the pending slot if it matches this thread; else None."""
    with _lock:
        key = (channel, user_id)
        state = _pending.get(key)
        if state and state["thread_ts"] == thread_ts:
            del _pending[key]
            return state
    return None


def _format_blockquote(text: str, limit: int = 500) -> str:
    """Render text as markdown blockquote lines (> prefix on each line)."""
    trimmed = text.strip()[:limit]
    if len(text.strip()) > limit:
        trimmed += "…"
    return "\n".join(f"> {line}" if line else ">" for line in trimmed.split("\n"))


_HEADER = (
    "# Feedback Log\n\n"
    "*Append-only. Every 👎 on a bot answer + the user's one-liner on what was missing. "
    "Picked up automatically by `search_files` so the next answer can do better.*\n\n"
    "---\n\n"
)


def append_feedback(
    thread_ts: str,
    user_id: str,
    user_name: str | None,
    skill: str | None,
    bot_excerpt: str,
    user_comment: str,
    gaps_file: Path = GAPS_FILE,
) -> None:
    """Append one feedback entry to gaps.md. Creates the file + folder if needed."""
    gaps_file.parent.mkdir(parents=True, exist_ok=True)
    fresh = not gaps_file.exists() or gaps_file.stat().st_size == 0

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    who = f"{user_name} ({user_id})" if user_name else user_id
    skill_line = f"- **Skill:** {skill}\n" if skill else ""

    entry = (
        f"## {ts} — thread `{thread_ts}`\n\n"
        f"- **User:** {who}\n"
        f"{skill_line}"
        f"- **Reaction:** 👎\n\n"
        f"**Original answer (excerpt):**\n\n"
        f"{_format_blockquote(bot_excerpt)}\n\n"
        f"**What could be better:**\n\n"
        f"{_format_blockquote(user_comment, limit=2000)}\n\n"
        f"---\n\n"
    )

    with _lock:
        with gaps_file.open("a", encoding="utf-8") as f:
            if fresh:
                f.write(_HEADER)
            f.write(entry)
