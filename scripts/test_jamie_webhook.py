#!/usr/bin/env python3
"""Stuur een synthetische Jamie-payload naar de live webhook.

Gebruik:
    cd ~/Ainstein
    python3 scripts/test_jamie_webhook.py

Vereisten: JAMIE_WEBHOOK_SECRET in .env (of leeg laten als de bot zonder secret draait).
"""

import hashlib
import hmac
import json
import os
import time
import urllib.request

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

WEBHOOK_URL = "https://ainstein.duckdns.org/webhooks/jamie"
SECRET = os.environ.get("JAMIE_WEBHOOK_SECRET", "").strip()

PAYLOAD = {
    "metadata": {
        "id": f"test-meetingnote-{int(time.time())}",
    },
    "data": {
        "title": "Test — kennismaking met potentiële klant",
        "startTime": "2026-06-26T14:00:00+02:00",
        "participants": [
            {"name": "Thomas Thiadens", "email": "thomas@minkowski.org"},
            {"name": "Anna de Vries", "email": "anna.devries@test-bedrijf.nl"},
        ],
        "summary": {
            "markdown": (
                "Thomas en Anna spraken over de uitdagingen bij Test BV. "
                "Anna is HR-directeur en merkt dat het middenmanagement moeite heeft met de transitie "
                "naar hybride werken. Medewerkers missen structuur en richting. "
                "Thomas heeft een korte introductie gegeven van Minkowski's aanpak rondom "
                "leiderschapsontwikkeling en futures thinking. Anna reageerde positief en wil een voorstel zien."
            )
        },
        "tasks": [
            {
                "content": "Thomas stuurt een voorstel op maat voor Test BV",
                "assignee": "Thomas",
            },
            {
                "content": "Anna bespreekt intern of er budget is voor Q3",
                "assignee": "Anna",
            },
            {
                "content": "Thomas plant een vervolggesprek in met Anna en haar manager",
                "assignee": "Thomas",
            },
        ],
        # Geen transcript — conform echte Jamie-payload
    },
}

body = json.dumps(PAYLOAD).encode("utf-8")
timestamp = str(int(time.time()))

headers = {
    "Content-Type": "application/json",
}

if SECRET:
    signed = f"{timestamp}.".encode() + body
    sig = hmac.new(SECRET.encode(), signed, hashlib.sha256).hexdigest()
    headers["x-jamie-signature"] = f"t={timestamp},v0={sig}"
    print(f"Signature toegevoegd (secret aanwezig)")
else:
    print("Geen JAMIE_WEBHOOK_SECRET — payload wordt zonder handtekening verstuurd")

print(f"Sturen naar: {WEBHOOK_URL}")
print(f"Meeting ID: {PAYLOAD['metadata']['id']}")
print(f"Titel: {PAYLOAD['data']['title']}")

import ssl
ctx = ssl.create_default_context()
ctx.load_verify_locations(cafile=__import__("certifi").where())

req = urllib.request.Request(WEBHOOK_URL, data=body, headers=headers, method="POST")
try:
    with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
        print(f"Status: {resp.status}")
        print(f"Response: {resp.read().decode()}")
        print("\nPayload verstuurd. Check #ainstein-status en je DM in Slack.")
except Exception as e:
    print(f"Fout: {e}")
