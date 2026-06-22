#!/usr/bin/env python3
"""Backfill historische Jamie-meetings naar decisions.jsonl.

Recovert vergaderingen die zijn verwerkt vóór de fix in transcript_processor.py
(commit 29c1586) — toen werd de trace nooit geschreven. Bron: #ainstein-status Slack.

Gebruik (op de VM):
    cd ~/Ainstein
    python3 scripts/backfill_jamie_meetings.py

Veilig om meerdere keren te draaien — controleert op duplicaten via meeting_id.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent.parent
DECISIONS_LOG = BASE / "logs" / "decisions.jsonl"

# Echte meetings uit #ainstein-status, in chronologische volgorde.
# Tests en Q4-testpayloads (Sarah Johnson / Alex Chen) zijn weggelaten.
HISTORICAL_MEETINGS = [
    {
        "meeting_id": "backfill-20260617-135348",
        "meeting_title": "Lance, Jorgen & Guido Check In",
        "timestamp": "2026-06-17T13:53:48+00:00",
    },
    {
        "meeting_id": "backfill-20260617-144338",
        "meeting_title": "Interview Leiderschapsprogramma KS/IT",
        "timestamp": "2026-06-17T14:43:38+00:00",
    },
    {
        "meeting_id": "backfill-20260618-114619",
        "meeting_title": "Update Maud/Jörgen",
        "timestamp": "2026-06-18T11:46:19+00:00",
    },
    {
        "meeting_id": "backfill-20260618-123350",
        "meeting_title": "Debrief met Minkowski",
        "timestamp": "2026-06-18T12:33:50+00:00",
    },
    {
        "meeting_id": "backfill-20260618-134535",
        "meeting_title": "Update en bespreken intervisie calls",
        "timestamp": "2026-06-18T13:45:35+00:00",
    },
    {
        "meeting_id": "backfill-20260618-145431",
        "meeting_title": "Voorbereiding Programma Hei-dag Waardestromen",
        "timestamp": "2026-06-18T14:54:31+00:00",
    },
    {
        "meeting_id": "backfill-20260622-090833",
        "meeting_title": "Toelichting Minkowski- voorstel Senior Leadership bijeenkomst",
        "timestamp": "2026-06-22T09:08:33+00:00",
    },
    {
        "meeting_id": "backfill-20260622-092753",
        "meeting_title": "Interview Leiderschapsprogramma KS/IT",
        "timestamp": "2026-06-22T09:27:53+00:00",
    },
]


def load_existing_ids() -> set:
    """Laad alle bestaande meeting_ids uit decisions.jsonl."""
    ids = set()
    if not DECISIONS_LOG.exists():
        return ids
    with open(DECISIONS_LOG, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                mid = entry.get("meeting_id")
                if mid:
                    ids.add(mid)
            except json.JSONDecodeError:
                pass
    return ids


def backfill():
    DECISIONS_LOG.parent.mkdir(exist_ok=True)
    existing = load_existing_ids()
    added = 0
    skipped = 0

    with open(DECISIONS_LOG, "a", encoding="utf-8") as f:
        for m in HISTORICAL_MEETINGS:
            if m["meeting_id"] in existing:
                print(f"  SKIP (al aanwezig): {m['meeting_title']}")
                skipped += 1
                continue

            entry = {
                "timestamp": m["timestamp"],
                "skill": "meeting_reviewer",
                "meeting_id": m["meeting_id"],
                "meeting_title": m["meeting_title"],
                "iterations": 1,
                "answer_chars": 0,
                "total_duration_s": 0,
                "tools_called": [],
                "files_read": [],
                "backfilled": True,
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print(f"  TOEGEVOEGD: {m['meeting_title']} ({m['timestamp'][:10]})")
            added += 1

    print(f"\nKlaar: {added} toegevoegd, {skipped} overgeslagen.")
    print("Dashboard wordt automatisch bijgewerkt bij de volgende cron-run (elke 6u).")
    print("Of direct: python3 dashboard/generate.py")


if __name__ == "__main__":
    backfill()
