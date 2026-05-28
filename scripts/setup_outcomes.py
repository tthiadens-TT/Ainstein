#!/usr/bin/env python3
"""
setup_outcomes.py — Maakt 08_Outcomes folder + template aan in de Shared Drive.

Gebruik:
    python3 scripts/setup_outcomes.py
"""

import os
import sys
from pathlib import Path

def _get_service():
    sa_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_file and not sa_json:
        print("ERROR: Geen service account gevonden. Zet GOOGLE_SERVICE_ACCOUNT_FILE.")
        sys.exit(1)
    import tempfile, json
    if sa_json and not sa_file:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp.write(sa_json); tmp.flush()
        sa_file = tmp.name
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_file(
        sa_file, scopes=["https://www.googleapis.com/auth/drive"]
    )
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    return drive

DRIVE_ROOT = os.environ.get("AINSTEIN_DRIVE_ROOT_ID", "0AFvBEDYKrnHbUk9PVA")
FOLDER_NAME = "08_Outcomes"

TEMPLATE_CONTENT = """# Outcomes — Template voor win/loss registratie

Kopieer dit bestand voor elk voorstel dat een beslissing heeft gekregen.
Bestandsnaam: JJJJMMDD_[Klant]_[Voorstel]_[WON|VERLOREN|NO_DECISION].md

---

## Voorstel
- **Klant:** [naam organisatie]
- **Voorstel:** [titel of korte beschrijving]
- **Datum voorstel:** [datum]
- **Datum beslissing:** [datum]

## Uitkomst
- **Outcome:** WON / VERLOREN / NO DECISION
- **Reden:** [1-3 zinnen — waarom hebben ze gekozen / niet gekozen?]

## Wat werkte
- [bullet]
- [bullet]

## Wat niet werkte
- [bullet]
- [bullet]

## Commercieel
- **Prijsindicatie Minkowski:** €
- **Budget klant (indien bekend):** €
- **Doorlooptijd:** [van] → [tot]
- **Concurrenten (indien bekend):** [namen]

## Lessen voor volgende keer
- [bullet]
- [bullet]

---
*Gelogd door: Thomas / Jörgen*
*Dit bestand wordt door Ainstein gelezen bij het bouwen van nieuwe proposals.*
"""

def main():
    drive = _get_service()

    # 1. Check of 08_Outcomes al bestaat
    res = drive.files().list(
        q=f"'{DRIVE_ROOT}' in parents and name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id,name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()

    if res.get("files"):
        folder_id = res["files"][0]["id"]
        print(f"✅ Folder '{FOLDER_NAME}' bestaat al (ID: {folder_id})")
    else:
        folder = drive.files().create(
            body={"name": FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder", "parents": [DRIVE_ROOT]},
            fields="id",
            supportsAllDrives=True,
        ).execute()
        folder_id = folder["id"]
        print(f"✅ Folder '{FOLDER_NAME}' aangemaakt (ID: {folder_id})")

    # 2. Maak template aan via Drive API (plain text upload → converteert naar Google Doc)
    import io
    from googleapiclient.http import MediaIoBaseUpload
    media = MediaIoBaseUpload(
        io.BytesIO(TEMPLATE_CONTENT.encode("utf-8")),
        mimetype="text/plain",
        resumable=False,
    )
    file_meta_body = {
        "name": "00_TEMPLATE — Outcome registratie",
        "mimeType": "application/vnd.google-apps.document",
        "parents": [folder_id],
    }
    created = drive.files().create(
        body=file_meta_body,
        media_body=media,
        fields="id",
        supportsAllDrives=True,
    ).execute()
    doc_id = created["id"]

    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    print(f"✅ Template aangemaakt: {url}")
    print()
    print("Klaar. 08_Outcomes is live in de Shared Drive.")
    print("Kopieer het template voor elk voorstel dat een beslissing krijgt.")

if __name__ == "__main__":
    main()
