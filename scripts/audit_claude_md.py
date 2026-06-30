#!/usr/bin/env python3
"""
audit_claude_md.py — Controleer of CLAUDE.md up-to-date is met de repo.

Drie checks:
  1. Python modules (root + scripts/) — welke staan NIET in CLAUDE.md?
  2. Skills (skills/*.md) — welke staan NIET in de skills-sectie?
  3. Drive-mappen — welke paden uit de code ontbreken in de Source Layer tabel?

Gebruik:
    python3 scripts/audit_claude_md.py
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

# Modules die we bewust niet documenteren (infra/hulp, geen Ainstein-logica)
SKIP_MODULES = {
    "log_setup.py",          # logging boilerplate
    "memory.py",             # deprecated local memory (pre-Drive)
    "models.py",             # dataclasses / type stubs
    "read_pdf.py",           # utility, gedocumenteerd in memory (PDF-leesregel)
    "setup_gdrive_auth.py",  # eenmalig setup script
    "read_gdoc_comments.py", # utility
    "update_gdoc.py",        # utility
    "list_drive_changes.py", # utility
    "setup_outcomes.py",     # eenmalig setup script
    "run_backup.sh",         # bash, geen py
    "__init__.py",
    # Scrapers: gedekt door generieke vermelding in Current State
    # ("scrapers voor LinkedIn, Medium, Substack, website, Slack")
    "scrape_linkedin.py",
    "scrape_medium.py",
    "scrape_substack.py",
    "scrape_website.py",
    "scrape_slack.py",
    # Infra/backup: gedekt door backup_architecture memory
    "backup_drive.py",
    # Dit script zelf
    "audit_claude_md.py",
}

# Drive-mappen die in de code voorkomen en gedocumenteerd moeten zijn
EXPECTED_DRIVE_FOLDERS = [
    "00_Werkdocumenten",
    "01_Clients",
    "02_Frameworks & Tools",
    "03_Experts",
    "04_Marketing",
    "05_Ainstein Knowledge Base",
    "_bronmateriaal",
    "_kennis",
]

# Repo-assets die gedocumenteerd moeten zijn
EXPECTED_ASSETS = [
    "assets/fonts/Sen-ExtraBold.ttf",
    "scripts/bronnen.json",
]


def load_claude_md():
    return CLAUDE_MD.read_text(encoding="utf-8")


def check_python_modules(claude_text):
    issues = []

    # Root .py bestanden
    root_py = [
        p.name for p in REPO_ROOT.glob("*.py")
        if p.name not in SKIP_MODULES
    ]
    # scripts/ .py bestanden
    scripts_py = [
        p.name for p in (REPO_ROOT / "scripts").glob("*.py")
        if p.name not in SKIP_MODULES
    ]

    all_modules = sorted(set(root_py + scripts_py))

    for mod in all_modules:
        stem = mod.replace(".py", "")
        # Check op bestandsnaam (met of zonder .py) in CLAUDE.md
        if mod not in claude_text and stem not in claude_text:
            issues.append(mod)

    return all_modules, issues


def check_skills(claude_text):
    skills_dir = REPO_ROOT / "skills"
    all_skills = sorted(p.stem for p in skills_dir.glob("*.md"))
    missing = [s for s in all_skills if s not in claude_text]
    return all_skills, missing


def check_drive_folders(claude_text):
    missing = [f for f in EXPECTED_DRIVE_FOLDERS if f not in claude_text]
    return EXPECTED_DRIVE_FOLDERS, missing


def check_assets(claude_text):
    missing = []
    for asset in EXPECTED_ASSETS:
        # Check op bestandsnaam of pad
        name = Path(asset).name
        if asset not in claude_text and name not in claude_text:
            missing.append(asset)
    return EXPECTED_ASSETS, missing


def _section(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print('─' * 60)


def main():
    if not CLAUDE_MD.exists():
        print("FOUT: CLAUDE.md niet gevonden op", CLAUDE_MD)
        sys.exit(1)

    claude_text = load_claude_md()

    total_issues = 0

    # 1 — Python modules
    _section("1. Python modules")
    all_mods, missing_mods = check_python_modules(claude_text)
    if missing_mods:
        print(f"  ONTBREEKT ({len(missing_mods)}/{len(all_mods)}):")
        for m in missing_mods:
            print(f"    ✗  {m}")
        total_issues += len(missing_mods)
    else:
        print(f"  ✓  Alle {len(all_mods)} modules gedocumenteerd")

    # 2 — Skills
    _section("2. Skills (skills/*.md)")
    all_skills, missing_skills = check_skills(claude_text)
    if missing_skills:
        print(f"  ONTBREEKT ({len(missing_skills)}/{len(all_skills)}):")
        for s in missing_skills:
            print(f"    ✗  {s}")
        total_issues += len(missing_skills)
    else:
        print(f"  ✓  Alle {len(all_skills)} skills gedocumenteerd")

    # 3 — Drive-mappen
    _section("3. Drive-mappen (Source Layer tabel)")
    all_folders, missing_folders = check_drive_folders(claude_text)
    if missing_folders:
        print(f"  ONTBREEKT ({len(missing_folders)}/{len(all_folders)}):")
        for f in missing_folders:
            print(f"    ✗  {f}")
        total_issues += len(missing_folders)
    else:
        print(f"  ✓  Alle {len(all_folders)} Drive-mappen gedocumenteerd")

    # 4 — Repo-assets
    _section("4. Repo-assets (bronnen.json, fonts, etc.)")
    all_assets, missing_assets = check_assets(claude_text)
    if missing_assets:
        print(f"  ONTBREEKT ({len(missing_assets)}/{len(all_assets)}):")
        for a in missing_assets:
            print(f"    ✗  {a}")
        total_issues += len(missing_assets)
    else:
        print(f"  ✓  Alle {len(all_assets)} assets gedocumenteerd")

    # Totaal
    print(f"\n{'═' * 60}")
    if total_issues == 0:
        print("  AUDIT GESLAAGD — niets ontbreekt in CLAUDE.md")
    else:
        print(f"  AUDIT GEFAALD — {total_issues} item(s) ontbreken in CLAUDE.md")
    print('═' * 60)

    sys.exit(0 if total_issues == 0 else 1)


if __name__ == "__main__":
    main()
