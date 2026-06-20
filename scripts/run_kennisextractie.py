#!/usr/bin/env python3
"""
run_kennisextractie.py — Bron-agnostische kennis-laag: verrijken + bevestigen.

Bewijs-fase (handmatig draaien, mens kijkt mee). Leest de databronnen uit
`scripts/bronnen.json`, kruist ze (verrijken = alle bronnen; bevestigen = alleen
over onafhankelijke oorsprongen), en werkt de meegroeiende kennis-laag bij:
`06_Marketing/_kennis/kennis_laag.md` (plain-text .md).

Architectuur: dit SCRIPT bezit de laag-I/O (download → prompt → schrijf); de
agent doet alleen het redeneren. De bot-tools kunnen geen .md op een gekozen pad
mergen — daarom een script, net als scrape_slack.py / backup_drive.py.

Gebruik (op de VM):
    python3 scripts/run_kennisextractie.py [--dry-run]

Vereiste env vars (via .env):
    ANTHROPIC_API_KEY
    GOOGLE_SERVICE_ACCOUNT_FILE of GOOGLE_SERVICE_ACCOUNT_JSON
    AINSTEIN_DRIVE_ROOT_ID            (default: Minkowski AInstein)
    SLACK_BOT_TOKEN                   (optioneel — voor de samenvatting-notificatie)
    AINSTEIN_STATUS_CHANNEL / AINSTEIN_TRANSCRIPT_CHANNEL  (optioneel — doelkanaal)
"""

import argparse
import io
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Repo root op het pad zodat `agent` importeerbaar is; scripts/ staat al op
# sys.path[0] zodat `scrape_slack` direct importeerbaar is.
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
log = logging.getLogger("run_kennisextractie")

# Drive-helpers hergebruiken (scrape_slack.py:66-166)
from scrape_slack import _get_drive_service, _resolve_folder_chain, _upload_markdown

SHARED_DRIVE_ID = os.environ.get("AINSTEIN_DRIVE_ROOT_ID", "0AFvBEDYKrnHbUk9PVA")
BRONNEN_FILE = Path(__file__).resolve().parent / "bronnen.json"
LAAG_NAAM = "kennis_laag"  # _upload_markdown voegt .md toe
KENNIS_PAD = ("06_Marketing", "_kennis")

SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = (
    os.environ.get("AINSTEIN_STATUS_CHANNEL")
    or os.environ.get("AINSTEIN_TRANSCRIPT_CHANNEL", "C0B6B69Q812")
)

LAAG_START, LAAG_END = "<<<LAAG_START>>>", "<<<LAAG_END>>>"
SAM_START, SAM_END = "<<<SAMENVATTING_START>>>", "<<<SAMENVATTING_END>>>"


# ---------------------------------------------------------------------------
# Slack-notificatie (stdlib, geen slack_sdk-afhankelijkheid — patroon backup_drive)
# ---------------------------------------------------------------------------

def _slack_notify(message: str) -> None:
    if not SLACK_TOKEN:
        log.info("Geen SLACK_BOT_TOKEN — sla notificatie over.")
        return
    try:
        import urllib.request
        body = json.dumps({"channel": SLACK_CHANNEL, "text": message[:39000]}).encode()
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=body,
            headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log.warning("Slack-notificatie mislukt: %s", e)


# ---------------------------------------------------------------------------
# Laag-I/O
# ---------------------------------------------------------------------------

