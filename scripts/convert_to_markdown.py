#!/usr/bin/env python3
"""
convert_to_markdown.py — Converteer bronbestanden naar plain-text Markdown cache.

Aslander IA-principe: plain text is de universele taal. Grote bronbestanden
(.docx, .pdf, .pptx, etc.) worden eenmalig geconverteerd naar geïndexeerde
.md-bestanden in _cached/ op Drive. Ainstein leest de cache — niet het
propriëtaire origineel. Schatting: 60-80% minder tokens per raadpleging.

Gebruik (op de VM):
    python3 scripts/convert_to_markdown.py
    python3 scripts/convert_to_markdown.py --folder 01_Proposals
    python3 scripts/convert_to_markdown.py --dry-run
    python3 scripts/convert_to_markdown.py --force --limit 5

Vereiste env vars (via .env):
    GOOGLE_SERVICE_ACCOUNT_FILE of GOOGLE_SERVICE_ACCOUNT_JSON
    AINSTEIN_DRIVE_ROOT_ID  (default: Minkowski AInstein Shared Drive)
"""

import argparse
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("convert_to_markdown")

from scrape_slack import _get_drive_service, _resolve_folder_chain, _upload_markdown
from tools import _read_drive_file_content, _drive_list_files_in_folder

SHARED_DRIVE_ID = os.environ.get("AINSTEIN_DRIVE_ROOT_ID", "0AFvBEDYKrnHbUk9PVA")
CACHE_ROOT = "_cached"

SOURCE_FOLDERS = ["01_Proposals", "02_Tools", "04_Experts"]

# Overslaan: al plain-text, of niet leesbaar (afbeeldingen, media, archieven)
SKIP_EXTENSIONS = {".md", ".txt", ".json", ".csv", ".rtf"}
UNSUPPORTED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".mp4", ".mp3", ".wav", ".mov",
    ".zip", ".tar", ".gz", ".7z",
    ".exe", ".dmg", ".pkg",
}


# ---------------------------------------------------------------------------
# Index-header
# ---------------------------------------------------------------------------

def _extract_sections(text: str) -> str:
    """Haal betekenisvolle ## headers op uit de tekst voor de index."""
    headers = re.findall(r"^##\s+(.+)$", text, re.MULTILINE)
    # Filter generieke parseerheaders (Page 1, Slide 3, Sheet: X)
    meaningful = [h for h in headers if not re.match(r"^(Page|Slide|Sheet:)\s+\d*", h)]
    if meaningful:
        return " · ".join(meaningful[:8])
    if headers:
        return f"{len(headers)} secties"
    return "volledig document"


def _build_header(title: str, source_path: str, text: str, today: str) -> str:
    secties = _extract_sections(text)
    return (
        f"# {title}\n"
        f"**Bron:** `{source_path}`\n"
        f"**Gecachet:** {today}\n"
        f"**Secties:** {secties}\n\n"
        f"---\n\n"
    )


# ---------------------------------------------------------------------------
# Drive helpers
# ---------------------------------------------------------------------------

