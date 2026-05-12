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
import re
from pathlib import Path

logger = logging.getLogger("gdoc_tools")

_DOCS_SERVICE = None
_DRIVE_WRITE_SERVICE = None


def _get_docs_service():
    global _DOCS_SERVICE
    if _DOCS_SERVICE is not None:
        return _DOCS_SERVICE
    from update_gdoc import get_creds, CredentialsError
    from googleapiclient.discovery import build
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
    from update_gdoc import get_creds, CredentialsError
    from googleapiclient.discovery import build
    try:
        creds = get_creds(raise_on_error=True)
        _DRIVE_WRITE_SERVICE = build("drive", "v3", credentials=creds, cache_discovery=False)
        return _DRIVE_WRITE_SERVICE
    except CredentialsError as e:
        raise RuntimeError(str(e)) from e


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

def create_gdoc(title: str, content: str) -> dict:
    """Create a new Google Doc and write initial content.

    Returns {"doc_id": str, "url": str, "title": str}.
    Raises RuntimeError if credentials are missing or the API call fails.
    """
    service = _get_docs_service()

    # Create empty doc
    doc = service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    # Write initial content
    if content:
        service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
        ).execute()

    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    logger.info("create_gdoc: created '%s' → %s", title, doc_id)
    return {"doc_id": doc_id, "url": url, "title": title}


# ---------------------------------------------------------------------------
# update_gdoc_section
# ---------------------------------------------------------------------------

def update_gdoc_section(doc_id: str, old_text: str, new_text: str) -> dict:
    """Replace the first occurrence of old_text with new_text in the doc.

    Uses replaceAllText (case-sensitive). Returns the number of replacements.
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
    """Mark a Google Doc comment as resolved and optionally add a reply.

    Adds the reply first (if provided), then marks the comment resolved.
    Returns {"doc_id": str, "comment_id": str, "status": "resolved"}.
    Raises RuntimeError on failure.
    """
    doc_id = _extract_doc_id(doc_id)
    service = _get_drive_write_service()

    if reply_text:
        service.comments().replies().create(
            fileId=doc_id,
            commentId=comment_id,
            fields="id",
            body={"content": reply_text},
        ).execute()
        logger.info("resolve_comment: added reply to comment %s", comment_id)

    service.comments().update(
        fileId=doc_id,
        commentId=comment_id,
        fields="id,resolved",
        body={"resolved": True},
    ).execute()
    logger.info("resolve_comment: resolved comment %s in %s", comment_id, doc_id)

    return {"doc_id": doc_id, "comment_id": comment_id, "status": "resolved"}


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
