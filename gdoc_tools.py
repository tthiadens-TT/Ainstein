"""
Google Docs write operations for Ainstein.

Provides: create_gdoc, update_gdoc_section, resolve_comment, get_doc_content.
All functions raise RuntimeError on failure so callers can surface meaningful
error messages rather than silently returning None.

Credentials (SA-first, OAuth-fallback):
- On the VM: set GOOGLE_SERVICE_ACCOUNT_FILE (path to JSON key) or
  GOOGLE_SERVICE_ACCOUNT_JSON (inline JSON string). The service account
  needs both drive and documents scope.
- Locally: falls back to OAuth via update_gdoc.py / setup_gdrive_auth.py.
"""

import logging
import os
import re

logger = logging.getLogger("gdoc_tools")

_DOCS_SERVICE = None
_DRIVE_WRITE_SERVICE = None

# Google Drive folder ID for the AInstein root (contains 01_Clients … 05_Ainstein Knowledge Base)
# Default points to the Workspace Shared Drive "Minkowski AInstein" — same as tools.py.
_AINSTEIN_DRIVE_ROOT_ID = os.environ.get(
    "AINSTEIN_DRIVE_ROOT_ID", "0AFvBEDYKrnHbUk9PVA"
)
# Cached working-folder ID — resolved lazily on first create_gdoc() call
_WERKDOCUMENTEN_FOLDER_ID: str | None = None


def _get_service_account_creds():
    """Return service account credentials (VM/server mode).

    Tries GOOGLE_SERVICE_ACCOUNT_FILE first, then GOOGLE_SERVICE_ACCOUNT_JSON.
    Returns None when neither is set — falls back to local OAuth mode.
    """
    import json as _json
    import os as _os
    sa_file = _os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    sa_json_str = _os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_file and not sa_json_str:
        return None
    try:
        from google.oauth2 import service_account
        scopes = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/documents",
        ]
        if sa_file:
            return service_account.Credentials.from_service_account_file(sa_file, scopes=scopes)
        info = _json.loads(sa_json_str)
        return service_account.Credentials.from_service_account_info(info, scopes=scopes)
    except Exception as e:
        logger.error("gdoc_tools: service account init failed: %s", e)
        return None


def _get_docs_service():
    global _DOCS_SERVICE
    if _DOCS_SERVICE is not None:
        return _DOCS_SERVICE
    from googleapiclient.discovery import build

    sa_creds = _get_service_account_creds()
    if sa_creds:
        _DOCS_SERVICE = build("docs", "v1", credentials=sa_creds, cache_discovery=False)
        logger.info("gdoc_tools: Docs service via service account")
        return _DOCS_SERVICE

    # OAuth fallback — alleen voor lokale ontwikkeling.
    # Op de VM moet GOOGLE_SERVICE_ACCOUNT_FILE of GOOGLE_SERVICE_ACCOUNT_JSON zijn gezet.
    # Als die ontbreken op de VM is er een configuratiefout — fail fast met duidelijke melding.
    if os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE") or os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        raise RuntimeError(
            "Service account env vars zijn gezet maar credentials konden niet worden geladen. "
            "Controleer GOOGLE_SERVICE_ACCOUNT_FILE of GOOGLE_SERVICE_ACCOUNT_JSON."
        )

    try:
        from update_gdoc import get_creds, CredentialsError
        creds = get_creds(raise_on_error=True)
        _DOCS_SERVICE = build("docs", "v1", credentials=creds, cache_discovery=False)
        logger.info("gdoc_tools: Docs service via OAuth (lokale modus)")
        return _DOCS_SERVICE
    except Exception as e:
        raise RuntimeError(
            f"Geen geldige credentials voor Google Docs. "
            f"Op de VM: zet GOOGLE_SERVICE_ACCOUNT_FILE. Lokaal: draai setup_gdrive_auth.py. Fout: {e}"
        ) from e