def _find_source_folder_id(service, folder_name: str) -> str | None:
    """Zoek de ID van een top-level folder in de Shared Drive."""
    try:
        res = service.files().list(
            q=(
                f"'{SHARED_DRIVE_ID}' in parents and name='{folder_name}' "
                f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
            ),
            fields="files(id)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        files = res.get("files", [])
        return files[0]["id"] if files else None
    except Exception as e:
        log.error("Fout bij zoeken folder %s: %s", folder_name, e)
        return None


def _get_cached_modtime(service, cache_folder_id: str, stem: str) -> str | None:
    """Geef modifiedTime van gecachet bestand, of None als het niet bestaat."""
    md_name = f"{stem}.md"
    try:
        res = service.files().list(
            q=f"'{cache_folder_id}' in parents and name='{md_name}' and trashed=false",
            fields="files(modifiedTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        files = res.get("files", [])
        return files[0].get("modifiedTime") if files else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Conversie per folder
# ---------------------------------------------------------------------------

def convert_folder(
    service, folder_name: str, dry_run: bool, force: bool, limit: int | None
) -> tuple[int, int, int]:
    """Converteer één bron-folder. Retourneert (converted, skipped, errors)."""
    log.info("=== Folder: %s ===", folder_name)

    src_folder_id = _find_source_folder_id(service, folder_name)
    if not src_folder_id:
        log.warning("Folder niet gevonden in Drive: %s", folder_name)
        return 0, 0, 0

    files = _drive_list_files_in_folder(service, src_folder_id)
    log.info("  %d bestanden gevonden", len(files))

    if not dry_run:
        cache_folder_id = _resolve_folder_chain(service, SHARED_DRIVE_ID, CACHE_ROOT, folder_name)
    else:
        cache_folder_id = None

    converted = skipped = errors = 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for f in files:
        if limit is not None and converted >= limit:
            log.info("  Limiet van %d bereikt.", limit)
            break

        name = f["name"]
        file_id = f["id"]
        mime_type = f.get("mimeType", "")
        source_modified = f.get("modifiedTime", "")
        stem = Path(name).stem
        suffix = Path(name).suffix.lower()

        # Skip plain-text en niet-leesbare bestanden
        if suffix in SKIP_EXTENSIONS or mime_type in {
            "application/vnd.google-apps.folder",
            "application/vnd.google-apps.shortcut",
        }:
            skipped += 1
            continue
        if suffix in UNSUPPORTED_EXTENSIONS:
            log.debug("  Skip (niet ondersteund): %s", name)
            skipped += 1
            continue

        # Skip verborgen bestanden (.DS_Store, .gitkeep, etc.)
        if name.startswith("."):
            skipped += 1
            continue

        source_path = f"{folder_name}/{name}"

        # Freshness check — sla over als cache recenter is dan bron
        if not force and not dry_run:
            cached_modtime = _get_cached_modtime(service, cache_folder_id, stem)
            if cached_modtime and cached_modtime >= source_modified:
                log.info("  Actueel (skip): %s", name)
                skipped += 1
                continue

        if dry_run:
            log.info("  [DRY-RUN] %s → _cached/%s/%s.md", name, folder_name, stem)
            converted += 1
            continue

        # Lees en converteer
        log.info("  Converteer: %s", source_path)
        try:
            text = _read_drive_file_content(service, file_id, name, mime_type)
        except Exception as e:
            log.error("  Leesfout %s: %s", name, e)
            errors += 1
            continue

        if not text or (text.startswith("[") and ("failed" in text.lower() or "error" in text.lower())):
            log.warning("  Overgeslagen (leesfout): %s — %s", name, text[:100] if text else "leeg")
            errors += 1
            continue

        header = _build_header(stem, source_path, text, today)
        full_content = header + text

        try:
            url = _upload_markdown(service, stem, full_content, cache_folder_id)
            log.info("  Opgeslagen: %s → %s", name, url or "geen URL")
            converted += 1
        except Exception as e:
            log.error("  Upload mislukt %s: %s", name, e)
            errors += 1

    return converted, skipped, errors


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Converteer Drive-bronbestanden naar Markdown cache in _cached/."
    )
    parser.add_argument("--folder", help="Scan alleen deze folder (bijv. 01_Proposals)")
    parser.add_argument("--dry-run", action="store_true", help="Toon wat er zou gebeuren, schrijf niets")
    parser.add_argument("--force", action="store_true", help="Herschrijf ook al gecachede bestanden")
    parser.add_argument("--limit", type=int, default=None, help="Max N bestanden per folder (voor testing)")
    args = parser.parse_args()

    service = _get_drive_service()

    folders = [args.folder] if args.folder else SOURCE_FOLDERS

    if args.dry_run:
        log.info("DRY-RUN modus — er wordt niets geschreven naar Drive.")

    total_converted = total_skipped = total_errors = 0

    for folder_name in folders:
        c, s, e = convert_folder(service, folder_name, args.dry_run, args.force, args.limit)
        total_converted += c
        total_skipped += s
        total_errors += e

    log.info(
        "Klaar. Geconverteerd: %d | Overgeslagen: %d | Fouten: %d",
        total_converted, total_skipped, total_errors,
    )
    if args.dry_run:
        log.info("(DRY-RUN: niets geschreven naar Drive)")


if __name__ == "__main__":
    main()
