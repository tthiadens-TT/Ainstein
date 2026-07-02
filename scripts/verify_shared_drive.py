#!/usr/bin/env python3
"""
Verifieer wat er ECHT in de Minkowski Shared Drive staat, via het serviceaccount.

WAAROM DIT SCRIPT BESTAAT
-------------------------
De MCP Drive-connector (die Claude Code sessies gebruiken) kan de inhoud van
sommige Shared Drive-submappen niet betrouwbaar tonen: hij geeft een lege lijst
terug zonder foutmelding. Daardoor is via de connector niet te onderscheiden of
een map echt leeg is, of dat de blokkade de inhoud verbergt.

Het serviceaccount (ainstein-bot, dat productie ook gebruikt) heeft die blokkade
niet en leest de Shared Drive wél volledig. Dit script gebruikt dat account om
de echte inhoud te tonen, zodat we grondwaarheid hebben vóór we op basis van de
inventarisatie van AInstein_OUD iets migreren of verwijderen.

WAT DIT SCRIPT DOET
-------------------
- Logt in met het serviceaccount (GOOGLE_SERVICE_ACCOUNT_FILE of _JSON).
- Loopt recursief door de Shared Drive (of door de map-IDs die je meegeeft).
- Print per map een boom met bestandsnaam, type en grootte, plus tellingen.

WAT DIT SCRIPT NIET DOET
------------------------
ALLEEN LEZEN. Geen create, geen copy, geen move, geen rename, geen delete.
De enige Drive-aanroep is files().list(). Er kan niets stukgaan.

GEBRUIK (op de VM)
------------------
    cd ~/Ainstein
    python3 scripts/verify_shared_drive.py                 # hele Shared Drive
    python3 scripts/verify_shared_drive.py <folderId> ...  # alleen deze mappen
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Zorg dat modules uit de repo-root (gdoc_tools.py) importeerbaar zijn, ook als
# het script als `python3 scripts/verify_shared_drive.py` wordt gedraaid.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

# Shared Drive "Minkowski AInstein"
SHARED_DRIVE_ID = os.environ.get("AINSTEIN_DRIVE_ROOT_ID", "0AFvBEDYKrnHbUk9PVA")

FOLDER_MIME = "application/vnd.google-apps.folder"


def _human_size(n: int) -> str:
    if n <= 0:
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.0f}TB"


def _get_drive_service():
    """Drive v3 client via het serviceaccount. Hergebruikt de projectlogin."""
    try:
        from gdoc_tools import _get_service_account_creds
    except Exception as e:  # pragma: no cover
        sys.exit(
            "Kon gdoc_tools niet importeren. Draai dit script vanuit ~/Ainstein "
            f"(cd ~/Ainstein). Fout: {e}"
        )
    creds = _get_service_account_creds()
    if creds is None:
        sys.exit(
            "Geen serviceaccount-credentials gevonden. Zet GOOGLE_SERVICE_ACCOUNT_FILE "
            "(of GOOGLE_SERVICE_ACCOUNT_JSON) in de omgeving. Op de VM staat die in .env."
        )
    from googleapiclient.discovery import build
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _list_children(svc, folder_id: str) -> list[dict]:
    """Alle directe kinderen van een map. ALLEEN LEZEN (files().list)."""
    items: list[dict] = []
    page_token = None
    while True:
        resp = svc.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            corpora="drive",
            driveId=SHARED_DRIVE_ID,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageSize=200,
            orderBy="folder,name",
            pageToken=page_token,
        ).execute()
        items.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return items


def _walk(svc, folder_id: str, label: str, depth: int, counts: dict) -> None:
    children = _list_children(svc, folder_id)
    folders = [c for c in children if c.get("mimeType") == FOLDER_MIME]
    files = [c for c in children if c.get("mimeType") != FOLDER_MIME]

    indent = "  " * depth
    print(f"{indent}[MAP] {label}  ({len(files)} bestanden, {len(folders)} submappen)")

    for f in files:
        counts["files"] += 1
        size = _human_size(int(f.get("size", 0) or 0))
        size_str = f"  {size}" if size else ""
        mime = f.get("mimeType", "").split(".")[-1]
        print(f"{indent}    - {f['name']}  [{mime}]{size_str}")

    for sub in folders:
        counts["folders"] += 1
        _walk(svc, sub["id"], sub["name"], depth + 1, counts)


def main() -> None:
    svc = _get_drive_service()
    targets = sys.argv[1:]

    print("=" * 70)
    print("VERIFICATIE SHARED DRIVE (read-only, via serviceaccount)")
    print("=" * 70)

    counts = {"files": 0, "folders": 0}

    if targets:
        for fid in targets:
            try:
                meta = svc.files().get(
                    fileId=fid, fields="id, name", supportsAllDrives=True
                ).execute()
                name = meta.get("name", fid)
            except Exception as e:
                print(f"[FOUT] kon map {fid} niet openen: {e}")
                continue
            _walk(svc, fid, name, 0, counts)
            print()
    else:
        _walk(svc, SHARED_DRIVE_ID, "Minkowski AInstein (root)", 0, counts)

    print("=" * 70)
    print(f"TOTAAL: {counts['files']} bestanden in {counts['folders']} submappen")
    print("=" * 70)


if __name__ == "__main__":
    main()