def _get_drive_write_service():
    """Drive v3 client with write scope (for comment operations)."""
    global _DRIVE_WRITE_SERVICE
    if _DRIVE_WRITE_SERVICE is not None:
        return _DRIVE_WRITE_SERVICE
    from googleapiclient.discovery import build

    sa_creds = _get_service_account_creds()
    if sa_creds:
        _DRIVE_WRITE_SERVICE = build("drive", "v3", credentials=sa_creds, cache_discovery=False)
        logger.info("gdoc_tools: Drive write service via service account")
        return _DRIVE_WRITE_SERVICE

    # OAuth fallback — alleen voor lokale ontwikkeling. Zie _get_docs_service() voor toelichting.
    if os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE") or os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        raise RuntimeError(
            "Service account env vars zijn gezet maar credentials konden niet worden geladen. "
            "Controleer GOOGLE_SERVICE_ACCOUNT_FILE of GOOGLE_SERVICE_ACCOUNT_JSON."
        )

    try:
        from update_gdoc import get_creds, CredentialsError
        creds = get_creds(raise_on_error=True)
        _DRIVE_WRITE_SERVICE = build("drive", "v3", credentials=creds, cache_discovery=False)
        logger.info("gdoc_tools: Drive write service via OAuth (lokale modus)")
        return _DRIVE_WRITE_SERVICE
    except Exception as e:
        raise RuntimeError(
            f"Geen geldige credentials voor Google Drive. "
            f"Op de VM: zet GOOGLE_SERVICE_ACCOUNT_FILE. Lokaal: draai setup_gdrive_auth.py. Fout: {e}"
        ) from e


def _get_or_create_werkdocumenten_folder() -> str:
    """Return the Drive folder ID for '00_Werkdocumenten', creating it if needed.

    This keeps Ainstein draft docs out of the curated source layer (01_Clients…05_Ainstein Knowledge Base).
    Thomas moves finalized proposals to 01_Clients/<naam>/Proposals manually.
    """
    global _WERKDOCUMENTEN_FOLDER_ID
    if _WERKDOCUMENTEN_FOLDER_ID is not None:
        return _WERKDOCUMENTEN_FOLDER_ID

    service = _get_drive_write_service()
    folder_name = "00_Werkdocumenten"

    # Check whether the folder already exists inside the AInstein root
    q = (
        f"name='{folder_name}' "
        f"and mimeType='application/vnd.google-apps.folder' "
        f"and '{_AINSTEIN_DRIVE_ROOT_ID}' in parents "
        f"and trashed=false"
    )
    results = service.files().list(
        q=q, fields="files(id,name)",
        supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute()
    files = results.get("files", [])
    if files:
        _WERKDOCUMENTEN_FOLDER_ID = files[0]["id"]
        logger.info("_get_or_create_werkdocumenten_folder: found %s", _WERKDOCUMENTEN_FOLDER_ID)
        return _WERKDOCUMENTEN_FOLDER_ID

    # Create it
    meta = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [_AINSTEIN_DRIVE_ROOT_ID],
    }
    folder = service.files().create(body=meta, fields="id", supportsAllDrives=True).execute()
    _WERKDOCUMENTEN_FOLDER_ID = folder["id"]
    logger.info("_get_or_create_werkdocumenten_folder: created %s", _WERKDOCUMENTEN_FOLDER_ID)
    return _WERKDOCUMENTEN_FOLDER_ID


def _find_folder_by_name(drive_service, parent_id: str, name: str, max_depth: int = 3) -> str | None:
    """BFS: return folder ID of first folder whose name contains `name` (case-insensitive)."""
    name_lower = name.lower().strip()
    queue = [(parent_id, 0)]
    while queue:
        current_id, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        try:
            res = drive_service.files().list(
                q=f"'{current_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="files(id,name)",
                supportsAllDrives=True, includeItemsFromAllDrives=True,
                pageSize=100,
            ).execute()
        except Exception as e:
            logger.warning("_find_folder_by_name: list failed at depth %d: %s", depth, e)
            continue
        for f in res.get("files", []):
            if name_lower in f["name"].lower():
                return f["id"]
            queue.append((f["id"], depth + 1))
    return None


