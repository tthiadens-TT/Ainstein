"""
Tests for jamie.infer_client_name() — the cheap, internal routing pre-fill.

Covers the regression that triggered this fix: a garbled label like
"McKinsey Benchmark en" (first 3 words of a longer title) must never be
produced. No participant-domain signal -> None, not a guess from the title.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jamie import infer_client_name  # noqa: E402
from models import TranscriptEvent  # noqa: E402


def _event(title: str, participants: list[dict]) -> TranscriptEvent:
    return TranscriptEvent(
        meeting_id="m1",
        title=title,
        started_at="2026-07-01T10:00:00Z",
        participants=participants,
        transcript="",
        summary="",
        recording_url=None,
        language="nl",
        source_tool="jamie",
    )


def test_domain_match_returns_name():
    event = _event(
        "Kennismaking",
        [
            {"name": "Jörgen van der Sloot", "email": "jorgen@minkowski.org"},
            {"name": "Anna de Vries", "email": "anna@testbv.nl"},
        ],
    )
    assert infer_client_name(event) == "Anna de Vries"


def test_no_external_participant_returns_none():
    event = _event(
        "Interne sync",
        [{"name": "Jörgen van der Sloot", "email": "jorgen@minkowski.org"}],
    )
    assert infer_client_name(event) is None


def test_no_email_at_all_returns_none():
    event = _event("Gesprek zonder e-mails", [{"name": "Onbekend"}])
    assert infer_client_name(event) is None


def test_regression_mckinsey_title_never_used_as_fallback():
    """The exact real-world bug: a long title used to get truncated to its
    first 3 words ("McKinsey Benchmark en") and shown as the client label.
    With no external participant, the function must return None — it must
    never fall back to parsing the title at all."""
    event = _event(
        "McKinsey Benchmark en Voorbereiding Managementdag",
        [{"name": "Jörgen van der Sloot", "email": "jorgen@minkowski.org"}],
    )
    result = infer_client_name(event)
    assert result is None
    assert result != "McKinsey Benchmark en"
