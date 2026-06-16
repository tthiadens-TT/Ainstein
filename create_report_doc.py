#!/usr/bin/env python3
"""
create_report_doc.py — Maakt een professioneel geformatteerd Google Doc voor Ainstein-rapporten.

Gebruik:
    python3 create_report_doc.py --title "Maandrapport Juni 2026" < rapport.md
    python3 create_report_doc.py --title "..." --parent-id FOLDER_ID < rapport.md

Markdown-syntaxis voor de invoertekst:
    # Titel tekst          → Grote documenttitel (Heading 1)
    ## Sectiekop           → Sectiekop (Heading 2)
    ### Subsectiekop       → Subsectiekop (Heading 3)
    *cursieve regel*       → Ondertitel (cursief, grijs)
    **vette regel**        → Sleutelregel (vet, blauw) — voor tijdsinvestering e.d.
    - bullet item          → Ongeordende lijst
    1. genummerd item      → Genummerde lijst
    ---                    → Scheidingslijn (grijs)
    ~~voettekst~~          → Voettekst (klein, grijs, cursief)
    gewone tekst           → Normale alinea
    (lege regel)           → Witruimte
"""

import argparse
import os
import sys

FOLDER_WERKDOCUMENTEN = "1he_FIDDdqdB8cFRHhbPxpBd1YbY9wQIm"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]


