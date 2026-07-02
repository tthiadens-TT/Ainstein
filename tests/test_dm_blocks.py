"""
Tests for the Slack Block Kit builders in transcript_processor.py.

Covers:
- _chunk_text respects Slack's ~3000-char section-text limit (the safety
  concern _post_chunked used to cover before the DM moved to Block Kit).
- _build_dm_blocks produces title/analysis/button/insights blocks, not one
  flat text blob.
- _build_channel_blocks (previously dead code, duplicated inline) now takes
  debrief_text and extracts the "Klant/traject:" line itself.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import transcript_processor as tp  # noqa: E402
from models import TranscriptEvent  # noqa: E402


def _event(title: str = "Debrief Intervisie en next steps") -> TranscriptEvent:
    return TranscriptEvent(
        meeting_id="m1",
        title=title,
        started_at="2026-07-01T10:00:00Z",
        participants=[],
        transcript="",
        summary="",
        recording_url=None,
        language="nl",
        source_tool="jamie",
    )


def test_chunk_text_empty_returns_empty_list():
    assert tp._chunk_text("") == []


def test_chunk_text_short_text_single_chunk():
    text = "Korte analyse van een meeting."
    assert tp._chunk_text(text) == [text]


def test_chunk_text_splits_long_text_under_slack_limit():
    text = "x" * 7000
    chunks = tp._chunk_text(text)
    assert len(chunks) == 3
    assert all(len(c) <= 2900 for c in chunks)
    assert "".join(chunks) == text


def test_build_dm_blocks_has_title_analysis_button_and_insights():
    event = _event()
    debrief = "**Klant/traject:** NN Group\n\n**Taken — Ainstein's analyse:**\n- iets"
    blocks = tp._build_dm_blocks(event, debrief, "https://docs.google.com/document/d/abc")

    texts = [b["text"]["text"] for b in blocks if b["type"] == "section"]
    assert any(event.title in t for t in texts)
    assert any("NN Group" in t for t in texts)
    assert any(b["type"] == "actions" for b in blocks)
    assert any(
        b["type"] == "context" and "Insights:" in b["elements"][0]["text"]
        for b in blocks
    )


def test_build_dm_blocks_without_doc_url_has_no_button_or_insights():
    event = _event()
    blocks = tp._build_dm_blocks(event, "**Klant/traject:** onbekend", None)
    assert not any(b["type"] == "actions" for b in blocks)
    assert not any(b["type"] == "context" for b in blocks)


def test_build_channel_blocks_extracts_client_line_and_dm_status():
    event = _event()
    debrief = "**Klant/traject:** Inkomen Collectief\n\n**Taken:**\n- iets"
    blocks = tp._build_channel_blocks(event, debrief, "https://docs.google.com/x", [("Jörgen", "U1")])

    header = blocks[0]["text"]["text"]
    assert "Inkomen Collectief" in header
    assert any(b["type"] == "actions" for b in blocks)
    assert any(
        b["type"] == "context" and "<@U1>" in b["elements"][0]["text"]
        for b in blocks
    )
