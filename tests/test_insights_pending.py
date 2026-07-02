"""
Tests for the Insights-pending mapping in transcript_processor.py.

Regression: _pending_insights used to hold a single doc_id per Slack channel,
so a second meeting processed shortly after the first would silently
overwrite the first meeting's mapping. An "Insights: ..." reply meant for
meeting A could then update meeting B's Google Doc instead, with no error.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import transcript_processor as tp  # noqa: E402


def setup_function(_):
    tp._pending_insights.clear()


def test_single_pending_resolves_without_hint():
    tp.register_insights_pending("C1", "doc-a", "Debrief Intervisie en next steps")
    doc_id, remaining = tp.pop_insights_pending("C1")
    assert doc_id == "doc-a"
    assert remaining == []
    # popped -> nothing left pending
    assert tp._pending_insights.get("C1") in (None, [])


def test_no_pending_returns_none_and_empty_list():
    doc_id, remaining = tp.pop_insights_pending("C-empty")
    assert doc_id is None
    assert remaining == []


def test_two_pending_without_hint_asks_instead_of_guessing():
    tp.register_insights_pending("C1", "doc-a", "Debrief Intervisie en next steps")
    tp.register_insights_pending("C1", "doc-b", "Aanpak Teamonveiligheid & Ongeschreven Regels")
    doc_id, remaining = tp.pop_insights_pending("C1", hint="goed gesprek, veel gehad aan de tips")
    assert doc_id is None
    assert len(remaining) == 2
    # nothing was consumed — both still pending for a follow-up attempt
    doc_id_a, _ = tp.pop_insights_pending("C1", hint="Debrief Intervisie en next steps")
    assert doc_id_a == "doc-a"


def test_two_pending_resolved_by_title_hint():
    tp.register_insights_pending("C1", "doc-a", "Debrief Intervisie en next steps")
    tp.register_insights_pending("C1", "doc-b", "Aanpak Teamonveiligheid & Ongeschreven Regels")
    doc_id, remaining = tp.pop_insights_pending("C1", hint="dit was over Teamonveiligheid, sterk gesprek")
    assert doc_id == "doc-b"
    assert remaining == []
    # the other meeting is still pending, unaffected
    doc_id_a, remaining_a = tp.pop_insights_pending("C1", hint="Debrief Intervisie en next steps")
    assert doc_id_a == "doc-a"
    assert remaining_a == []


def test_different_channels_are_independent():
    tp.register_insights_pending("C1", "doc-a", "Meeting A")
    tp.register_insights_pending("C2", "doc-b", "Meeting B")
    doc_id_1, _ = tp.pop_insights_pending("C1")
    doc_id_2, _ = tp.pop_insights_pending("C2")
    assert doc_id_1 == "doc-a"
    assert doc_id_2 == "doc-b"
