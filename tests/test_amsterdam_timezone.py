"""
Regression test for slack_app._AMS — the Amsterdam-timezone constant used in
start/stop/crash status messages.

Bug (flagged daily-review 2026-07-04, herbevestigd 2026-07-08): start_time,
shutdown_time en crash_time gebruikten `datetime.now()` (naive, server-local —
UTC op de VM) maar het bericht labelde dit als "(Amsterdam)". Op 8 juli
zichtbaar: 4 restart-berichten tussen 07:03-07:47 CEST meldden zichzelf als
"05:xx (Amsterdam)". Fix: `datetime.now(_AMS)`, hetzelfde patroon als
agent.py:19 al gebruikte voor de systeemprompt-datum.
"""

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from slack_app import _AMS  # noqa: E402


def test_ams_is_europe_amsterdam():
    assert _AMS.key == "Europe/Amsterdam"


def test_ams_formats_with_cest_or_cet_offset():
    """Een Amsterdam-tijd moet altijd een niet-lege, herkenbare UTC-offset
    hebben (CET +01:00 of CEST +02:00) — nooit de kale UTC-offset (+00:00)
    die de oorspronkelijke bug stilzwijgend als 'Amsterdam' labelde."""
    now_ams = datetime.now(_AMS)
    offset = now_ams.utcoffset()
    assert offset is not None
    assert offset.total_seconds() in (3600, 7200)  # +01:00 (CET) of +02:00 (CEST)
