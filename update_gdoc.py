#!/usr/bin/env python3
"""
Update the text content of an existing Google Doc.

Requires a token with 'documents' write scope.
If your current token only has drive.readonly, re-run setup_gdrive_auth.py
after updating SCOPES to include documents write scope.

Usage:
    python3 update_gdoc.py <document_id> <content_file.txt>
    python3 update_gdoc.py <document_id> --text "Direct text content"
"""

import sys
import argparse
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN = Path.home() / ".minkowski_gdrive_token.json"

REQUIRED_SCOPE = "https://www.googleapis.com/auth/documents"


def get_creds():
    if not TOKEN.exists():
        print(f"ERROR: No token at {TOKEN}. Run setup_gdrive_auth.py first.")
        sys.exit(1)
    creds = Credentials.from_authorized_user_file(str(TOKEN))
    if REQUIRED_SCOPE not in (creds.scopes or []):
        print(f"ERROR: Token missing scope '{REQUIRED_SCOPE}'.")
        print("Fix: update SCOPES in setup_gdrive_auth.py and re-run it.")
        print("     Add: 'https://www.googleapis.com/auth/documents'")
        sys.exit(1)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json())
    elif creds.expired:
        print("ERROR: OAuth token verlopen zonder refresh_token — draai setup_gdrive_auth.py opnieuw.")
        sys.exit(1)
    return creds


def clear_and_write(service, doc_id: str, content: str):
    """Replace all content in the doc with new text."""
    # Get current doc to find end index
    doc = service.documents().get(documentId=doc_id).execute()
    body = doc.get("body", {})
    content_list = body.get("content", [])

    end_index = 1
    for element in content_list:
        if "endIndex" in element:
            end_index = element["endIndex"]

    requests = []

    # Delete existing content (keep index 1, which is the start)
    if end_index > 2:
        requests.append({
            "deleteContentRange": {
                "range": {
                    "startIndex": 1,
                    "endIndex": end_index - 1
                }
            }
        })

    # Insert new content
    requests.append({
        "insertText": {
            "location": {"index": 1},
            "text": content
        }
    })

    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests}
    ).execute()

    print(f"OK — document {doc_id} updated.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("doc_id", help="Google Doc ID")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("content_file", nargs="?", help="Path to text file with new content")
    group.add_argument("--text", help="Direct text content")
    args = parser.parse_args()

    if args.content_file:
        content = Path(args.content_file).read_text()
    else:
        content = args.text

    creds = get_creds()
    service = build("docs", "v1", credentials=creds)
    clear_and_write(service, args.doc_id, content)


if __name__ == "__main__":
    main()
