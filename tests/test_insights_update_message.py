"""
Tests for slack_app._insights_update_message().

Regression: the DM handler for "Insights: ..." replies showed an
unconditional "✅ Insights toegevoegd" regardless of whether the two
placeholder replacements in the Meetingnote actually succeeded.
update_gdoc_section() never raises on a missing placeholder — it returns
status "not_found" instead. On 3 July 2026 this was harmless (the RS&Z doc's
placeholder happened to already be filled in correctly), but a wrong name
could have been left in place with a false "✅" confirmation. See
reviews/2026-07-04.md.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from slack_app import _insights_update_message  # noqa: E402


def _ok():
    return {"doc_id": "d1", "occurrences_changed": 1, "status": "ok"}


def _not_found():
    return {"doc_id": "d1", "occurrences_changed": 0, "status": "not_found"}


def test_both_ok_shows_success():
    msg = _insights_update_message(_ok(), _ok())
    assert msg == "✅ Insights toegevoegd aan de Meetingnote."


def test_text_placeholder_missing_flags_partial():
    msg = _insights_update_message(_not_found(), _ok())
    assert "⚠️" in msg
    assert "Insights-tekst" in msg
    assert "Insights-header" not in msg


def test_header_placeholder_missing_flags_partial():
    msg = _insights_update_message(_ok(), _not_found())
    assert "⚠️" in msg
    assert "Insights-header" in msg
    assert "Insights-tekst" not in msg


def test_both_missing_flags_both():
    msg = _insights_update_message(_not_found(), _not_found())
    assert "⚠️" in msg
    assert "Insights-tekst" in msg
    assert "Insights-header" in msg
