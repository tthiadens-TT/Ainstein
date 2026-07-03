#!/usr/bin/env python3
"""
migrate_stray_marketing.py — Eenmalige opruiming van de verweesde spookmap
`06_Marketing` op de Shared Drive-root, ontstaan doordat scrapers vóór de
drive_structure-fix (commit bd836c6) de oude mapnaam gebruikten.

WAT HET DOET
------------
1. Vergelijkt elk bestand in de stray `06_Marketing/_bronmateriaal/slack/` met
   zijn naamgenoot in de ECHTE `04_Marketing/_bronmateriaal/slack/`.
   Classificatie per bestand (inhoud byte-vergeleken):
     - UNIEK            : alleen in stray            -> verplaatsen naar echt
     - IDENTIEK         : zelfde inhoud              -> stray naar prullenbak
     - STRAY_SUBSET     : stray-inhoud zit in real   -> stray naar prullenbak
     - REAL_SUBSET      : real-inhoud zit in stray   -> stray WINT (real->prullenbak, stray verplaatst)
     - DIVERGENT        : geen van beide             -> OVERSLAAN, melden voor handmatig oordeel
2. Ruimt daarna op (alleen als leeg): stray slack/_bronmateriaal/06_Marketing,
   plus de dubbele LEGE `_kennis`-map onder 04_Marketing (id via --dup-kennis).

VEILIG
------
--dry-run (default): alleen lezen + classificeren, niets wijzigen.
--apply: voert de veilige acties uit. DIVERGENTE bestanden worden NOOIT
automatisch aangeraakt. Verwijderen = naar prullenbak (trashed=true), 30 dagen
herstelbaar. Niet-lege mappen worden nooit verwijderd.

GEBRUIK (op de VM)
------------------
    cd ~/Ainstein
    python3 scripts/migrate_stray_marketing.py            # dry-run
    python3 scripts/migrate_stray_marketing.py --apply
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
except Exception:
    pass

import drive_structure as ds
from gdoc_tools import _get_service_account_creds
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

ROOT_ID = "0AFvBEDYKrnHbUk9PVA"
DUP_EMPTY_KENNIS_ID = "1e8ZeptGvdAdDUu_7m15YxLyyZu_ibBTb"  # lege 30-juni-duplicaat


def _children(svc, pid):
    out, tok = [], None
    while True:
        r = svc.files().list(
            q=f"'{pid}' in parents and trashed=false",
            fields="nextPageToken, files(id,name,mimeType,size)",
            corpora="drive", driveId=ROOT_ID,
            supportsAllDrives=True, includeItemsFromAllDrives=True,
            pageSize=200, pageToken=tok,
        ).execute()
        out.extend(r.get("files", []))
        tok = r.get("nextPageToken")
        if not tok:
            break
    return out


def _download(svc, fid) -> str:
    req = svc.files().get_media(fileId=fid, supportsAllDrives=True)
    buf = io.BytesIO()
    d = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = d.next_chunk()
    return buf.getvalue().decode("utf-8", errors="replace")


def _trash(svc, fid):
    svc.files().update(fileId=fid, body={"trashed": True}, supportsAllDrives=True).execute()


def _move(svc, fid, new_parent, old_parent):
    svc.files().update(fileId=fid, addParents=new_parent, removeParents=old_parent,
                       supportsAllDrives=True, fields="id").execute()


def _update_content(svc, fid, text):
    media = MediaIoBaseUpload(io.BytesIO(text.encode("utf-8")), mimetype="text/plain", resumable=False)
    svc.files().update(fileId=fid, media_body=media, supportsAllDrives=True, fields="id").execute()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Voer de veilige acties uit (default: dry-run)")
    ap.add_argument("--show-divergent", action="store_true",
                    help="Print per divergent bestand de stray-regels die NIET in real staan (read-only)")
    ap.add_argument("--merge-divergent", action="store_true",
                    help="Divergente bestanden mergen: unieke late-juni-staart uit stray achter real aanvullen "
                         "(bestanden waar alleen de header-datum verschilt: stray naar prullenbak)")
    args = ap.parse_args()
    mode = "APPLY" if args.apply else "DRY-RUN"

    svc = build("drive", "v3", credentials=_get_service_account_creds(), cache_discovery=False)

    # Stray 06_Marketing op root vinden (exacte oude naam, dus GEEN drive_structure-rol)
    stray = [f for f in _children(svc, ROOT_ID)
             if f["name"] == "06_Marketing" and f["mimeType"].endswith("folder")]
    if not stray:
        print("Geen stray '06_Marketing' op root — niets te doen.")
        return 0
    stray_id = stray[0]["id"]

    # Echte slack-map via drive_structure
    real_slack = ds.resolve_path(svc, "marketing", ("_bronmateriaal", "slack"), create=True)

    # Stray slack-map opzoeken (kan ontbreken)
    stray_slack = None
    bm = [f for f in _children(svc, stray_id) if f["name"] == "_bronmateriaal"]
    if bm:
        sl = [f for f in _children(svc, bm[0]["id"]) if f["name"] == "slack"]
        if sl:
            stray_slack = sl[0]["id"]

    print("=" * 64)
    print(f"MIGRATIE STRAY 06_Marketing  [{mode}]")
    print(f"  stray 06_Marketing = {stray_id}")
    print(f"  echte slack-map    = {real_slack}")
    print("=" * 64)

    divergent = []
    if stray_slack:
        real_files = {f["name"]: f for f in _children(svc, real_slack)}
        for f in sorted(_children(svc, stray_slack), key=lambda x: x["name"]):
            n = f["name"]
            sc = _download(svc, f["id"])
            if n not in real_files:
                print(f"  UNIEK        {n} ({len(sc)}c) -> verplaatsen")
                if args.apply:
                    _move(svc, f["id"], real_slack, stray_slack)
                continue
            rc = _download(svc, real_files[n]["id"])
            if sc == rc:
                print(f"  IDENTIEK     {n} -> stray naar prullenbak")
                if args.apply:
                    _trash(svc, f["id"])
            elif sc in rc:
                print(f"  STRAY_SUBSET {n} (stray {len(sc)}c ⊂ real {len(rc)}c) -> stray naar prullenbak")
                if args.apply:
                    _trash(svc, f["id"])
            elif rc in sc:
                print(f"  REAL_SUBSET  {n} (real {len(rc)}c ⊂ stray {len(sc)}c) -> stray wint, real naar prullenbak")
                if args.apply:
                    _trash(svc, real_files[n]["id"])
                    _move(svc, f["id"], real_slack, stray_slack)
            else:
                real_lines = set(l.strip() for l in rc.splitlines() if l.strip())
                uniek = [l for l in sc.splitlines()
                         if l.strip() and l.strip() not in real_lines
                         and not l.strip().startswith("_Bron:")]
                if args.merge_divergent:
                    if not uniek:
                        print(f"  MERGE {n}: alleen header-datum verschilt -> stray naar prullenbak")
                        if args.apply:
                            _trash(svc, f["id"])
                    else:
                        print(f"  MERGE {n}: {len(uniek)} unieke regels -> aanvullen achter real, dan stray weg")
                        if args.apply:
                            merged = (
                                rc.rstrip()
                                + "\n\n---\n\n## [Aangevuld 2026-07-02] Late-juni berichten uit de verweesde 06_Marketing\n"
                                + "_De echte maand-file stopte met bijwerken bij de map-hernoeming op 30 juni; "
                                + "dit blok is de 30-juni-staart die de scraper toen naar de verweesde map schreef._\n\n"
                                + sc.strip() + "\n"
                            )
                            _update_content(svc, real_files[n]["id"], merged)
                            _trash(svc, f["id"])
                else:
                    print(f"  DIVERGENT    {n} (stray {len(sc)}c ≠ real {len(rc)}c) -> OVERGESLAGEN, handmatig oordeel")
                    divergent.append(n)
                    if args.show_divergent:
                        print(f"      stray-regels NIET in real ({len(uniek)}):")
                        for l in uniek[:15]:
                            print(f"        + {l[:100]}")

    # Opruimen (alleen lege mappen), na de bestand-migratie
    print("-" * 64)
    def _maybe_trash_folder(fid, label):
        kids = _children(svc, fid)
        if kids:
            print(f"  LAAT STAAN   {label} (nog {len(kids)} items)")
            return False
        print(f"  LEEG -> weg  {label}")
        if args.apply:
            _trash(svc, fid)
        return True

    if not divergent:
        # stray slack -> _bronmateriaal -> 06_Marketing, van binnen naar buiten
        if stray_slack:
            _maybe_trash_folder(stray_slack, "stray .../slack")
        if bm:
            _maybe_trash_folder(bm[0]["id"], "stray .../_bronmateriaal")
        _maybe_trash_folder(stray_id, "stray 06_Marketing")
    else:
        print(f"  STRAY BLIJFT staan: {len(divergent)} divergente bestanden eerst oplossen: {divergent}")

    # Dubbele lege _kennis onder 04_Marketing
    try:
        dup = svc.files().get(fileId=DUP_EMPTY_KENNIS_ID, fields="id,name,parents",
                              supportsAllDrives=True).execute()
        _maybe_trash_folder(DUP_EMPTY_KENNIS_ID, f"dubbele lege _kennis ({dup.get('name')})")
    except Exception as e:
        print(f"  dubbele _kennis niet gevonden/al weg: {e}")

    print("=" * 64)
    if not args.apply:
        print("DRY-RUN: niets gewijzigd. Draai met --apply om uit te voeren.")
    elif divergent:
        print(f"KLAAR (deels): {len(divergent)} divergente bestanden vereisen handmatig oordeel.")
    else:
        print("KLAAR: migratie + opruiming voltooid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
