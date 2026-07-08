"""
Tests for transcript_processor._extract_client_line() — pulls the
"**Klant/traject:**" line the meeting_reviewer skill must emit (Stap 0),
so the #ainstein-status post shows Ainstein's own verified determination
instead of the raw jamie.py pre-fill guess.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from transcript_processor import _extract_client_line  # noqa: E402


def test_extracts_simple_value():
    debrief = "**Klant/traject:** NN Group\n\n**Taken — Ainstein's analyse:**\n- iets"
    assert _extract_client_line(debrief) == "NN Group"


def test_extracts_labeled_suggestion_line():
    debrief = (
        "**Klant/traject:** Geen klantnaam genoemd. Op basis van de facilitators "
        "zou dit LEAD3 of Inkomen Collectief kunnen zijn — klopt dat?\n\n**Taken**"
    )
    result = _extract_client_line(debrief)
    assert result is not None
    assert "LEAD3" in result and "Inkomen Collectief" in result


def test_returns_none_when_line_absent():
    debrief = "**Taken — Ainstein's analyse:**\n- iets zonder klantregel"
    assert _extract_client_line(debrief) is None


def test_returns_none_for_empty_input():
    assert _extract_client_line("") is None
    assert _extract_client_line(None) is None


def test_strips_em_dash_core_violation():
    """Daily-review 2026-07-08: het model negeert het CORE em dash-verbod
    herhaaldelijk (~2/3 van de gevallen) in deze vrije-tekstregel. Mechanische
    guard i.p.v. alleen op prompt-adherentie vertrouwen."""
    debrief = "**Klant/traject:** Test BV — eerste contact, 26 juni 2026.\n\n**Taken**"
    result = _extract_client_line(debrief)
    assert "—" not in result
    assert result == "Test BV, eerste contact, 26 juni 2026."
