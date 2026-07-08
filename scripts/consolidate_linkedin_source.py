#!/usr/bin/env python3
"""consolidate_linkedin_source.py — EENMALIG. Herstel compleetheid van de
LinkedIn/Substack-bronnen en ruim verweesde legacy-docs op.

ACHTERGROND (8 juli 2026): de kennislaag-pijplijn las voor LinkedIn-Jörgen een
handmatige scrape van 42 posts (`linkedin_jorgen_archief.md`), terwijl een
completere scrape van 120 posts (27 mei) verweesd als Google Doc in de root van
`_bronmateriaal/` lag — ongelezen. Er was geen compleetheids-check, dus de armere
bron werd stilzwijgend canoniek. Dit script maakt de rijkste versie per bron
canoniek (als platte `.md` in de juiste pijplijn-map) en ruimt de wezen op.

De code-oorzaak (scraper met datum-in-de-naam → stapelt, en kon een rijkere bron
overschrijven met minder) is los gefixt in `scrape_linkedin.py`
(compleetheids-grendel + stabiele bestandsnaam).

VEILIG: standaard --dry-run (leest alleen, verwijdert niets). Pas met --apply
worden bestanden geschreven/naar de prullenbak verplaatst (omkeerbaar: trash,
geen permanente delete). Draai op de VM:
    python3 scripts/consolidate_linkedin_source.py            # dry-run
    python3 scripts/consolidate_linkedin_source.py --apply    # uitvoeren

NB: eenmalig hulpmiddel. Na een geslaagde --apply mag dit script weg (zie
roadmap) — het hoort niet in de vaste pijplijn.
"""
import argparse
import io
import os
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass

import tools
from scripts.verify_shared_drive import _get_drive_service

ROOT = os.environ.get("AINSTEIN_DRIVE_ROOT_ID", "0AFvBEDYKrnHbUk9PVA")


def _count_posts(text: str) -> int:
    md = len(re.findall(r'(?m)^#{2,3}\s+', text))
    labels = len(re.findall(r'(?mi)^\s*POST\s+\d', text))
    urls = len(re.findall(r'_URL:', text))
    return max(md - 1, labels, urls, 0)


def _kids(svc, pid):
    return svc.files().list(
        q=f"'{pid}' in parents and trashed=false",
        fields="files(id,name,mimeType,size)",
        supportsAllDrives=True, includeItemsFromAllDrives=True,
        corpora="drive", driveId=ROOT, pageSize=1000,
    ).execute().get("files", [])


def _folder_by_prefix(svc, pid, prefix):
    for f in _kids(svc, pid):
        if f["mimeType"].endswith("folder") and f["name"].startswith(prefix):
            return f["id"]
    return None


def _read(svc, f):
    return tools._read_drive_file_content(svc, f["id"], f["name"], f["mimeType"])


def _shingles(text: str, k: int = 8) -> set:
    """Genormaliseerde k-woord-shingles van de inhoudelijke tekst — formaat-
    onafhankelijke vingerafdruk om overlap tussen twee scrapes te meten."""
    words = re.findall(r"\w+", text.lower())
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}


def _coverage(orphan_txt: str, canonical_txt: str) -> float:
    """Welk deel van de wees-inhoud zit al in het canonieke bestand? 1.0 = volledig
    gedekt (veilig te verwijderen); <1.0 = de wees heeft unieke inhoud."""
    o = _shingles(orphan_txt)
    if not o:
        return 1.0
    c = _shingles(canonical_txt)
    return len(o & c) / len(o)


COVERAGE_SAFE = 0.92  # ≥ dit deel gedekt → wees is (vrijwel) subset, veilig te trashen


