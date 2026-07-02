#!/usr/bin/env python3
"""
restore_voice.py — Herstel skills/minkowski_voice.md vanuit Drive na een deploy.

deploy.yml doet git reset --hard origin/main, wat de verrijkte voice overschrijft
met de GitHub-baseline. Dit script haalt de meest recente versie op uit Drive
(04_Marketing/_kennis/minkowski_voice.md) zodat de verrijking niet verloren gaat.

Gebruik: python3 scripts/restore_voice.py
Aangeroepen vanuit deploy.yml, direct na git reset --hard.
Faalt nooit hard — bij Drive-fout blijft de GitHub-baseline gewoon staan.
"""

import logging
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger("restore_voice")

SHARED_DRIVE_ID = os.environ.get("AINSTEIN_DRIVE_ROOT_ID", "0AFvBEDYKrnHbUk9PVA")
VOICE_DRIVE_PAD = ("_kennis",)  # onder marketing-rolmap (drive_structure)
VOICE_DRIVE_NAAM = "minkowski_voice.md"
VOICE_LOCAL = _REPO_ROOT / "skills" / "minkowski_voice.md"


def main() -> int:
    try:
        from scrape_slack import _get_drive_service
        import drive_structure as ds
        import io
        from googleapiclient.http import MediaIoBaseDownload

        service = _get_drive_service()
        folder_id = ds.resolve_path(service, "marketing", VOICE_DRIVE_PAD)

        res = service.files().list(
            q=f"'{folder_id}' in parents and name='{VOICE_DRIVE_NAAM}' and trashed=false",
            fields="files(id,name,modifiedTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        bestanden = res.get("files", [])

        if not bestanden:
            log.info("Geen Drive-versie gevonden — GitHub-baseline blijft staan.")
            return 0

        fid = bestanden[0]["id"]
        modified = bestanden[0].get("modifiedTime", "onbekend")

        req = service.files().get_media(fileId=fid, supportsAllDrives=True)
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()

        inhoud = buf.getvalue().decode("utf-8", errors="replace")
        if len(inhoud) < 500:
            log.warning("Drive-versie verdacht kort (%d tekens) — GitHub-baseline blijft staan.", len(inhoud))
            return 0

        VOICE_LOCAL.write_text(inhoud, encoding="utf-8")
        log.info("Voice hersteld vanuit Drive (bijgewerkt: %s, %d tekens).", modified, len(inhoud))
        return 0

    except Exception as e:
        log.warning("Voice restore mislukt (%s) — GitHub-baseline blijft staan.", e)
        return 0


if __name__ == "__main__":
    sys.exit(main())