def _download_existing_laag(service, folder_id: str, filename: str) -> str:
    """Download de huidige kennis-laag (.md) via get_media. Lege string als hij nog niet bestaat."""
    from googleapiclient.http import MediaIoBaseDownload

    res = service.files().list(
        q=f"'{folder_id}' in parents and name='{filename}' and trashed=false",
        fields="files(id,name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    files = res.get("files", [])
    if not files:
        return ""

    try:
        request = service.files().get_media(fileId=files[0]["id"], supportsAllDrives=True)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buf.getvalue().decode("utf-8", errors="replace")
    except Exception as e:
        log.warning("Kon bestaande laag niet downloaden (%s) — start met lege laag.", e)
        return ""


def _extract_block(text: str, start: str, end: str) -> str:
    i = text.find(start)
    j = text.find(end)
    if i == -1 or j == -1 or j <= i:
        return ""
    return text[i + len(start):j].strip()


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

def _build_prompt(bronnen: list, current_laag: str, today: str) -> str:
    return (
        "Voer een kennisextractie uit volgens de extract_knowledge skill (laag-modus).\n\n"
        f"Vandaag is {today}.\n\n"
        "Bron-lijst (lees deze bronnen; weeg bevestiging per oorsprong, niet per bron):\n"
        f"{json.dumps(bronnen, ensure_ascii=False, indent=2)}\n\n"
        "Huidige kennis-laag:\n"
        f"<HUIDIGE_LAAG>\n{current_laag}\n</HUIDIGE_LAAG>\n\n"
        "Lever exact de twee fenced blokken "
        f"({LAAG_START}…{LAAG_END} en {SAM_START}…{SAM_END}) "
        "zoals het Outputformaat voorschrijft. Niets buiten de blokken dat erin hoort."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Bron-agnostische kennis-laag — verrijken + bevestigen")
    parser.add_argument("--dry-run", action="store_true", help="Niet schrijven/posten — print de output")
    args = parser.parse_args()

    log.info("=== Kennisextractie gestart ===")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.error("ANTHROPIC_API_KEY ontbreekt in .env — afgebroken.")
        return 1

    if not BRONNEN_FILE.exists():
        log.error("Bron-lijst niet gevonden: %s", BRONNEN_FILE)
        return 1
    bronnen = json.loads(BRONNEN_FILE.read_text(encoding="utf-8"))
    log.info("Bronnen geladen: %s", [b["bron"] for b in bronnen])

    service = _get_drive_service()
    kennis_folder_id = _resolve_folder_chain(service, SHARED_DRIVE_ID, *KENNIS_PAD)
    log.info("Doelmap gereed: %s", "/".join(KENNIS_PAD))

    current_laag = _download_existing_laag(service, kennis_folder_id, f"{LAAG_NAAM}.md")
    had_promotiebesluiten = "## Promotiebesluiten" in current_laag
    log.info("Bestaande laag: %d tekens%s", len(current_laag), " (eerste run)" if not current_laag else "")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt = _build_prompt(bronnen, current_laag, today)

    import anthropic
    from agent import run_agent
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    log.info("Agent draait (skill=extract_knowledge)...")
    response, _trace = run_agent(
        [{"role": "user", "content": prompt}],
        client,
        skill="extract_knowledge",
        max_iterations=25,
        max_tokens=16000,
    )

    nieuwe_laag = _extract_block(response, LAAG_START, LAAG_END)
    samenvatting = _extract_block(response, SAM_START, SAM_END) or "(geen samenvatting in output)"

    # Sanity-check (bewijs-fase: mens kijkt mee, dus één check i.p.v. de volledige firewall)
    fout = None
    if not nieuwe_laag:
        fout = "geen/lege LAAG-blok in de output"
    elif had_promotiebesluiten and "## Promotiebesluiten" not in nieuwe_laag:
        fout = "Promotiebesluiten-sectie verdween uit de nieuwe laag"

    if args.dry_run:
        print("\n===== SAMENVATTING =====\n" + samenvatting)
        print("\n===== NIEUWE LAAG =====\n" + (nieuwe_laag or "(leeg)"))
        if fout:
            print(f"\n[!] sanity-check zou falen: {fout}")
        return 0

    if fout:
        log.error("Sanity-check gefaald: %s — laag NIET overschreven.", fout)
        _slack_notify(
            f":warning: *Kennisextractie — niet weggeschreven* ({today})\n"
            f"Sanity-check faalde: {fout}. Concept ter controle:\n\n{samenvatting[:3000]}"
        )
        return 1

    link = _upload_markdown(service, LAAG_NAAM, nieuwe_laag, kennis_folder_id)
    log.info("Kennis-laag bijgewerkt: %s", link)

    # Print de samenvatting naar stdout zodat wie het script draait de gaten
    # direct ziet — connector-onafhankelijk, geen Slack/Drive-toegang nodig.
    print("\n" + "=" * 64)
    print("SAMENVATTING — verkondigd vs verkocht")
    print("=" * 64)
    print(samenvatting)
    print("=" * 64)
    print(f"Volledige kennis-laag: {link}\n")

    _slack_notify(
        f":white_check_mark: *Kennis-laag bijgewerkt* ({today})\n{link}\n\n{samenvatting}"
    )

    log.info("=== Kennisextractie afgerond ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
