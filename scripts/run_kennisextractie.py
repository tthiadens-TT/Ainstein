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
DIS_START, DIS_END = "<<<DISTILLATIE_START>>>", "<<<DISTILLATIE_END>>>"


# ---------------------------------------------------------------------------
# Slack-notificatie (stdlib, geen slack_sdk-afhankelijkheid — patroon backup_drive)
# ---------------------------------------------------------------------------

def _slack_notify(message: str) -> None:
    if not SLACK_TOKEN:
        log.info("Geen SLACK_BOT_TOKEN — sla notificatie over.")
        return
    try:
        import ssl
        import urllib.request
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ctx = ssl.create_default_context()
        body = json.dumps({"channel": SLACK_CHANNEL, "text": message[:39000]}).encode()
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=body,
            headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10, context=ctx)
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

def _build_distil_prompt(bron: dict, today: str) -> str:
    """MAP-stap: distilleer één bron tot een compact facetten-blok."""
    return (
        "Distilleer deze ene databron volgens de extract_knowledge_distilleer skill.\n\n"
        f"Vandaag is {today}.\n\n"
        "Bron:\n"
        f"{json.dumps(bron, ensure_ascii=False, indent=2)}\n\n"
        f"Lever exact één fenced blok ({DIS_START}…{DIS_END}) zoals het "
        "Outputformaat voorschrijft. Niets eromheen."
    )


def _build_merge_prompt(distillaties: list[str], current_laag: str, today: str) -> str:
    """REDUCE-stap: kruis alle distillaties + merge in de laag. Geen bronnen lezen."""
    blokken = "\n\n".join(distillaties)
    return (
        "Kruis de onderstaande distillaties en werk de kennis-laag bij volgens de "
        "extract_knowledge_merge skill. Lees GEEN bronnen — alles zit in de distillaties.\n\n"
        f"Vandaag is {today}.\n\n"
        "Distillaties per bron:\n"
        f"{blokken}\n\n"
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
    parser = argparse.ArgumentParser(description="Bron-agnostische kennis-laag — map-reduce (distilleer per bron, kruis daarna)")
    parser.add_argument("--dry-run", action="store_true", help="Niet schrijven/posten — print de output")
    parser.add_argument("--bron", action="append", metavar="NAAM",
                        help="Beperk tot deze bron(nen) — herhaalbaar (voor testen)")
    parser.add_argument("--map-only", action="store_true",
                        help="Alleen de distilleer-stap draaien en printen; geen reduce/schrijven")
    parser.add_argument("--reduce-from", metavar="PAD",
                        help="Sla MAP over; laad distillaties uit dit JSON-bestand en draai alleen REDUCE "
                             "(goedkoop herhalen zonder alle bronnen opnieuw te lezen)")
    args = parser.parse_args()

    log.info("=== Kennisextractie gestart (map-reduce) ===")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.error("ANTHROPIC_API_KEY ontbreekt in .env — afgebroken.")
        return 1

    if not BRONNEN_FILE.exists():
        log.error("Bron-lijst niet gevonden: %s", BRONNEN_FILE)
        return 1
    bronnen = json.loads(BRONNEN_FILE.read_text(encoding="utf-8"))
    if args.bron:
        wanted = set(args.bron)
        bronnen = [b for b in bronnen if b["bron"] in wanted]
        if not bronnen:
            log.error("Geen bronnen matchen --bron %s", args.bron)
            return 1
    log.info("Bronnen: %s", [b["bron"] for b in bronnen])

    service = _get_drive_service()
    kennis_folder_id = _resolve_folder_chain(service, SHARED_DRIVE_ID, *KENNIS_PAD)
    log.info("Doelmap gereed: %s", "/".join(KENNIS_PAD))

    current_laag = _download_existing_laag(service, kennis_folder_id, f"{LAAG_NAAM}.md")
    had_promotiebesluiten = "## Promotiebesluiten" in current_laag
    log.info("Bestaande laag: %d tekens%s", len(current_laag), " (eerste run)" if not current_laag else "")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    import anthropic
    from agent import run_agent
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # --- MAP: distilleer elke bron los (kleine, begrensde context per bron) ---
    if args.reduce_from:
        distillaties = json.loads(Path(args.reduce_from).read_text(encoding="utf-8"))
        log.info("REDUCE-from: %d distillaties geladen uit %s — MAP overgeslagen",
                 len(distillaties), args.reduce_from)
    else:
        distillaties = []
        for i, bron in enumerate(bronnen, 1):
            log.info("[map %d/%d] distilleren: %s (oorsprong=%s)", i, len(bronnen), bron["bron"], bron["oorsprong"])
            try:
                resp, _ = run_agent(
                    [{"role": "user", "content": _build_distil_prompt(bron, today)}],
                    client,
                    skill="extract_knowledge_distilleer",
                    max_iterations=12,
                    max_tokens=8000,
                )
            except Exception as e:
                log.warning("[map %d/%d] bron %s mislukt: %s — overslaan", i, len(bronnen), bron["bron"], e)
                continue
            blok = _extract_block(resp, DIS_START, DIS_END)
            if not blok:
                log.warning("[map %d/%d] bron %s: geen distillatie-blok — overslaan", i, len(bronnen), bron["bron"])
                continue
            # Bewaar mét markers, zodat de reduce-stap de grenzen ziet
            distillaties.append(f"{DIS_START}\n{blok}\n{DIS_END}")
            log.info("[map %d/%d] ✓ %s (%d tekens distillatie)", i, len(bronnen), bron["bron"], len(blok))

        if not distillaties:
            log.error("Geen enkele distillatie geslaagd — afgebroken.")
            return 1
        # Bewaar distillaties zodat REDUCE goedkoop te herhalen is (zonder MAP).
        import tempfile
        dist_path = os.path.join(tempfile.gettempdir(), f"kennis_distillaties_{today}.json")
        try:
            Path(dist_path).write_text(json.dumps(distillaties, ensure_ascii=False), encoding="utf-8")
            log.info("Distillaties bewaard: %s (gebruik --reduce-from om REDUCE te herhalen)", dist_path)
        except Exception as e:
            log.warning("Kon distillaties niet bewaren: %s", e)
        log.info("MAP klaar: %d/%d bronnen gedistilleerd, %d tekens totaal",
                 len(distillaties), len(bronnen), sum(len(d) for d in distillaties))

    if args.map_only:
        print("\n" + "=" * 64 + "\nDISTILLATIES (map-only)\n" + "=" * 64)
        print("\n\n".join(distillaties))
        return 0

    # --- REDUCE: kruis distillaties + merge in de laag (kleine input, voltooit altijd) ---
    log.info("REDUCE: kruisen + mergen (skill=extract_knowledge_merge)...")
    response, _trace = run_agent(
        [{"role": "user", "content": _build_merge_prompt(distillaties, current_laag, today)}],
        client,
        skill="extract_knowledge_merge",
        max_iterations=8,
        max_tokens=32000,       # laag + samenvatting in één generatie; voorkomt afgekapte samenvatting
        request_timeout=900.0,  # merge schrijft de hele laag opnieuw → trage generatie
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
