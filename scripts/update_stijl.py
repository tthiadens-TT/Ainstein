#!/usr/bin/env python3
"""
update_stijl.py — Schrijfstijl levend houden: haal nieuwe patronen op uit bronmateriaal,
verrijk skills/minkowski_voice.md, sla op in Drive, herstart service.

Architectuur:
- Leest bronmateriaal (LinkedIn, Substack, website) uit Drive via service account
- Laat een agent nieuwe stijlpatronen extraheren (skill=extract_style_patterns)
- Schrijft de bijgewerkte minkowski_voice.md lokaal weg
- Slaat de verrijkte voice op als 06_Marketing/_kennis/minkowski_voice.md in Drive
  (zodat restore_voice.py de verrijking kan herstellen na een git reset --hard)
- Schrijft de bijgewerkte verbal_identity.md terug naar Drive (sectie 4+5)
- Herstart ainstein.service zodat de nieuwe stem direct actief is
- Geen git-operaties — deploy.yml regelt git, cron regelt de verrijking

Gebruik (op de VM, wekelijks via cron):
    python3 scripts/update_stijl.py [--dry-run] [--no-push]

Vereiste env vars (via .env):
    ANTHROPIC_API_KEY
    GOOGLE_SERVICE_ACCOUNT_FILE of GOOGLE_SERVICE_ACCOUNT_JSON
    AINSTEIN_DRIVE_ROOT_ID  (default: Minkowski AInstein Shared Drive)
    SLACK_BOT_TOKEN         (optioneel — voor de samenvatting-notificatie)
"""

import argparse
import io
import json
import logging
import os
import subprocess
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
log = logging.getLogger("update_stijl")

from scrape_slack import _get_drive_service, _resolve_folder_chain, _upload_markdown

SHARED_DRIVE_ID = os.environ.get("AINSTEIN_DRIVE_ROOT_ID", "0AFvBEDYKrnHbUk9PVA")
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = (
    os.environ.get("AINSTEIN_STATUS_CHANNEL")
    or os.environ.get("AINSTEIN_TRANSCRIPT_CHANNEL", "C0B6B69Q812")
)

STEM_START, STEM_END = "<<<STEM_START>>>", "<<<STEM_END>>>"

# Bronnen die het rijkst zijn voor stijlpatronen (eigen stem, geen feiten-bronnen)
STIJL_BRONNEN = {"linkedin-jorgen", "linkedin-minkowski", "substack", "website-minkowski"}

VOICE_FILE = _REPO_ROOT / "skills" / "minkowski_voice.md"
VERBAL_IDENTITY_PAD = ("06_Marketing",)
VERBAL_IDENTITY_NAAM = "verbal_identity"
VOICE_KENNIS_PAD = ("06_Marketing", "_kennis")
VOICE_KENNIS_NAAM = "minkowski_voice"

# Max tekens bronmateriaal per bron — stijl heeft geen volledigheid nodig, wel variatie
MAX_CHARS_PER_BRON = 30_000


# ---------------------------------------------------------------------------
# Drive helpers
# ---------------------------------------------------------------------------

def _list_files_in_folder(service, folder_id: str) -> list[dict]:
    result = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageToken=page_token,
        ).execute()
        result.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return result


def _download_file(service, file_id: str) -> str:
    from googleapiclient.http import MediaIoBaseDownload
    try:
        req = service.files().get_media(fileId=file_id, supportsAllDrives=True)
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        return buf.getvalue().decode("utf-8", errors="replace")
    except Exception as e:
        log.warning("Kon bestand niet downloaden (%s): %s", file_id, e)
        return ""


def _resolve_bron_folder(service, locatie: str) -> str | None:
    """Los 'pad/naar/map' op naar een folder-ID via BFS."""
    parts = [p for p in locatie.strip("/").split("/") if p]
    try:
        return _resolve_folder_chain(service, SHARED_DRIVE_ID, *parts)
    except Exception as e:
        log.warning("Map niet gevonden '%s': %s", locatie, e)
        return None


def _lees_bron(service, bron: dict) -> str:
    """Lees alle bestanden in een Drive-map samen tot MAX_CHARS_PER_BRON tekens."""
    folder_id = _resolve_bron_folder(service, bron["locatie"])
    if not folder_id:
        return ""
    bestanden = _list_files_in_folder(service, folder_id)
    tekst_delen = []
    totaal = 0
    for f in bestanden:
        if totaal >= MAX_CHARS_PER_BRON:
            break
        inhoud = _download_file(service, f["id"])
        if not inhoud.strip():
            continue
        rest = MAX_CHARS_PER_BRON - totaal
        tekst_delen.append(f"## {f['name']}\n\n{inhoud[:rest]}")
        totaal += min(len(inhoud), rest)
    if not tekst_delen:
        log.info("Bron '%s': geen bestanden of leeg — overgeslagen", bron["bron"])
    return "\n\n---\n\n".join(tekst_delen)


