#!/usr/bin/env python3
"""
Opruimen: verwijder cache-bestanden uit folder-roots.

Dit zijn oude bestanden van vóór de fix in commit 709b9d7.
Ze horen niet in folder-roots (01_Clients, 04_Marketing, etc.) maar in submappen.
Dit script verwijdert ze zodat de structuur schoon is.

Gebruik:
    python3 scripts/cleanup_stray_cache.py
    python3 scripts/cleanup_stray_cache.py --dry-run
"""

import io, sys, os
sys.path.insert(0, "."); sys.path.insert(0, "scripts")
try:
    from dotenv import load_dotenv; load_dotenv()
except Exception:
    pass
from scrape_slack import _get_drive_service
from googleapiclient.http import MediaIoBaseDownload

s = _get_drive_service()
DRIVE = "0AFvBEDYKrnHbUk9PVA"

ROOTS_THAT_SHOULD_BE_CLEAN = {
    "01_Clients", "02_Frameworks & Tools", "03_Experts", "04_Marketing", "05_Ainstein Knowledge Base"
}

def head(fid, n=400):
    try:
        req = s.files().get_media(fileId=fid, supportsAllDrives=True)
        buf = io.BytesIO(); dl = MediaIoBaseDownload(buf, req, chunksize=n*2)
        done = False
        while not done:
            _, done = dl.next_chunk()
            if buf.tell() >= n: break
        return buf.getvalue()[:n].decode("utf-8", "replace")
    except Exception:
        return None

def children(fid):
    out, tok = [], None
    while True:
        r = s.files().list(q="'%s' in parents and trashed=false" % fid,
            fields="nextPageToken, files(id,name,mimeType)", pageSize=200,
            supportsAllDrives=True, includeItemsFromAllDrives=True, pageToken=tok).execute()
        out += r.get("files", []); tok = r.get("nextPageToken")
        if not tok: break
    return out

roots = children(DRIVE)
to_delete = []

for root in roots:
    if root["name"] not in ROOTS_THAT_SHOULD_BE_CLEAN:
        continue

    root_id = root["id"]
    root_name = root["name"]
    direct_kids = children(root_id)
    direct_mds = [f for f in direct_kids if f["name"].lower().endswith(".md")
                   and not f["mimeType"].endswith("folder")]

    for md in direct_mds:
        h = head(md["id"]) or ""
        if "**Gecachet:**" in h:
            to_delete.append((root_name, md["id"], md["name"]))

print("=== CLEANUP STRAY CACHE FILES ===\n")
print("Gevonden: %d cache-bestanden in folder-roots" % len(to_delete))

if not to_delete:
    print("Geen stray cache-bestanden. Structuur is schoon.\n")
    sys.exit(0)

for root_name, fid, fname in sorted(to_delete):
    print(f"  [{root_name}] {fname}")

dry_run = "--dry-run" in sys.argv
if dry_run:
    print(f"\n(DRY-RUN: {len(to_delete)} bestanden zouden verwijderd worden)")
    sys.exit(0)

print(f"\nVerwijderen...")
deleted = 0
for root_name, fid, fname in to_delete:
    try:
        s.files().delete(fileId=fid, supportsAllDrives=True).execute()
        print(f"  ✓ {fname}")
        deleted += 1
    except Exception as e:
        print(f"  ✗ {fname}: {e}")

print(f"\nKlaar. Verwijderd: {deleted} / {len(to_delete)}")
