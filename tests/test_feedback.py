"""
Tests for feedback.py — the learning loop.

Covers:
- Pending-state machine (register / has / pop)
- capture_feedback writes valid markdown with Type, Category, Source
- Header is written once, subsequent entries don't duplicate it
- Multi-line user comments render as clean blockquotes
- Backwards-compat alias append_feedback
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import feedback  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_pending_state():
    """Reset the in-memory pending dict between tests."""
    feedback._pending.clear()
    yield
    feedback._pending.clear()


@pytest.fixture
def gaps_file(tmp_path: Path) -> Path:
    return tmp_path / "gaps.md"


# --- Pending state machine ---------------------------------------------------


def test_register_then_has_pending():
    feedback.register_pending("C1", "U1", "1700.000", "1700.000", "excerpt")
    assert feedback.has_pending("C1", "U1", "1700.000") is True


def test_has_pending_requires_matching_thread():
    feedback.register_pending("C1", "U1", "1700.000", "1700.000", "excerpt")
    assert feedback.has_pending("C1", "U1", "9999.000") is False


def test_has_pending_is_per_user():
    feedback.register_pending("C1", "U1", "1700.000", "1700.000", "excerpt")
    assert feedback.has_pending("C1", "U2", "1700.000") is False


def test_pop_pending_clears_state():
    feedback.register_pending("C1", "U1", "1700.000", "1700.000", "excerpt")
    state = feedback.pop_pending("C1", "U1", "1700.000")
    assert state is not None
    assert state["bot_excerpt"] == "excerpt"
    assert feedback.has_pending("C1", "U1", "1700.000") is False


def test_pop_pending_returns_none_when_thread_mismatches():
    feedback.register_pending("C1", "U1", "1700.000", "1700.000", "excerpt")
    assert feedback.pop_pending("C1", "U1", "9999.000") is None
    # Original slot should still be there
    assert feedback.has_pending("C1", "U1", "1700.000") is True


def test_second_register_overwrites_first():
    feedback.register_pending("C1", "U1", "1700.000", "1700.000", "first")
    feedback.register_pending("C1", "U1", "1800.000", "1800.000", "second")
    state = feedback.pop_pending("C1", "U1", "1800.000")
    assert state is not None
    assert state["bot_excerpt"] == "second"


# --- Markdown writing — capture_feedback -------------------------------------


def test_capture_feedback_creates_file_with_header(gaps_file: Path):
    feedback.capture_feedback(
        thread_id="1700.123",
        user_id="U1",
        user_name="Thomas",
        skill="analyse_opportunity",
        bot_excerpt="Our indicative tier is mid-market, around €60k.",
        user_comment="Missed that we asked for 3 languages — that pushes the tier.",
        feedback_type="qualitative",
        category="missende-inhoud",
        source="slack",
        gaps_file=gaps_file,
    )

    content = gaps_file.read_text(encoding="utf-8")
    assert content.count("# Feedback Log") == 1
    assert "thread `1700.123`" in content
    assert "Thomas (U1)" in content
    assert "analyse_opportunity" in content
    assert "**Source:** slack" in content
    assert "**Type:** qualitative" in content
    assert "**Category:** missende-inhoud" in content
    assert "> Missed that we asked for 3 languages" in content
    assert "> Our indicative tier is mid-market" in content


def test_capture_feedback_second_entry_does_not_duplicate_header(gaps_file: Path):
    feedback.capture_feedback(
        thread_id="1700.123",
        user_id="U1",
        user_name="Thomas",
        skill=None,
        bot_excerpt="first answer",
        user_comment="first critique",
        feedback_type="technical",
        category="hallucinatie",
        source="slack",
        gaps_file=gaps_file,
    )
    feedback.capture_feedback(
        thread_id="1800.456",
        user_id="U2",
        user_name=None,
        skill="build_proposal",
        bot_excerpt="second answer",
        user_comment="second critique",
        feedback_type="qualitative",
        category="commercieel-zwak",
        source="inline",
        gaps_file=gaps_file,
    )
    content = gaps_file.read_text(encoding="utf-8")
    assert content.count("# Feedback Log") == 1
    assert "thread `1700.123`" in content
    assert "thread `1800.456`" in content
    assert "**Source:** slack" in content
    assert "**Source:** inline" in content
    assert "**Type:** technical" in content
    assert "**Type:** qualitative" in content


def test_capture_feedback_handles_missing_user_name(gaps_file: Path):
    feedback.capture_feedback(
        thread_id="1700.123",
        user_id="U1",
        user_name=None,
        skill=None,
        bot_excerpt="answer",
        user_comment="critique",
        feedback_type="qualitative",
        category="te-generiek",
        source="slack",
        gaps_file=gaps_file,
    )
    content = gaps_file.read_text(encoding="utf-8")
    assert "**User:** U1" in content
    assert "(U1)" not in content


def test_multiline_comment_renders_as_blockquote(gaps_file: Path):
    feedback.capture_feedback(
        thread_id="1700.123",
        user_id="U1",
        user_name="Thomas",
        skill=None,
        bot_excerpt="short",
        user_comment="line one\nline two\nline three",
        feedback_type="qualitative",
        category="missende-inhoud",
        source="slack",
        gaps_file=gaps_file,
    )
    content = gaps_file.read_text(encoding="utf-8")
    assert "> line one" in content
    assert "> line two" in content
    assert "> line three" in content


def test_creates_parent_folder_if_missing(tmp_path: Path):
    nested = tmp_path / "does_not_exist" / "gaps.md"
    feedback.capture_feedback(
        thread_id="1700.123",
        user_id="U1",
        user_name=None,
        skill=None,
        bot_excerpt="a",
        user_comment="b",
        feedback_type="qualitative",
        category="missende-inhoud",
        source="slack",
        gaps_file=nested,
    )
    assert nested.exists()
    assert "Feedback Log" in nested.read_text(encoding="utf-8")


# --- Label normalisation -----------------------------------------------------


def test_unknown_type_falls_back_to_qualitative(gaps_file: Path):
    feedback.capture_feedback(
        thread_id="1",
        user_id="U1",
        user_name=None,
        skill=None,
        bot_excerpt="x",
        user_comment="y",
        feedback_type="onzin",
        category="missende-inhoud",
        source="slack",
        gaps_file=gaps_file,
    )
    content = gaps_file.read_text(encoding="utf-8")
    assert "**Type:** qualitative" in content


# --- Backwards-compat alias --------------------------------------------------


def test_append_feedback_alias_still_works(gaps_file: Path):
    feedback.append_feedback(
        thread_ts="1700.123",
        user_id="U1",
        user_name="Thomas",
        skill="analyse_opportunity",
        bot_excerpt="answer",
        user_comment="critique",
        gaps_file=gaps_file,
    )
    content = gaps_file.read_text(encoding="utf-8")
    assert "thread `1700.123`" in content
    # Default labels applied
    assert "**Type:** qualitative" in content
    assert "**Category:** missende-inhoud" in content
    assert "**Source:** slack" in content
