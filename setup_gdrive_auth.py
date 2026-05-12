#!/usr/bin/env python3
"""
One-time setup: authorise the Minkowski bot to read and write Google Docs/Sheets/Slides
and to resolve comments on proposal documents.

Prerequisite — done once in Google Cloud Console:
  1. Create a project at https://console.cloud.google.com (or reuse one).
  2. APIs & Services → Library → enable "Google Drive API".
  3. APIs & Services → OAuth consent screen → set user type to "External",
     fill in app name, your email, scopes (none needed at this step), and
     add yourself as a Test User.
  4. APIs & Services → Credentials → Create OAuth client ID → "Desktop app".
  5. Download the JSON and save it to:
        ~/.minkowski_gdrive_credentials.json

Then run this script once:
        .venv/bin/python setup_gdrive_auth.py

It opens a browser, you grant Drive + Docs access, and a refresh token is
written to ~/.minkowski_gdrive_token.json. The bot picks it up automatically.
"""
from pathlib import Path
import sys

CREDS = Path.home() / ".minkowski_gdrive_credentials.json"
TOKEN = Path.home() / ".minkowski_gdrive_token.json"
SCOPES = [
    "https://www.googleapis.com/auth/drive",        # Drive lezen + schrijven (o.a. comments resolven)
    "https://www.googleapis.com/auth/documents",    # Google Docs inhoud bewerken
]


def main() -> int:
    if not CREDS.exists():
        print(f"ERROR: {CREDS} not found.")
        print("See the docstring at the top of this file for setup steps.")
        return 1

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ERROR: google-auth-oauthlib not installed. Run:")
        print("  .venv/bin/python -m pip install -r requirements.txt")
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN.write_text(creds.to_json())
    print(f"OK — token written to {TOKEN}")
    print("The bot can now resolve .gdoc / .gsheet / .gslides files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
