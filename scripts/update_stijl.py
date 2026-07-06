#!/usr/bin/env python3
"""
update_stijl.py — PATTERNS-laag levend houden: haal nieuwe patronen op uit bronmateriaal,
verrijk de PATTERNS-zone in skills/minkowski_voice.md, sla op in Drive, herstart service.

CORE/PATTERNS-scheiding (sinds 2026-07-06):
- CORE (taalregel, verboden woorden, em dash-verbod, schrijfregels, taglines) leeft
  uitsluitend in verbal_identity.md (Drive, mens-onderhouden). Dit script raakt CORE
  nooit aan — geen download, geen LLM-prompt, geen schrijfactie.
- PATTERNS (vier schrijfpatronen, vocabulaire, citaten) leeft in skills/minkowski_voice.md,
  binnen sentinel-markers (<!-- PATTERNS:START/END -->). Dit is het enige dat dit script
  leest, naar de LLM stuurt, en terugschrijft.
- Beide bestanden gebruiken dezelfde sentinel-markers voor hun PATTERNS-stub, zodat
  bijwerken nooit meer op koptekst-tekst hoeft te matchen (de oorzaak van de oude
  duplicatie-bug: een hardcoded "## 6."-marker die niet bestond, viel terug op
  stilzwijgend appenden). Ontbreken de sentinels: het script faalt hard, nooit stil.

Architectuur:
- Leest bronmateriaal (LinkedIn, Substack, website) uit Drive via service account
- Laat een agent nieuwe PATTERNS extraheren (skill=extract_style_patterns) — CORE gaat
  niet mee de prompt in
- Schrijft de bijgewerkte minkowski_voice.md lokaal weg (PATTERNS-sentinel vervangen)
- Slaat de verrijkte voice op als 04_Marketing/_kennis/minkowski_voice.md in Drive
  (zodat restore_voice.py de verrijking kan herstellen na een git reset --hard)
- Ververst alleen de PATTERNS-stub in verbal_identity.md, CORE blijft ongewijzigd
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

# Sentinel-comments die de PATTERNS-zone afbakenen — zowel in skills/minkowski_voice.md
# als in verbal_identity.md. Matchen op deze vaste markers i.p.v. koptekst-tekst (## 4. ...):
# koppen kunnen hernummerd/herschreven worden door mensen, sentinels niet. Ontbreken ze,
# dan faalt het script hard (zie _extract_sentinel_block/_replace_sentinel_block) in plaats
# van stilzwijgend te dupliceren — precies de bug die dit verving (zie CACHE_DESIGN.md-achtige
# postmortem: append-fallback op een ontbrekende "## 6."-marker liet dubbele stubs achter).
PATTERNS_START, PATTERNS_END = "<!-- PATTERNS:START -->", "<!-- PATTERNS:END -->"

# Bronnen die het rijkst zijn voor stijlpatronen (eigen stem, geen feiten-bronnen)
STIJL_BRONNEN = {"linkedin-jorgen", "linkedin-minkowski", "substack", "website-minkowski"}

VOICE_FILE = _REPO_ROOT / "skills" / "minkowski_voice.md"
# Subpaden ONDER de marketing-rolmap (prefix 04_), opgelost via drive_structure.
VERBAL_IDENTITY_PAD = ()            # de marketing-rolmap zelf
VERBAL_IDENTITY_NAAM = "verbal_identity"
VOICE_KENNIS_PAD = ("_kennis",)
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
    """Los een bronnen.json-locatie ('04_Marketing/...') op via drive_structure
    (prefix-matching, read-only). Hernoemen van de rolmap breekt dit niet."""
    import drive_structure as ds
    try:
        return ds.parse_location(service, locatie, create=False)
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
    """Download verbal_identity.md uit 04_Marketing. Geeft (inhoud, file_id)."""
    try:
        import drive_structure as ds
        folder_id = ds.resolve_path(service, "marketing", VERBAL_IDENTITY_PAD)
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
# Sentinel-parsing — vervangt het oude koptekst-matchen (## 4. ... ## 6.)
# ---------------------------------------------------------------------------

def _extract_sentinel_block(text: str, start_marker: str, end_marker: str) -> str:
    """Geeft de inhoud strikt tussen twee sentinel-markers. Raises als ze ontbreken."""
    i = text.find(start_marker)
    j = text.find(end_marker)
    if i == -1 or j == -1 or j <= i:
        raise ValueError(f"Sentinel-blok {start_marker}...{end_marker} niet gevonden of ongeldig.")
    return text[i + len(start_marker):j].strip()


def _replace_sentinel_block(text: str, start_marker: str, end_marker: str, new_inner: str) -> str:
    """Vervangt de inhoud strikt tussen twee sentinel-markers, markers blijven staan.

    Raises als de markers ontbreken — geen stille append-fallback. Dat was precies de
    oorzaak van de duplicatie-bug in verbal_identity.md (koptekst-marker "## 6." bestond
    niet, dus viel het oude script terug op appenden, wekelijks een nieuwe kopie erbij).
    """
    i = text.find(start_marker)
    j = text.find(end_marker)
    if i == -1 or j == -1 or j <= i:
        raise ValueError(
            f"Sentinel-blok {start_marker}...{end_marker} niet gevonden — "
            "weiger te schrijven (voorkomt stille duplicatie)."
        )
    before = text[: i + len(start_marker)]
    after = text[j:]
    return f"{before}\n{new_inner}\n{after}"


# ---------------------------------------------------------------------------
# Drive: voice opslaan als dedicated bestand in _kennis/
# ---------------------------------------------------------------------------

def _save_voice_to_drive_kennis(service, inhoud: str) -> None:
    """Sla minkowski_voice.md op als dedicated bestand in 04_Marketing/_kennis/
    zodat restore_voice.py de verrijking kan herstellen na een git reset --hard."""
    try:
        import drive_structure as ds
        folder_id = ds.resolve_path(service, "marketing", VOICE_KENNIS_PAD, create=True)
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

def _build_prompt(bronnen_tekst: str, huidige_patterns: str, today: str) -> str:
    """huidige_patterns is uitsluitend de PATTERNS-zone (vier schrijfpatronen, vocabulaire,
    citaten, NL/EN-verschil) — nooit CORE (taalregel, verboden woorden, em dash, schrijfregels).
    CORE leeft in verbal_identity.md en wordt hier nooit meegestuurd of overschreven."""
    return (
        "Verrijk de Minkowski PATTERNS-laag (waargenomen schrijfstijl) op basis van het "
        "bronmateriaal hieronder. Volg de extract_style_patterns skill. Dit is uitsluitend "
        "de evoluerende laag — vaste kernregels (taalregel, verboden woorden, em dash) staan "
        "elders en horen niet in je antwoord thuis.\n\n"
        f"Vandaag is {today}.\n\n"
        f"<HUIDIGE_PATTERNS>\n{huidige_patterns}\n</HUIDIGE_PATTERNS>\n\n"
        f"<BRONNEN>\n{bronnen_tekst}\n</BRONNEN>\n\n"
        f"Lever precies één blok ({STEM_START}…{STEM_END}) met de volledige bijgewerkte "
        "PATTERNS-inhoud. Niets erbuiten."
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

    # Huidige stem laden — alleen de PATTERNS-zone gaat naar de LLM.
    # CORE (taalregel, verboden woorden, em dash-verbod, schrijfregels) leeft
    # sinds 2026-07-06 uitsluitend in verbal_identity.md en wordt hier nooit
    # aangeraakt — dit bestand bevat het niet meer.
    if not VOICE_FILE.exists():
        log.error("skills/minkowski_voice.md niet gevonden: %s", VOICE_FILE)
        return 1
    huidige_bestand = VOICE_FILE.read_text(encoding="utf-8")
    try:
        huidige_patterns = _extract_sentinel_block(huidige_bestand, PATTERNS_START, PATTERNS_END)
    except ValueError as e:
        log.error("skills/minkowski_voice.md: %s — afgebroken (geen stille fallback).", e)
        return 1

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    import anthropic
    from agent import run_agent
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    log.info("Agent aan het werk (skill=extract_style_patterns)...")
    response, _ = run_agent(
        [{"role": "user", "content": _build_prompt(bronnen_tekst, huidige_patterns, today)}],
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

    nieuwe_patterns = response[i + len(STEM_START):j].strip()

    # Minimale sanity-check op de PATTERNS-inhoud (niet meer het hele bestand)
    if len(nieuwe_patterns) < len(huidige_patterns) * 0.7:
        log.error(
            "Nieuwe PATTERNS-inhoud is >30%% korter dan de huidige (%d vs %d tekens) — "
            "waarschijnlijk onvolledig. Afgebroken.",
            len(nieuwe_patterns), len(huidige_patterns),
        )
        return 1

    nieuwe_stem = _replace_sentinel_block(huidige_bestand, PATTERNS_START, PATTERNS_END, nieuwe_patterns)

    if args.dry_run:
        print("\n" + "=" * 64)
        print("NIEUWE MINKOWSKI VOICE — PATTERNS-zone (dry-run, niet weggeschreven)")
        print("=" * 64)
        print(nieuwe_patterns)
        return 0

    # Schrijf lokaal
    VOICE_FILE.write_text(nieuwe_stem, encoding="utf-8")
    log.info("skills/minkowski_voice.md bijgewerkt (PATTERNS: %d → %d tekens)", len(huidige_patterns), len(nieuwe_patterns))

    # Sla op in Drive als persistent backup (zodat restore_voice.py na deploy kan herstellen)
    _save_voice_to_drive_kennis(service, nieuwe_stem)

    # Update verbal_identity.md in Drive (secties 4+5 worden vervangen)
    _update_verbal_identity_in_drive(service, today)

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


def _update_verbal_identity_in_drive(service, today: str) -> None:
    """Ververst alleen de PATTERNS-stub in verbal_identity.md (sentinel-based, geen
    koptekst-matching meer). CORE (secties 1-3) wordt hier nooit aangeraakt — dat is
    precies het punt: dit script mag het onaantastbare deel niet kunnen wijzigen.

    Faalt hard als de PATTERNS-sentinels ontbreken, in plaats van stilzwijgend te
    appenden — dat appenden veroorzaakte de duplicatie-bug die dit vervangt.
    """
    inhoud, fid = _download_verbal_identity(service)
    if not inhoud:
        log.warning("verbal_identity.md niet gevonden of leeg — Drive-update overgeslagen.")
        return

    stub = (
        f"## 4. Schrijfpatronen — automatisch verrijkt\n\n"
        f"*Laatste update: {today}. Gegenereerd door update_stijl.py op basis van recente bronnen.*\n\n"
        f"Zie `skills/minkowski_voice.md` voor de volledige, actuele PATTERNS-laag die Ainstein "
        f"gebruikt. De kernregels (CORE) staan alleen in dit bestand.\n"
    )

    try:
        nieuwe_inhoud = _replace_sentinel_block(inhoud, PATTERNS_START, PATTERNS_END, stub)
    except ValueError as e:
        log.error(
            "verbal_identity.md: %s — Drive-update NIET uitgevoerd. "
            "Los dit handmatig op (sentinels teruggezet) vóór de volgende cron-run.",
            e,
        )
        _slack_notify(
            f":warning: *update_stijl.py kon verbal_identity.md niet bijwerken* ({today})\n"
            f"PATTERNS-sentinels ontbreken of zijn beschadigd. Geen wijziging doorgevoerd — "
            f"controleer het bestand handmatig in Drive."
        )
        return

    try:
        import drive_structure as ds
        folder_id = ds.resolve_path(service, "marketing", VERBAL_IDENTITY_PAD)
        _upload_markdown(service, VERBAL_IDENTITY_NAAM, nieuwe_inhoud, folder_id)
        log.info("verbal_identity.md PATTERNS-stub bijgewerkt in Drive (CORE ongewijzigd).")
    except Exception as e:
        log.warning("Kon verbal_identity.md niet bijwerken in Drive: %s", e)


if __name__ == "__main__":
    sys.exit(main())
