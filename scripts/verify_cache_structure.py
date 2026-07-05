#!/usr/bin/env python3
"""
Verifieer de cache-structuur: geen .md-rommeling in folder-roots.

Dit script checkt dat cache-bestanden (.md met **Gecachet:** header) staan
in hun juiste submappen — naast het origineel — niet plat in folder-roots.

Design-regel: cache-bestanden horen NÁ́ÁST hun bronbestand, niet gegroepeerd
in één root. Violaties wijzen op fouten in convert_to_markdown.py.

Gebruik:
    python3 scripts/verify_cache_structure.py
    python3 scripts/verify_cache_structure.py --folder 04_Marketing
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

# Deze mappen zijn "ROOT" — ze mogen GEEN cache-bestanden bevatten (laag rommel)
# Cache-bestanden horen in submappen (naast origineel)
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
violations = []

for root in roots:
    if root["name"] not in ROOTS_THAT_SHOULD_BE_CLEAN:
        continue

    root_id = root["id"]
    root_name = root["name"]
    direct_kids = children(root_id)
    direct_mds = [f for f in direct_kids if f["name"].lower().endswith(".md")
                   and not f["mimeType"].endswith("folder")]

    # Controleer: zijn dit cache-bestanden? (hebben **Gecachet:** header)
    for md in direct_mds:
        h = head(md["id"]) or ""
        if "**Gecachet:**" in h:
            violations.append({
                "root": root_name,
                "file": md["name"],
                "reason": "Cache-bestand staat in root (moet in subfolder)"
            })

print("=== CACHE STRUCTURE VERIFICATION ===\n")

if not violations:
    print("✅ SCHOON: geen cache-bestanden in folder-roots gevonden.")
    print("Cache-bestanden staan correct in hun submappen (naast origineel).\n")
    sys.exit(0)

print("❌ VIOLATIONS GEVONDEN: %d cache-bestanden in folder-roots\n" % len(violations))
for v in violations:
    print(f"  [{v['root']}] {v['file']}")
    print(f"    → {v['reason']}\n")

print("\nDIT DUIDT OP:")
print("  - convert_to_markdown.py schreef cache naar folder-root i.p.v. subfolder")
print("  - De fix in commit 709b9d7 werkt niet, OF")
print("  - Er is een nieuwe cache-run gedraaid met oude, foutieve code\n")

sys.exit(1)
