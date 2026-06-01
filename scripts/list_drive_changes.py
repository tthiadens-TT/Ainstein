#!/usr/bin/env python3
"""
list_drive_changes.py — Toont bestanden die recent zijn toegevoegd of gewijzigd
in de Minkowski Shared Drive.

Gebruik (vanuit /home/thomas/Ainstein):
    .venv/bin/python3 scripts/list_drive_changes.py [--hours N]

Output: JSON met per bestand: naam, map, aanmaakdatum, wijzigingsdatum, eigenaar.
Default venster: 26 uur (iets meer dan 24u om randgevallen bij de daggrens op te vangen).
"""

import argparse
import json
import os
import sys


def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            if key.strip() not in os.environ:
                os.environ[key.strip()] = val.strip().strip('"').strip("'")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=26,
                        help="Tijdvenster in uren (default: 26)")
    args = parser.parse_args()

    _load_env()

    # tools.py verwacht env vars — laad ze hierboven vóór de import
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    try:
        import tools
    except ImportError as e:
        print(json.dumps({"error": f"Kan tools.py niet laden: {e}"}))
        sys.exit(1)

    result = tools.list_recent_files(hours=args.hours)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
