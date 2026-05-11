"""
Feedback capture loop — kanaal-onafhankelijk.

Flow (Slack 👎):
  1. User reacts 👎 on a bot message in Slack
  2. Bot posts a thread follow-up: "what could be better?"
  3. User's next thread message is captured, classified (technical/qualitative + sub-label),
     and appended to 07_Feedback/gaps.md
  4. search_files picks up that file automatically on future retrievals

Flow (inline correction):
  - Agent calls record_correction tool when user corrects mid-conversation.
  - That tool routes into capture_feedback with source="inline".

Storage is markdown on purpose — transparent, greppable, editable, goes through git.
In-memory pending state resets on bot restart; acceptable loss (user just reacts again).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from tools import SOURCE_ROOT

FEEDBACK_DIR = SOURCE_ROOT / "07_Feedback"
GAPS_FILE = FEEDBACK_DIR / "gaps.md"

# Vaste labelset. Auto-classifier moet hieruit kiezen; gebruiker kan overrulen.
FEEDBACK_TYPES = ("technical", "qualitative")

TECHNICAL_CATEGORIES = (
    "hallucinatie",
    "context-misverstand",
    "onleesbaar-bestand",
    "tool-fout",
    "verkeerde-bron-gekozen",
)

QUALITATIVE_CATEGORIES = (
    "commercieel-zwak",
    "tone-of-voice",
    "missende-inhoud",
    "verkeerde-logica",
    "niet-Minkowski",
    "te-generiek",
)

ALL_CATEGORIES = TECHNICAL_CATEGORIES + QUALITATIVE_CATEGORIES


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
    "*Append-only. Elke 👎 of inline correctie + classificatie (Type + Category). "
    "Picked up automatically by `search_files` so the next answer can do better. "
    "Run `/feedback-review` periodically to surface patterns and propose edits.*\n\n"
    "---\n\n"
)


def _normalise_type(feedback_type: str | None) -> str:
    if feedback_type and feedback_type.lower() in FEEDBACK_TYPES:
        return feedback_type.lower()
    return "qualitative"  # safest default — surfaces in /feedback-review review


def _normalise_category(category: str | None) -> str:
    if category and category in ALL_CATEGORIES:
        return category
    return "missende-inhoud" if category is None else category


def capture_feedback(
    thread_id: str,
    user_id: str,
    user_name: str | None,
    skill: str | None,
    bot_excerpt: str,
    user_comment: str,
    feedback_type: str,
    category: str,
    source: str = "slack",
    gaps_file: Path = GAPS_FILE,
) -> None:
    """Append one feedback entry to gaps.md. Creates the file + folder if needed.

    feedback_type: "technical" | "qualitative" (see FEEDBACK_TYPES)
    category:      one of TECHNICAL_CATEGORIES / QUALITATIVE_CATEGORIES
    source:        "slack" | "inline" | "cli" | "web" — capture channel
    """
    gaps_file.parent.mkdir(parents=True, exist_ok=True)
    fresh = not gaps_file.exists() or gaps_file.stat().st_size == 0

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    who = f"{user_name} ({user_id})" if user_name else user_id
    skill_line = f"- **Skill:** {skill}\n" if skill else ""

    ftype = _normalise_type(feedback_type)
    cat = _normalise_category(category)

    entry = (
        f"## {ts} — thread `{thread_id}`\n\n"
        f"- **User:** {who}\n"
        f"{skill_line}"
        f"- **Source:** {source}\n"
        f"- **Type:** {ftype}\n"
        f"- **Category:** {cat}\n\n"
        f"**Original answer (excerpt):**\n\n"
        f"{_format_blockquote(bot_excerpt)}\n\n"
        f"**What could be better:**\n\n"
        f"{_format_blockquote(user_comment, limit=2000)}\n\n"
        f"---\n\n"
    )

    with _lock:
        from tools import _is_drive_mode, drive_append_feedback
        if _is_drive_mode():
            # Drive API mode: upload via service account (no local filesystem write)
            drive_append_feedback(entry=entry, header=_HEADER if fresh else "")
        else:
            # Filesystem mode: append directly to local gaps.md
            gaps_file.parent.mkdir(parents=True, exist_ok=True)
            with gaps_file.open("a", encoding="utf-8") as f:
                if fresh:
                    f.write(_HEADER)
                f.write(entry)


# Backwards-compatible alias — kept so existing callers keep working until
# every call site has been migrated. New code should call capture_feedback.
def append_feedback(
    thread_ts: str,
    user_id: str,
    user_name: str | None,
    skill: str | None,
    bot_excerpt: str,
    user_comment: str,
    feedback_type: str = "qualitative",
    category: str = "missende-inhoud",
    source: str = "slack",
    gaps_file: Path = GAPS_FILE,
) -> None:
    capture_feedback(
        thread_id=thread_ts,
        user_id=user_id,
        user_name=user_name,
        skill=skill,
        bot_excerpt=bot_excerpt,
        user_comment=user_comment,
        feedback_type=feedback_type,
        category=category,
        source=source,
        gaps_file=gaps_file,
    )