def _load_env():
    """Laad .env bestand als het beschikbaar is."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            if key.strip() not in os.environ:
                os.environ[key.strip()] = val.strip().strip('"').strip("'")


def _get_creds():
    sa_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_file and not sa_json:
        raise RuntimeError(
            "Geen service account credentials. "
            "Zet GOOGLE_SERVICE_ACCOUNT_FILE of GOOGLE_SERVICE_ACCOUNT_JSON in .env of omgeving."
        )
    from google.oauth2 import service_account
    if sa_file:
        return service_account.Credentials.from_service_account_file(sa_file, scopes=SCOPES)
    import json as _j
    return service_account.Credentials.from_service_account_info(_j.loads(sa_json), scopes=SCOPES)


def _rgb(r, g, b):
    return {"color": {"rgbColor": {"red": r, "green": g, "blue": b}}}


def parse_blocks(text):
    """Converteer eenvoudige markdown-tekst naar een lijst van content-blokken."""
    blocks = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            blocks.append({"type": "spacer"})
        elif line == "---":
            blocks.append({"type": "divider"})
        elif line.startswith("# "):
            blocks.append({"type": "title", "text": line[2:]})
        elif line.startswith("## "):
            blocks.append({"type": "heading", "text": line[3:]})
        elif line.startswith("### "):
            blocks.append({"type": "subheading", "text": line[4:]})
        elif line.startswith("~~") and line.endswith("~~") and len(line) > 4:
            blocks.append({"type": "footer", "text": line[2:-2]})
        elif line.startswith("**") and line.endswith("**") and len(line) > 4:
            blocks.append({"type": "keyline", "text": line[2:-2]})
        elif line.startswith("*") and line.endswith("*") and len(line) > 2:
            blocks.append({"type": "subtitle", "text": line[1:-1]})
        elif line.startswith("- "):
            blocks.append({"type": "bullet", "text": line[2:]})
        elif len(line) > 2 and line[0].isdigit() and line[1] in ".)" and line[2] == " ":
            blocks.append({"type": "numbered", "text": line[3:]})
        else:
            blocks.append({"type": "paragraph", "text": line})
    return blocks


def build_requests(blocks):
    """Bouw Google Docs API batchUpdate-verzoeken voor geformateerde inhoud.

    Verzoeken worden op volgorde uitgevoerd — elk insertText schuift de
    index op, en de stijlverzoeken die daarop volgen gebruiken de bijgewerkte
    indexen. Verzoeken voor tekststijl slaan de afsluitende \\n over (end_t)
    zodat de alinea-opmaak niet beïnvloed wordt.
    """
    requests = []
    idx = 1  # Nieuw Google Doc: body begint op index 1

    for block in blocks:
        btype = block["type"]
        text = block.get("text", "")

        if btype == "spacer":
            line = "\n"
        elif btype == "divider":
            line = "─" * 60 + "\n"
        else:
            line = text + "\n"

        n = len(line)
        end = idx + n        # inclusief \n — voor alineastijl
        end_t = idx + n - 1  # exclusief \n — voor tekststijl

        # Tekst invoegen
        requests.append({
            "insertText": {"location": {"index": idx}, "text": line}
        })

        # Alineastijl
        if btype == "title":
            requests.append({"updateParagraphStyle": {
                "range": {"startIndex": idx, "endIndex": end},
                "paragraphStyle": {"namedStyleType": "HEADING_1"},
                "fields": "namedStyleType",
            }})
        elif btype == "heading":
            requests.append({"updateParagraphStyle": {
                "range": {"startIndex": idx, "endIndex": end},
                "paragraphStyle": {"namedStyleType": "HEADING_2"},
                "fields": "namedStyleType",
            }})
        elif btype == "subheading":
            requests.append({"updateParagraphStyle": {
                "range": {"startIndex": idx, "endIndex": end},
                "paragraphStyle": {"namedStyleType": "HEADING_3"},
                "fields": "namedStyleType",
            }})
        elif btype in ("bullet",) and idx < end_t:
            requests.append({"createParagraphBullets": {
                "range": {"startIndex": idx, "endIndex": end},
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
            }})
        elif btype == "numbered" and idx < end_t:
            requests.append({"createParagraphBullets": {
                "range": {"startIndex": idx, "endIndex": end},
                "bulletPreset": "NUMBERED_DECIMAL_ALPHA_ROMAN",
            }})

        # Tekststijl-overrides
        if idx < end_t:
            if btype == "subtitle":
                requests.append({"updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end_t},
                    "textStyle": {
                        "italic": True,
                        "foregroundColor": _rgb(0.45, 0.45, 0.45),
                        "fontSize": {"magnitude": 10, "unit": "PT"},
                    },
                    "fields": "italic,foregroundColor,fontSize",
                }})
            elif btype == "keyline":
                requests.append({"updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end_t},
                    "textStyle": {
                        "bold": True,
                        "foregroundColor": _rgb(0.1, 0.38, 0.65),
                    },
                    "fields": "bold,foregroundColor",
                }})
            elif btype == "divider":
                requests.append({"updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end_t},
                    "textStyle": {
                        "foregroundColor": _rgb(0.78, 0.78, 0.78),
                        "fontSize": {"magnitude": 7, "unit": "PT"},
                    },
                    "fields": "foregroundColor,fontSize",
                }})
            elif btype == "footer":
                requests.append({"updateTextStyle": {
                    "range": {"startIndex": idx, "endIndex": end_t},
                    "textStyle": {
                        "italic": True,
                        "foregroundColor": _rgb(0.5, 0.5, 0.5),
                        "fontSize": {"magnitude": 9, "unit": "PT"},
                    },
                    "fields": "italic,foregroundColor,fontSize",
                }})

        idx += n

    return requests


def create_formatted_doc(title, parent_id, blocks):
    """Maak een geformatteerd Google Doc aan en geef het doc_id terug."""
    _load_env()
    creds = _get_creds()

    from googleapiclient.discovery import build

    drive = build("drive", "v3", credentials=creds)
    docs = build("docs", "v1", credentials=creds)

    # Leeg Google Doc aanmaken in doelmap
    created = drive.files().create(
        body={
            "name": title,
            "mimeType": "application/vnd.google-apps.document",
            "parents": [parent_id],
        },
        supportsAllDrives=True,
        fields="id,webViewLink",
    ).execute()

    doc_id = created["id"]
    url = created.get("webViewLink", f"https://docs.google.com/document/d/{doc_id}/edit")

    # Geformateerde inhoud toepassen
    reqs = build_requests(blocks)
    if reqs:
        docs.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": reqs},
        ).execute()

    print(f"Aangemaakt: {title}")
    print(f"URL: {url}")
    return doc_id, url


def main():
    parser = argparse.ArgumentParser(
        description="Maak een professioneel geformatteerd Google Doc voor Ainstein-rapporten."
    )
    parser.add_argument("--title", required=True, help="Documenttitel (bijv. 'Maandrapport Juni 2026')")
    parser.add_argument(
        "--parent-id",
        default=FOLDER_WERKDOCUMENTEN,
        dest="parent_id",
        help=f"Drive folder ID (default: {FOLDER_WERKDOCUMENTEN})",
    )
    args = parser.parse_args()

    text = sys.stdin.read()
    blocks = parse_blocks(text)
    create_formatted_doc(args.title, args.parent_id, blocks)


if __name__ == "__main__":
    main()
