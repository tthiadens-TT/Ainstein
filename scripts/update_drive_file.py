#!/usr/bin/env python3
"""
update_drive_file.py — Werk een bestaand Drive-bestand bij op basis van file ID of naam+map.

Gebruik:
    # Op basis van file ID (meest direct):
    python3 scripts/update_drive_file.py --file-id <ID> --local-path <pad>

    # Op basis van naam + map (maakt aan als het niet bestaat):
    python3 scripts/update_drive_file.py --folder-id <MAP-ID> --filename <naam.md> --local-path <pad>

    # Via stdin:
    cat bestand.md | python3 scripts/update_drive_file.py --file-id <ID>

Waarom dit script bestaat: de MCP Drive-connector heeft geen update-endpoint — alleen create.
Dit script gebruikt de service account (supportsAllDrives=True) en werkt voor zowel
persoonlijke Drive als Shared Drive.
"""

import argparse
import io
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
log = logging.getLogger("update_drive_file")

from scripts.scrape_slack import _get_drive_service, _upload_markdown


def update_by_file_id(service, file_id: str, content: str) -> str:
    from googleapiclient.http import MediaIoBaseUpload
    media = MediaIoBaseUpload(
        io.BytesIO(content.encode("utf-8")), mimetype="text/plain", resumable=False
    )
    doc = service.files().update(
        fileId=file_id,
        media_body=media,
        fields="id,webViewLink",
        supportsAllDrives=True,
    ).execute()
    log.info("Bijgewerkt (file ID: %s)", file_id)
    return doc.get("webViewLink", "")


def main():
    parser = argparse.ArgumentParser(description="Update een Drive-bestand via service account.")
    parser.add_argument("--file-id", help="ID van het bestaande Drive-bestand")
    parser.add_argument("--folder-id", help="ID van de map (gebruikt met --filename)")
    parser.add_argument("--filename", help="Bestandsnaam in de map (gebruikt met --folder-id)")
    parser.add_argument("--local-path", help="Pad naar lokaal bestand (lees stdin als weggelaten)")
    args = parser.parse_args()

    if not args.file_id and not (args.folder_id and args.filename):
        parser.error("Geef --file-id OF --folder-id + --filename op.")

    if args.local_path:
        content = Path(args.local_path).read_text(encoding="utf-8")
    else:
        content = sys.stdin.read()

    if not content.strip():
        log.error("Lege inhoud — niets bijgewerkt.")
        sys.exit(1)

    service = _get_drive_service()

    if args.file_id:
        url = update_by_file_id(service, args.file_id, content)
    else:
        url = _upload_markdown(service, args.filename, content, args.folder_id)

    if url:
        print(url)


if __name__ == "__main__":
    main()
