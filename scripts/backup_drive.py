#!/usr/bin/env python3
"""
backup_drive.py — Wekelijkse backup van de Minkowski AInstein bronnenlaag.

Wat het doet:
- Kopieert alle bestanden uit folders 01–07 naar een EXTERNE Shared Drive (Minkowski AInstein_Backup)
- Backup staat bewust BUITEN de bronnenlaag — aparte Shared Drive als tweede locatie
- Gebruikt de service account (geen OAuth nodig)
- Bewaart de laatste 4 wekelijkse snapshots, verwijdert oudere
- Logt naar stdout (geschikt voor cron + journald)

Gebruik:
    python3 scripts/backup_drive.py

Cron (wekelijks, zondag 03:00):
    0 3 * * 0 /home/thomas/Ainstein/scripts/run_backup.sh

Vereiste env var:
    AINSTEIN_BACKUP_DEST_ID  — Drive ID van de externe backup Shared Drive (Minkowski AInstein_Backup)
    AINSTEIN_DRIVE_ROOT_ID   — Drive ID van de bronnenlaag (Minkowski AInstein)
"""

import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = os.environ.get("AINSTEIN_TRANSCRIPT_CHANNEL", "C0B6B69Q812")


def _slack_notify(message: str) -> None:
    if not SLACK_TOKEN:
        return
    try:
        import urllib.request, json as _json
        body = _json.dumps({"channel": SLACK_CHANNEL, "text": message}).encode()
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=body,
            headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log.warning("Slack-notificatie mislukt: %s", e)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("backup_drive")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SHARED_DRIVE_ID = os.environ.get("AINSTEIN_DRIVE_ROOT_ID", "0AFvBEDYKrnHbUk9PVA")
BACKUP_DEST_ID = os.environ.get("AINSTEIN_BACKUP_DEST_ID", "")  # externe Shared Drive
SOURCE_FOLDER_PREFIXES = ("01_", "02_", "03_", "04_", "05_", "06_", "07_")
KEEP_SNAPSHOTS = 4  # bewaar de laatste N wekelijkse snapshots


def _get_service():
    """Bouw een Drive API service via service account."""
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    sa_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")

    _tmp_path = None
    if sa_json:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp.write(sa_json)
            _tmp_path = tmp.name
        sa_file = _tmp_path

    if not sa_file or not Path(sa_file).exists():
        log.error("Geen service account gevonden. Zet GOOGLE_SERVICE_ACCOUNT_FILE of GOOGLE_SERVICE_ACCOUNT_JSON.")
        sys.exit(1)

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_file(
            sa_file,
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    finally:
        if _tmp_path:
            os.unlink(_tmp_path)


def _list_top_folders(service):
    """Haal alle mappen op in de root van de Shared Drive."""
    res = service.files().list(
        q=f"'{SHARED_DRIVE_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        driveId=SHARED_DRIVE_ID,
        corpora="drive",
    ).execute()
    return {f["name"]: f["id"] for f in res.get("files", [])}


def _get_or_create_folder(service, name, parent_id):
    """Zoek een map op naam onder parent_id, maak hem aan als hij niet bestaat."""
    res = service.files().list(
        q=f"'{parent_id}' in parents and name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]

    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    created = service.files().create(
        body=meta,
        fields="id",
        supportsAllDrives=True,
    ).execute()
    log.info("Map aangemaakt: %s", name)
    return created["id"]


def _list_files_in_folder(service, folder_id):
    """Lijst alle bestanden (geen submappen) in een folder."""
    all_files = []
    page_token = None
    while True:
        kwargs = dict(
            q=f"'{folder_id}' in parents and mimeType!='application/vnd.google-apps.folder' and trashed=false",
            fields="nextPageToken, files(id, name, mimeType)",
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        if page_token:
            kwargs["pageToken"] = page_token
        res = service.files().list(**kwargs).execute()
        all_files.extend(res.get("files", []))
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return all_files


def _copy_file(service, file_id, file_name, dest_folder_id):
    """Kopieer een bestand naar dest_folder_id."""
    try:
        service.files().copy(
            fileId=file_id,
            body={"name": file_name, "parents": [dest_folder_id]},
            supportsAllDrives=True,
            fields="id",
        ).execute()
        return True
    except Exception as e:
        log.warning("Kopie mislukt voor %s: %s", file_name, e)
        return False


def _cleanup_old_snapshots(service, backup_root_id, keep=KEEP_SNAPSHOTS):
    """Verwijder snapshots ouder dan de laatste `keep` weken."""
    res = service.files().list(
        q=f"'{backup_root_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name, createdTime)",
        orderBy="createdTime",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    snapshots = sorted(res.get("files", []), key=lambda x: x.get("createdTime", ""))

    to_delete = snapshots[:-keep] if len(snapshots) > keep else []
    for snap in to_delete:
        try:
            service.files().delete(fileId=snap["id"], supportsAllDrives=True).execute()
            log.info("Oud snapshot verwijderd: %s", snap["name"])
        except Exception as e:
            log.warning("Kon snapshot %s niet verwijderen: %s", snap["name"], e)


def main():
    log.info("=== Ainstein Drive Backup gestart ===")

    if not BACKUP_DEST_ID:
        log.error("AINSTEIN_BACKUP_DEST_ID is niet gezet in .env — backup afgebroken.")
        log.error("Voeg toe: AINSTEIN_BACKUP_DEST_ID=<ID van Minkowski AInstein_Backup drive>")
        return 1

    service = _get_service()

    # Stap 1: haal alle top-level mappen op uit de bronnenlaag
    top_folders = _list_top_folders(service)
    log.info("Bronnenlaag mappen gevonden: %s", list(top_folders.keys()))

    # Stap 2: schrijf naar de EXTERNE backup Shared Drive (niet de bronnenlaag zelf)
    backup_root_id = BACKUP_DEST_ID
    log.info("Backup bestemming: externe Shared Drive (ID: %s)", backup_root_id)

    # Stap 3: maak een snapshot-map aan met de huidige datum
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snapshot_id = _get_or_create_folder(service, date_str, backup_root_id)
    log.info("Snapshot map: %s (ID: %s)", date_str, snapshot_id)

    # Stap 4: kopieer alle bestanden uit 01–07
    total_ok = 0
    total_fail = 0

    for folder_name, folder_id in top_folders.items():
        if not any(folder_name.startswith(p) for p in SOURCE_FOLDER_PREFIXES):
            continue

        log.info("Backup: %s ...", folder_name)
        dest_subfolder_id = _get_or_create_folder(service, folder_name, snapshot_id)
        files = _list_files_in_folder(service, folder_id)

        for f in files:
            ok = _copy_file(service, f["id"], f["name"], dest_subfolder_id)
            if ok:
                total_ok += 1
            else:
                total_fail += 1

    log.info("Backup klaar: %d bestanden gekopieerd, %d mislukt", total_ok, total_fail)

    # Stap 5: verwijder oude snapshots
    _cleanup_old_snapshots(service, backup_root_id)

    # Stap 6: Slack-notificatie
    if total_fail == 0:
        _slack_notify(f":white_check_mark: *Drive backup geslaagd* — {date_str}\n{total_ok} bestanden gekopieerd naar backup drive.")
    else:
        _slack_notify(f":warning: *Drive backup gedeeltelijk mislukt* — {date_str}\n{total_ok} gekopieerd, *{total_fail} mislukt*. Check `logs/backup.log` op de VM.")

    log.info("=== Ainstein Drive Backup afgerond ===")
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