def _download_verbal_identity(service) -> tuple[str, str | None]:
    """Download verbal_identity.md uit 06_Marketing. Geeft (inhoud, file_id)."""
    try:
        folder_id = _resolve_folder_chain(service, SHARED_DRIVE_ID, *VERBAL_IDENTITY_PAD)
        res = service.files().list(
            q=f"'{folder_id}' in parents and name='verbal_identity.md' and trashed=false",
            fields="files(id,name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        bestanden = res.get("files", [])
        if not bestanden:
            return "", None
        fid = bestanden[0]["id"]
        return _download_file(service, fid), fid
    except Exception as e:
        log.warning("Kon verbal_identity.md niet downloaden: %s", e)
        return "", None


# ---------------------------------------------------------------------------
# Drive: voice opslaan als dedicated bestand in _kennis/
# ---------------------------------------------------------------------------

def _save_voice_to_drive_kennis(service, inhoud: str) -> None:
    """Sla minkowski_voice.md op als dedicated bestand in 06_Marketing/_kennis/
    zodat restore_voice.py de verrijking kan herstellen na een git reset --hard."""
    try:
        folder_id = _resolve_folder_chain(service, SHARED_DRIVE_ID, *VOICE_KENNIS_PAD)
        _upload_markdown(service, VOICE_KENNIS_NAAM, inhoud, folder_id)
        log.info("minkowski_voice.md opgeslagen in Drive (_kennis/).")
    except Exception as e:
        log.warning("Kon minkowski_voice.md niet opslaan in Drive: %s", e)


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------

def _slack_notify(message: str) -> None:
    if not SLACK_TOKEN:
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
# Service restart
# ---------------------------------------------------------------------------

def _restart_ainstein() -> None:
    """Herstart ainstein.service zodat de nieuwe voice direct actief is."""
    try:
        subprocess.run(
            ["sudo", "systemctl", "restart", "ainstein"],
            check=True, capture_output=True,
        )
        log.info("ainstein.service herstart — nieuwe voice actief.")
    except subprocess.CalledProcessError as e:
        log.warning("Service restart mislukt (niet op VM?): %s", e.stderr.decode() if e.stderr else e)


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

def _build_prompt(bronnen_tekst: str, huidige_stem: str, today: str) -> str:
    return (
        "Verrijk de Minkowski schrijfstijl op basis van het bronmateriaal hieronder. "
        "Volg de extract_style_patterns skill.\n\n"
        f"Vandaag is {today}.\n\n"
        f"<HUIDIGE_STEM>\n{huidige_stem}\n</HUIDIGE_STEM>\n\n"
        f"<BRONNEN>\n{bronnen_tekst}\n</BRONNEN>\n\n"
        f"Lever precies één blok ({STEM_START}…{STEM_END}) met de volledige bijgewerkte inhoud. "
        "Niets erbuiten."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Schrijfstijl levend houden via bronmateriaal-extractie")
    parser.add_argument("--dry-run", action="store_true", help="Niet schrijven, niet opslaan — print output")
    parser.add_argument("--no-push", action="store_true", help="Verouderd — behouden voor backwards-compatibiliteit, heeft geen effect meer")
    args = parser.parse_args()

    log.info("=== Stijl-update gestart ===")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.error("ANTHROPIC_API_KEY ontbreekt — afgebroken.")
        return 1

    bronnen_file = Path(__file__).resolve().parent / "bronnen.json"
    if not bronnen_file.exists():
        log.error("bronnen.json niet gevonden.")
        return 1
    alle_bronnen = json.loads(bronnen_file.read_text(encoding="utf-8"))
    stijl_bronnen = [b for b in alle_bronnen if b["bron"] in STIJL_BRONNEN]
    log.info("Stijlbronnen: %s", [b["bron"] for b in stijl_bronnen])

    service = _get_drive_service()

    # Bronmateriaal ophalen
    bron_secties = []
    for bron in stijl_bronnen:
        log.info("Lezen: %s", bron["bron"])
        tekst = _lees_bron(service, bron)
        if tekst:
            bron_secties.append(f"# Bron: {bron['bron']} (oorsprong: {bron['oorsprong']})\n\n{tekst}")
            log.info("  %d tekens geladen", len(tekst))
        else:
            log.warning("  Bron %s leeg of niet bereikbaar — overgeslagen", bron["bron"])

    if not bron_secties:
        log.error("Geen bronmateriaal beschikbaar — afgebroken.")
        return 1

    bronnen_tekst = "\n\n" + ("=" * 60 + "\n\n").join(bron_secties)
    log.info("Totaal bronmateriaal: %d tekens", len(bronnen_tekst))

    # Huidige stem laden
    if not VOICE_FILE.exists():
        log.error("skills/minkowski_voice.md niet gevonden: %s", VOICE_FILE)
        return 1
    huidige_stem = VOICE_FILE.read_text(encoding="utf-8")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    import anthropic
    from agent import run_agent
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    log.info("Agent aan het werk (skill=extract_style_patterns)...")
    response, _ = run_agent(
        [{"role": "user", "content": _build_prompt(bronnen_tekst, huidige_stem, today)}],
        client,
        skill="extract_style_patterns",
        max_iterations=8,
        max_tokens=16000,
        request_timeout=300.0,
    )

    # Blok extraheren
    i = response.find(STEM_START)
    j = response.find(STEM_END)
    if i == -1 or j == -1 or j <= i:
        log.error("Geen %s…%s blok in de output — afgebroken.", STEM_START, STEM_END)
        if args.dry_run:
            print(response)
        return 1

    nieuwe_stem = response[i + len(STEM_START):j].strip()

    # Minimale sanity-check
    if len(nieuwe_stem) < len(huidige_stem) * 0.7:
        log.error(
            "Nieuwe stem is >30%% korter dan de huidige (%d vs %d tekens) — "
            "waarschijnlijk onvolledig. Afgebroken.",
            len(nieuwe_stem), len(huidige_stem),
        )
        return 1

    if args.dry_run:
        print("\n" + "=" * 64)
        print("NIEUWE MINKOWSKI VOICE (dry-run, niet weggeschreven)")
        print("=" * 64)
        print(nieuwe_stem)
        return 0

    # Schrijf lokaal
    VOICE_FILE.write_text(nieuwe_stem, encoding="utf-8")
    log.info("skills/minkowski_voice.md bijgewerkt (%d → %d tekens)", len(huidige_stem), len(nieuwe_stem))

    # Sla op in Drive als persistent backup (zodat restore_voice.py na deploy kan herstellen)
    _save_voice_to_drive_kennis(service, nieuwe_stem)

    # Update verbal_identity.md in Drive (secties 4+5 worden vervangen)
    _update_verbal_identity_in_drive(service, nieuwe_stem, today)

    # Herstart service zodat nieuwe voice direct actief is
    _restart_ainstein()

    _slack_notify(
        f":paintbrush: *Schrijfstijl bijgewerkt* ({today})\n"
        f"Minkowski Voice verrijkt op basis van {len(stijl_bronnen)} bronnen. "
        f"Ainstein draait met vernieuwde stem."
    )

    log.info("=== Stijl-update afgerond ===")
    # Schrijf uitvoertijdstempel voor het dashboard
    try:
        from datetime import datetime as _dt, timezone as _tz
        (_REPO_ROOT / "logs" / "cron_stijl.txt").write_text(_dt.now(_tz.utc).isoformat())
    except Exception:
        pass
    return 0


def _update_verbal_identity_in_drive(service, nieuwe_stem: str, today: str) -> None:
    """Update de schrijfpatronen-secties (4+5) in verbal_identity.md op Drive."""
    inhoud, fid = _download_verbal_identity(service)
    if not inhoud:
        log.warning("verbal_identity.md niet gevonden of leeg — Drive-update overgeslagen.")
        return

    # Vervang secties 4 en 5 met de distillatie uit de nieuwe stem
    # We zoeken sectie 4 tot het einde van sectie 5, en vervangen
    markering_start = "## 4. Schrijfpatronen"
    markering_einde = "## 6."  # sectie 6 blijft intact
    i = inhoud.find(markering_start)
    j = inhoud.find(markering_einde)

    extractie = (
        f"## 4. Schrijfpatronen — automatisch verrijkt\n\n"
        f"*Laatste update: {today}. Gegenereerd door update_stijl.py op basis van recente bronnen.*\n\n"
        f"Zie `skills/minkowski_voice.md` voor de volledige, actuele stem die Ainstein gebruikt.\n\n"
        f"---\n\n"
    )

    if i != -1 and j != -1 and j > i:
        nieuwe_inhoud = inhoud[:i] + extractie + inhoud[j:]
    else:
        # Secties niet gevonden — voeg toe aan het einde
        nieuwe_inhoud = inhoud + f"\n\n{extractie}"

    try:
        folder_id = _resolve_folder_chain(service, SHARED_DRIVE_ID, *VERBAL_IDENTITY_PAD)
        _upload_markdown(service, VERBAL_IDENTITY_NAAM, nieuwe_inhoud, folder_id)
        log.info("verbal_identity.md bijgewerkt in Drive.")
    except Exception as e:
        log.warning("Kon verbal_identity.md niet bijwerken in Drive: %s", e)


if __name__ == "__main__":
    sys.exit(main())
