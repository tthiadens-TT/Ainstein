#!/usr/bin/env python3
"""
Bulk-delete cache-bestanden uit folder-roots — snel, geen UI.
Verwijdert 157 bestanden in batch.
"""

import io, sys, os, time
sys.path.insert(0, "."); sys.path.insert(0, "scripts")
try:
    from dotenv import load_dotenv; load_dotenv()
except Exception:
    pass
from scrape_slack import _get_drive_service
from googleapiclient.http import MediaIoBaseDownload

s = _get_drive_service()
DRIVE = "0AFvBEDYKrnHbUk9PVA"
ROOTS = {"01_Clients", "02_Frameworks & Tools", "03_Experts", "04_Marketing", "05_Ainstein Knowledge Base"}

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
    if root["name"] not in ROOTS:
        continue
    direct_kids = children(root["id"])
    for md in [f for f in direct_kids if f["name"].lower().endswith(".md") and not f["mimeType"].endswith("folder")]:
        h = head(md["id"]) or ""
        if "**Gecachet:**" in h:
            to_delete.append((md["id"], md["name"]))

print(f"Deleting {len(to_delete)} cache-bestanden...")
deleted = failed = 0
for i, (fid, fname) in enumerate(to_delete):
    try:
        s.files().delete(fileId=fid, supportsAllDrives=True).execute()
        deleted += 1
        if (i+1) % 20 == 0:
            print(f"  {i+1}/{len(to_delete)} ✓")
    except Exception as e:
        failed += 1
        print(f"  {fname}: {e}")

print(f"\nKlaar: {deleted} verwijderd, {failed} mislukt")