def _upload_md(svc, name, content, folder_id, apply):
    md = name if name.endswith(".md") else f"{name}.md"
    if not apply:
        print(f"    [dry-run] zou schrijven: {md} ({len(content)} tekens) in map {folder_id}")
        return
    from googleapiclient.http import MediaIoBaseUpload
    existing = svc.files().list(
        q=f"'{folder_id}' in parents and name='{md}' and trashed=false",
        fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute().get("files", [])
    media = MediaIoBaseUpload(io.BytesIO(content.encode("utf-8")),
                              mimetype="text/plain", resumable=False)
    if existing:
        svc.files().update(fileId=existing[0]["id"], media_body=media,
                           supportsAllDrives=True).execute()
        print(f"    ✓ bijgewerkt: {md}")
    else:
        svc.files().create(body={"name": md, "mimeType": "text/plain",
                                 "parents": [folder_id]}, media_body=media,
                          supportsAllDrives=True).execute()
        print(f"    ✓ aangemaakt: {md}")


def _trash(svc, f, apply):
    if not apply:
        print(f"    [dry-run] zou naar prullenbak: {f['name']}")
        return
    svc.files().update(fileId=f["id"], body={"trashed": True},
                       supportsAllDrives=True).execute()
    print(f"    ✓ naar prullenbak: {f['name']}")


def consolidate_source(svc, submap_id, submap_name, orphan_files, stable_name, apply):
    """Kies de rijkste versie tussen de pijplijn-map en de verweesde docs,
    schrijf die als stabiele .md in de submap, en ruim de rest op."""
    print(f"\n── bron: {submap_name} ──")
    map_files = _kids(svc, submap_id)
    all_candidates = [("pijplijn", f) for f in map_files] + [("wees", f) for f in orphan_files]
    if not all_candidates:
        print("    geen bestanden gevonden — overslaan")
        return

    scored = []
    for herkomst, f in all_candidates:
        txt = _read(svc, f)
        n = _count_posts(txt)
        scored.append((n, herkomst, f, txt))
        print(f"    kandidaat [{herkomst}] {f['name']}: ~{n} posts, {len(txt)} tekens")

    # Kies canoniek op postentelling; gelijkspel → meeste tekens. Maar val terug
    # op tekens wanneer de telling onbetrouwbaar is (proza zonder post-scheidingen,
    # bv. Substack → telling 0 terwijl het bestand vol staat).
    def sort_key(x):
        n, h, f, txt = x
        return (n, len(txt))
    scored.sort(key=sort_key, reverse=True)
    best_n, best_h, best_f, best_txt = scored[0]
    print(f"    → RIJKSTE: [{best_h}] {best_f['name']} (~{best_n} posts, {len(best_txt)} tekens)")

    already_canonical = (best_h == "pijplijn" and best_f["name"] == f"{stable_name}.md")
    if already_canonical:
        print(f"    canoniek bestand is al correct ({stable_name}.md) — niets te schrijven")
    else:
        _upload_md(svc, stable_name, best_txt.lstrip("﻿"), submap_id, apply)

    # Ruim de overige kandidaten alleen op als hun inhoud aantoonbaar al in het
    # canonieke bestand zit. Overlap-grendel: nooit unieke content verliezen.
    for n, h, f, txt in scored:
        if f["id"] == best_f["id"]:
            continue
        cov = _coverage(txt, best_txt)
        if cov >= COVERAGE_SAFE:
            print(f"    inhoud '{f['name']}' voor {cov:.0%} gedekt door canoniek → opruimen")
            _trash(svc, f, apply)
        else:
            print(f"    ⚠ '{f['name']}' slechts {cov:.0%} gedekt — UNIEKE inhoud, "
                  f"NIET verwijderd. Handmatig beoordelen (mogelijk nieuwere posts).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Voer schrijf/trash echt uit (default: dry-run)")
    args = ap.parse_args()
    apply = args.apply

    svc = _get_drive_service()
    print("=" * 70)
    print(f"CONSOLIDATIE LinkedIn/Substack-bronnen — {'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 70)

    mk = _folder_by_prefix(svc, ROOT, "04_")
    bron = _folder_by_prefix(svc, mk, "_bronmateriaal")
    linkedin = _folder_by_prefix(svc, bron, "linkedin")
    jorgen = _folder_by_prefix(svc, linkedin, "jorgen")
    minkowski = _folder_by_prefix(svc, linkedin, "minkowski")
    substack = _folder_by_prefix(svc, bron, "substack")

    root_files = _kids(svc, bron)  # losse wezen in _bronmateriaal root

    def orphans(*needles):
        out = []
        for f in root_files:
            if f["mimeType"].endswith("folder"):
                continue
            if all(nd.lower() in f["name"].lower() for nd in needles[:1]) and \
               any(nd.lower() in f["name"].lower() for nd in needles):
                out.append(f)
        return out

    # LinkedIn Jörgen: wezen = "LinkedIn Posts — Jörgen ..." (VOLLEDIG + kleine)
    jorgen_orphans = [f for f in root_files if not f["mimeType"].endswith("folder")
                      and "linkedin posts" in f["name"].lower() and "jörgen" in f["name"].lower()]
    consolidate_source(svc, jorgen, "linkedin/jorgen", jorgen_orphans, "linkedin_jorgen", apply)

    # LinkedIn Minkowski: wees = "LinkedIn Posts — Minkowski ..."
    mink_orphans = [f for f in root_files if not f["mimeType"].endswith("folder")
                    and "linkedin posts" in f["name"].lower() and "minkowski" in f["name"].lower()]
    consolidate_source(svc, minkowski, "linkedin/minkowski", mink_orphans, "linkedin_minkowski", apply)

    # Substack: wees = "Substack Artikelen — ..."
    sub_orphans = [f for f in root_files if not f["mimeType"].endswith("folder")
                   and "substack artikelen" in f["name"].lower()]
    consolidate_source(svc, substack, "substack", sub_orphans, "substack_futuresready_2025", apply)

    print("\n" + "=" * 70)
    print("KLAAR." + ("" if apply else "  (dry-run — niets gewijzigd; draai met --apply)"))
    print("=" * 70)


if __name__ == "__main__":
    main()
