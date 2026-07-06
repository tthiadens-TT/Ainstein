"""Sentinel-based parsing in update_stijl.py moet PATTERNS betrouwbaar isoleren van CORE,
en hard falen bij ontbrekende markers in plaats van stilzwijgend te dupliceren — dat
stille appenden was precies de oorzaak van de duplicatie-bug in verbal_identity.md."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from update_stijl import _extract_sentinel_block, _replace_sentinel_block, PATTERNS_START, PATTERNS_END


def test_extract_sentinel_block_isolates_patterns_from_core():
    doc = (
        "# Verbal Identity\n\n"
        "<!-- CORE:START -->\n## 1. Taalregel\nEngels voor klantgerichte output.\n<!-- CORE:END -->\n\n"
        f"{PATTERNS_START}\n## 4. Schrijfpatronen\nWaargenomen stijl.\n{PATTERNS_END}\n"
    )
    patterns = _extract_sentinel_block(doc, PATTERNS_START, PATTERNS_END)
    assert "Waargenomen stijl" in patterns
    assert "Taalregel" not in patterns
    assert "Engels voor klantgerichte" not in patterns


def test_extract_sentinel_block_raises_when_markers_missing():
    with pytest.raises(ValueError):
        _extract_sentinel_block("geen sentinels hier", PATTERNS_START, PATTERNS_END)


def test_extract_sentinel_block_raises_when_end_before_start():
    broken = f"{PATTERNS_END}\ninhoud\n{PATTERNS_START}"
    with pytest.raises(ValueError):
        _extract_sentinel_block(broken, PATTERNS_START, PATTERNS_END)


def test_replace_sentinel_block_preserves_markers_and_surrounding_text():
    doc = f"voor\n{PATTERNS_START}\noude inhoud\n{PATTERNS_END}\nna"
    nieuw = _replace_sentinel_block(doc, PATTERNS_START, PATTERNS_END, "nieuwe inhoud")
    assert "voor" in nieuw and "na" in nieuw
    assert PATTERNS_START in nieuw and PATTERNS_END in nieuw
    assert "oude inhoud" not in nieuw
    assert "nieuwe inhoud" in nieuw


def test_replace_sentinel_block_is_idempotent():
    doc = f"{PATTERNS_START}\ninhoud A\n{PATTERNS_END}"
    eerste = _replace_sentinel_block(doc, PATTERNS_START, PATTERNS_END, "inhoud B")
    tweede = _replace_sentinel_block(eerste, PATTERNS_START, PATTERNS_END, "inhoud B")
    assert _extract_sentinel_block(eerste, PATTERNS_START, PATTERNS_END) == \
        _extract_sentinel_block(tweede, PATTERNS_START, PATTERNS_END)
    # Geen duplicatie: precies één stub, ongeacht hoe vaak je vervangt
    assert tweede.count(PATTERNS_START) == 1
    assert tweede.count(PATTERNS_END) == 1


def test_replace_sentinel_block_raises_never_appends_on_missing_markers():
    """Dit is de kern van de bugfix: bij ontbrekende markers NIET stilzwijgend
    appenden (dat veroorzaakte de wekelijkse duplicatie), maar hard falen."""
    doc = "document zonder sentinels"
    with pytest.raises(ValueError):
        _replace_sentinel_block(doc, PATTERNS_START, PATTERNS_END, "nieuwe inhoud")
    # De aanroeper (main / _update_verbal_identity_in_drive) moet dit opvangen
    # en NIETS schrijven — geverifieerd in de call sites, hier alleen het contract.
