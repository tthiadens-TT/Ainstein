"""
Google Docs write operations for Ainstein.

Provides: create_gdoc, update_gdoc_section, resolve_comment, get_doc_content.
All functions raise RuntimeError on failure so callers can surface meaningful
error messages rather than silently returning None.

Credentials: imports get_creds() from update_gdoc.py (OAuth token with
both drive + documents write scope). Run setup_gdrive_auth.py once to
issue/refresh the token with the correct scopes.
"""

import logging
import os
import re

logger = logging.getLogger("gdoc_tools")

_DOCS_SERVICE = None
_DRIVE_WRITE_SERVICE = None

# Google Drive folder ID for the AInstein root (contains 01_Proposals … 07_Feedback)
_AINSTEIN_DRIVE_ROOT_ID = os.environ.get(
    "AINSTEIN_DRIVE_ROOT_ID", "1ziMd8Zmhgpqq_iHyoz3-59_KwL7kbm7e"
)
# Cached working-folder ID — resolved lazily on first create_gdoc() call
_WERKDOCUMENTEN_FOLDER_ID: str | None = None


def _get_service_account_creds():
    """Return service account credentials when available (VM/server mode).

    Tries GOOGLE_SERVICE_ACCOUNT_FILE first, then GOOGLE_SERVICE_ACCOUNT_JSON.
    Returns None when neither is set (local OAuth mode).
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

    # Prefer service account (VM/server) over OAuth token (local)
    sa_creds = _get_service_account_creds()
    if sa_creds:
        _DOCS_SERVICE = build("docs", "v1", credentials=sa_creds, cache_discovery=False)
        logger.info("gdoc_tools: Docs service initialised via service account")
        return _DOCS_SERVICE

    from update_gdoc import get_creds, CredentialsError
    try:
        creds = get_creds(raise_on_error=True)
        _DOCS_SERVICE = build("docs", "v1", credentials=creds, cache_discovery=False)
        return _DOCS_SERVICE
    except CredentialsError as e:
        raise RuntimeError(str(e)) from e


def _get_drive_write_service():
    """Drive v3 client with write scope (for comment operations)."""
    global _DRIVE_WRITE_SERVICE
    if _DRIVE_WRITE_SERVICE is not None:
        return _DRIVE_WRITE_SERVICE
    from googleapiclient.discovery import build

    # Prefer service account (VM/server) over OAuth token (local)
    sa_creds = _get_service_account_creds()
    if sa_creds:
        _DRIVE_WRITE_SERVICE = build("drive", "v3", credentials=sa_creds, cache_discovery=False)
        logger.info("gdoc_tools: Drive write service initialised via service account")
        return _DRIVE_WRITE_SERVICE

    from update_gdoc import get_creds, CredentialsError
    try:
        creds = get_creds(raise_on_error=True)
        _DRIVE_WRITE_SERVICE = build("drive", "v3", credentials=creds, cache_discovery=False)
        return _DRIVE_WRITE_SERVICE
    except CredentialsError as e:
        raise RuntimeError(str(e)) from e


def _get_or_create_werkdocumenten_folder() -> str:
    """Return the Drive folder ID for '00_Werkdocumenten', creating it if needed.

    This keeps Ainstein draft docs out of the curated source layer (01_Proposals…07_Feedback).
    Thomas moves finalized proposals to 01_Proposals manually.
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
    results = service.files().list(q=q, fields="files(id,name)").execute()
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
    folder = service.files().create(body=meta, fields="id").execute()
    _WERKDOCUMENTEN_FOLDER_ID = folder["id"]
    logger.info("_get_or_create_werkdocumenten_folder: created %s", _WERKDOCUMENTEN_FOLDER_ID)
    return _WERKDOCUMENTEN_FOLDER_ID


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


def _apply_basic_formatting(service, doc_id: str) -> None:
    """Apply HEADING_1 / HEADING_2 paragraph styles to lines that start with # / ##.

    The # markers are kept in the text so parse_proposal_sections() can still
    split the doc into PPTX sections via plain-text Drive export. Heading styles
    make the document structure visually clear in Google Docs without touching content.
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

    if requests:
        service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": requests},
        ).execute()
        logger.info("_apply_basic_formatting: applied %d heading style(s) in %s", len(requests), doc_id)


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
    curated source layer 01_Proposals…07_Feedback). Pass parent_folder_id=None to
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
            file_meta = drive_service.files().get(fileId=doc_id, fields="parents").execute()
            previous_parents = ",".join(file_meta.get("parents", []))
            drive_service.files().update(
                fileId=doc_id,
                addParents=resolved_folder_id,
                removeParents=previous_parents,
                fields="id,parents",
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
