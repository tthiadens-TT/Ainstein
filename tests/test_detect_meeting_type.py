"""
Tests for transcript_processor._detect_meeting_type().

Regression: a meeting was silently classified as "internal" whenever no
participant had a recognized non-Minkowski email domain — including when
Jamie simply failed to attach any email to a participant (e.g. "Speaker 1").
This misclassified a real NN Group client call (Lead3, 3 July 2026) as
internal, which skipped the meeting_reviewer's client/traject detection
(Stap 0) entirely and mis-weighted the knowledge-layer origin for that
transcript. See reviews/2026-07-04.md.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from transcript_processor import _detect_meeting_type  # noqa: E402
from models import TranscriptEvent  # noqa: E402


def _event(title: str = "Programme design", participants=None) -> TranscriptEvent:
    return TranscriptEvent(
        meeting_id="m1",
        title=title,
        started_at="2026-07-03T08:00:00Z",
        participants=participants or [],
        transcript="",
        summary="",
        recording_url=None,
        language="nl",
        source_tool="jamie",
    )


def test_all_minkowski_emails_is_internal():
    event = _event(participants=[
        {"name": "Jörgen van der Sloot", "email": "jorgen@minkowski.org"},
        {"name": "Charlotte", "email": "charlotte@minkowski.nl"},
    ])
    assert _detect_meeting_type(event) == "internal"


def test_unidentified_participants_block_internal_classification():
    """Lead3 regression: only Jörgen has an email, the other four attendees
    are unidentified "Speaker N" entries with no email field at all. This
    must NOT be classified as internal — the meeting could easily be
    external, and internal skips client detection entirely."""
    event = _event(title="Lead3 Leadership Program Design", participants=[
        {"name": "Speaker 1", "email": ""},
        {"name": "Speaker 2", "email": ""},
        {"name": "Speaker 4", "email": ""},
        {"name": "Hiske", "email": ""},
        {"name": "Jörgen van der Sloot", "email": "jorgen@minkowski.org"},
    ])
    assert _detect_meeting_type(event) != "internal"


def test_confirmed_external_participant_is_not_internal():
    event = _event(participants=[
        {"name": "Jörgen van der Sloot", "email": "jorgen@minkowski.org"},
        {"name": "Klant X", "email": "klant@nn.nl"},
    ])
    assert _detect_meeting_type(event) != "internal"


def test_no_participants_is_not_internal():
    """No confirmed Minkowski participant at all is not proof of 'internal' —
    previously an empty participants list fell through the old check
    (empty non_minkowski list) straight into 'internal'."""
    event = _event(participants=[])
    assert _detect_meeting_type(event) != "internal"


def test_internal_keyword_in_title_still_forces_internal():
    event = _event(title="Interne standup", participants=[
        {"name": "Speaker 1", "email": ""},
    ])
    assert _detect_meeting_type(event) == "internal"