def _get_or_create_subfolder(drive_service, parent_id: str, name: str) -> str:
    """Find or create a named subfolder inside parent_id. Returns folder ID."""
    safe_name = name.replace("'", "\\'")
    res = drive_service.files().list(
        q=f"name='{safe_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id)",
        supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    folder = drive_service.files().create(body=meta, fields="id", supportsAllDrives=True).execute()
    logger.info("_get_or_create_subfolder: created '%s' under %s", name, parent_id)
    return folder["id"]


def find_or_create_meetingnotes_folder(search_terms) -> str:
    """Return folder ID for {client}/Meetingnotes/, creating it if needed.

    search_terms: str or list[str] — tried in order until a client folder is found.
    Search: BFS under Drive root (max 3 levels deep), then find/create Meetingnotes/ inside.
    Fallback: 00_Werkdocumenten/Meetingnotes/.
    """
    drive = _get_drive_write_service()

    if isinstance(search_terms, str):
        search_terms = [search_terms]

    skip = {"onbekend", "unknown", ""}
    for term in search_terms:
        if not term or term.lower() in skip:
            continue
        client_folder_id = _find_folder_by_name(drive, _AINSTEIN_DRIVE_ROOT_ID, term, max_depth=3)
        if client_folder_id:
            folder_id = _get_or_create_subfolder(drive, client_folder_id, "Meetingnotes")
            logger.info("find_or_create_meetingnotes_folder: '%s'/Meetingnotes → %s", term, folder_id)
            return folder_id
        logger.info("find_or_create_meetingnotes_folder: '%s' niet gevonden", term)

    werkdoc = _get_or_create_werkdocumenten_folder()
    folder_id = _get_or_create_subfolder(drive, werkdoc, "Meetingnotes")
    logger.info("find_or_create_meetingnotes_folder: fallback → 00_Werkdocumenten/Meetingnotes → %s", folder_id)
    return folder_id


def create_doc_via_drive(title: str, content: str, folder_id: str) -> dict:
    """Create a Google Doc using the Drive API for creation (content upload as
    text/plain, Drive auto-converts to a Google Doc), then apply Minkowski brand
    formatting via the Docs API.

    Used by transcript_processor._create_meetingnote() — every Meetingnote goes
    through this path, NOT create_gdoc(). Historical note (fixed 2026-07-06):
    this function originally skipped formatting entirely because "the service
    account has Drive API access but not Docs API access" (see commit history).
    That constraint no longer holds — _get_service_account_creds() has requested
    both drive and documents scopes for a while — but nobody wired the formatting
    step back in, so every Meetingnote silently stayed unbranded (plain default
    Google Doc) while create_gdoc()-based docs (save_note, proposals) already got
    Minkowski heading colour/fonts. Found when Thomas asked directly whether
    Meeting Notes used the Minkowski identity — they did not.

    Returns {"doc_id": str, "url": str, "title": str}.
    """
    import io
    from googleapiclient.http import MediaIoBaseUpload

    drive_service = _get_drive_write_service()
    file_meta = {
        "name": title,
        "mimeType": "application/vnd.google-apps.document",
        "parents": [folder_id],
    }
    media = MediaIoBaseUpload(io.BytesIO(content.encode("utf-8")), mimetype="text/plain", resumable=False)
    doc = drive_service.files().create(
        body=file_meta,
        media_body=media,
        fields="id,webViewLink,name",
        supportsAllDrives=True,
    ).execute()
    url = doc.get("webViewLink", f"https://docs.google.com/document/d/{doc['id']}/edit")
    doc_id = doc["id"]
    logger.info("create_doc_via_drive: created '%s' in folder %s → %s", title, folder_id, doc_id)

    try:
        docs_service = _get_docs_service()
        _apply_basic_formatting(docs_service, doc_id)
    except Exception as e:
        logger.warning("create_doc_via_drive: brand formatting failed (non-fatal): %s", e)

    return {"doc_id": doc_id, "url": url, "title": doc["name"]}


def _is_table_separator(line: str) -> bool:
    """Return True for Markdown table separator rows like |---|---| or |:---:|."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return False
    inner = stripped.strip("|")
    return bool(inner) and "-" in inner and all(c in "|-: " for c in inner)


def _preprocess_content(content: str) -> str:
    """Pre-process proposal text before inserting into Google Docs.

    Strips Markdown table separator rows (|---|---|) — they add no readability
    value in a word-processor context. All other content is preserved verbatim,
    including # heading markers used by parse_proposal_sections() for PPTX export.
    """
    lines = content.split("\n")
    return "\n".join(line for line in lines if not _is_table_separator(line))


# Minkowski-merkwaarden, rechtstreeks geverifieerd tegen MK-new-brandbook.pptx
# (python-pptx-inspectie 2026-07-06 van het echte bestand, niet de tekst-cache —
# slide 1: kleurvlak + hex-label per kleur, slide 2: font-schaal 14/25/50 geannoteerd).
# Zelfde bron als pptx_builder.py:BRAND — hier ingezet voor Google Docs, die tot nu toe
# alleen generieke Google-kopstijlen kregen en geen Minkowski-kleur/font.
_BRAND_HEADING_COLOR_RGB = {"red": 0x28 / 255, "green": 0x70 / 255, "blue": 0x93 / 255}  # #287093
_BRAND_FONT_HEADING = "Helvetica Neue"
_BRAND_FONT_BODY = "Helvetica Neue Light"


def _apply_basic_formatting(service, doc_id: str) -> None:
    """Apply HEADING_1 / HEADING_2 paragraph styles + Minkowski brand kleur/font aan
    lines die met # / ## beginnen; body-tekst krijgt het Minkowski body-font.

    De # markers blijven in de tekst staan zodat parse_proposal_sections() de doc
    nog kan splitsen in PPTX-secties via plain-text Drive-export. Dit is de enige
    opmaak-functie die alle Google Docs doorlopen (save_note, create_report_doc.py,
    proposal-flow) — vóór deze wijziging kregen ze alleen Google's generieke
    kopstijlen, geen Minkowski-merkidentiteit (kleur, typografie).
    """
    doc = service.documents().get(documentId=doc_id).execute()
    body_content = doc.get("body", {}).get("content", [])

    requests = []
    for element in body_content:
        if "paragraph" not in element:
            continue
        start_idx = element.get("startIndex", 0)
        end_idx = element.get("endIndex", 0)
        para = element["paragraph"]

        text = "".join(
            run.get("textRun", {}).get("content", "")
            for run in para.get("elements", [])
            if "textRun" in run
        )

        named_style = None
        if text.startswith("## "):
            named_style = "HEADING_2"
        elif text.startswith("# "):
            named_style = "HEADING_1"

        if named_style:
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": start_idx, "endIndex": end_idx},
                    "paragraphStyle": {"namedStyleType": named_style},
                    "fields": "namedStyleType",
                }
            })
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": start_idx, "endIndex": end_idx},
                    "textStyle": {
                        "weightedFontFamily": {"fontFamily": _BRAND_FONT_HEADING},
                        "foregroundColor": {
                            "color": {"rgbColor": _BRAND_HEADING_COLOR_RGB}
                        },
                    },
                    "fields": "weightedFontFamily,foregroundColor",
                }
            })
        elif text.strip():
            # Body-tekst: alleen het font zetten, kleur ongemoeid laten — voorkomt
            # dat bestaande inline-kleuren (bv. een handmatige markering) verdwijnen.
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": start_idx, "endIndex": end_idx},
                    "textStyle": {
                        "weightedFontFamily": {"fontFamily": _BRAND_FONT_BODY},
                    },
                    "fields": "weightedFontFamily",
                }
            })

    if requests:
        service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": requests},
        ).execute()
        logger.info("_apply_basic_formatting: applied %d formatting request(s) in %s", len(requests), doc_id)


def _extract_doc_id(doc_id_or_url: str) -> str:
    """Accept a raw doc_id or a full Google Docs URL and return the doc_id."""
    # URL pattern: docs.google.com/document/d/<id>/...
    match = re.search(r"/document/d/([a-zA-Z0-9_-]+)", doc_id_or_url)
    if match:
        return match.group(1)
    return doc_id_or_url.strip()


# ---------------------------------------------------------------------------
# create_gdoc
# ---------------------------------------------------------------------------

def create_gdoc(title: str, content: str, parent_folder_id: str | None = "werkdocumenten") -> dict:
    """Create a new Google Doc and write initial content.

    By default saves to the '00_Werkdocumenten' working folder (separate from the
    curated source layer 01_Clients…05_Ainstein Knowledge Base). Pass parent_folder_id=None to
    keep the doc in Drive root, or pass an explicit folder ID.

    Returns {"doc_id": str, "url": str, "title": str}.
    Raises RuntimeError if credentials are missing or the API call fails.
    """
    docs_service = _get_docs_service()
    drive_service = _get_drive_write_service()

    # 1. Create empty doc
    doc = docs_service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    # 2. Move to working folder
    resolved_folder_id: str | None = None
    if parent_folder_id == "werkdocumenten":
        try:
            resolved_folder_id = _get_or_create_werkdocumenten_folder()
        except Exception as e:
            logger.warning("create_gdoc: could not resolve 00_Werkdocumenten folder: %s — doc stays in Drive root", e)
    elif parent_folder_id:
        resolved_folder_id = parent_folder_id

    if resolved_folder_id:
        try:
            file_meta = drive_service.files().get(fileId=doc_id, fields="parents", supportsAllDrives=True).execute()
            previous_parents = ",".join(file_meta.get("parents", []))
            drive_service.files().update(
                fileId=doc_id,
                addParents=resolved_folder_id,
                removeParents=previous_parents,
                fields="id,parents",
                supportsAllDrives=True,
            ).execute()
            logger.info("create_gdoc: moved %s → folder %s", doc_id, resolved_folder_id)
        except Exception as e:
            logger.warning("create_gdoc: could not move doc to folder: %s", e)

    # 3. Insert content (preprocessed — strips markdown table separator rows)
    if content:
        processed = _preprocess_content(content)
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [{"insertText": {"location": {"index": 1}, "text": processed}}]},
        ).execute()

        # 4. Apply heading styles (non-fatal — doc is usable without it)
        try:
            _apply_basic_formatting(docs_service, doc_id)
        except Exception as e:
            logger.warning("create_gdoc: heading formatting failed (non-fatal): %s", e)

    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    logger.info("create_gdoc: created '%s' → %s (folder: %s)", title, doc_id, resolved_folder_id or "root")
    return {"doc_id": doc_id, "url": url, "title": title}


# ---------------------------------------------------------------------------
# update_gdoc_section  (suggestion-mode helper + main function)
# ---------------------------------------------------------------------------

def update_gdoc_section(doc_id: str, old_text: str, new_text: str) -> dict:
    """Replace the first occurrence of old_text with new_text in the doc.

    Uses replaceAllText (case-sensitive, direct edit).
    Returns {"doc_id", "occurrences_changed", "status"}.
    Raises RuntimeError if the API call fails or credentials are missing.
    """
    doc_id = _extract_doc_id(doc_id)
    service = _get_docs_service()

    result = service.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "replaceAllText": {
                        "containsText": {"text": old_text, "matchCase": True},
                        "replaceText": new_text,
                    }
                }
            ]
        },
    ).execute()

    replies = result.get("replies", [{}])
    occurrences = replies[0].get("replaceAllText", {}).get("occurrencesChanged", 0) if replies else 0
    logger.info("update_gdoc_section: %d replacement(s) in %s", occurrences, doc_id)
    return {
        "doc_id": doc_id,
        "occurrences_changed": occurrences,
        "status": "ok" if occurrences > 0 else "not_found",
    }


# ---------------------------------------------------------------------------
# resolve_comment
# ---------------------------------------------------------------------------

def resolve_comment(doc_id: str, comment_id: str, reply_text: str = "") -> dict:
    """Add a reply to a Google Doc comment (does NOT auto-resolve it).

    Thomas resolves comments manually after reviewing the changes in the doc.
    This keeps comments visible so Thomas has full track-and-trace in Google Docs.

    Returns {"doc_id": str, "comment_id": str, "status": "replied"}.
    Raises RuntimeError on failure.
    """
    doc_id = _extract_doc_id(doc_id)
    service = _get_drive_write_service()

    body = {
        "content": reply_text if reply_text else "✅ Verwerkt door Ainstein.",
    }
    service.replies().create(
        fileId=doc_id,
        commentId=comment_id,
        fields="id",
        body=body,
    ).execute()
    logger.info("resolve_comment: added reply to comment %s in %s", comment_id, doc_id)

    return {"doc_id": doc_id, "comment_id": comment_id, "status": "replied"}


# ---------------------------------------------------------------------------
# get_doc_content
# ---------------------------------------------------------------------------

def get_doc_content(doc_id: str) -> str:
    """Export a Google Doc as plain text via the Drive export endpoint.

    Returns the document text. Raises RuntimeError if credentials are missing
    or the export fails.
    """
    doc_id = _extract_doc_id(doc_id)
    service = _get_drive_write_service()

    data = service.files().export(
        fileId=doc_id, mimeType="text/plain"
    ).execute()

    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return str(data) if data else ""
