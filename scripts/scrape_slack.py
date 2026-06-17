#!/usr/bin/env python3
"""
scrape_slack.py — Exporteer Slack-kanaalgeschiedenis naar Markdown-bestanden in Drive.

Aslander IA-principe: platte tekst (Markdown) per onafhankelijke bron (bakje).
Output: één Google Doc per kanaal per maand in 06_Marketing/_bronmateriaal/slack/

Gebruik:
    python3 scripts/scrape_slack.py [--channels C1 C2] [--since YYYY-MM-DD] [--jorgen-only]

Standaard: alle publieke kanalen, alle geschiedenis, alle auteurs.

Vereiste env vars (via .env):
    SLACK_BOT_TOKEN          — bot token met channels:history + channels:read
    GOOGLE_SERVICE_ACCOUNT_FILE of GOOGLE_SERVICE_ACCOUNT_JSON
    AINSTEIN_DRIVE_ROOT_ID   — Shared Drive ID (default: Minkowski AInstein)
"""

import argparse
import io
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Load .env from parent directory (repo root)
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass  # dotenv optional — env vars may already be set

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("scrape_slack")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SHARED_DRIVE_ID = os.environ.get("AINSTEIN_DRIVE_ROOT_ID", "0AFvBEDYKrnHbUk9PVA")
# User token geeft toegang tot alle kanalen waar Thomas lid van is (geen /invite nodig)
# Fallback naar bot token als user token niet aanwezig is
SLACK_TOKEN = os.environ.get("SLACK_USER_TOKEN") or os.environ.get("SLACK_BOT_TOKEN", "")

# Jörgen's Slack user ID — set via env or pass --jorgen-id flag
JORGEN_SLACK_ID = os.environ.get("JORGEN_SLACK_ID", "")

# Slack API rate limit: max 1 req/sec for conversations.history (Tier 3)
_API_SLEEP = 1.1


# ---------------------------------------------------------------------------
# Drive helpers
# ---------------------------------------------------------------------------

def _get_drive_service():
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    sa_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    _tmp = None

    if sa_json:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(sa_json)
            _tmp = f.name
        sa_file = _tmp

    if not sa_file or not Path(sa_file).exists():
        log.error("Geen service account. Zet GOOGLE_SERVICE_ACCOUNT_FILE of GOOGLE_SERVICE_ACCOUNT_JSON.")
        sys.exit(1)

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        creds = service_account.Credentials.from_service_account_file(
            sa_file, scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    finally:
        if _tmp:
            os.unlink(_tmp)


def _get_or_create_folder(service, name: str, parent_id: str) -> str:
    res = service.files().list(
        q=(
            f"'{parent_id}' in parents and name='{name}' "
            f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
        ),
        fields="files(id)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    created = service.files().create(body=meta, fields="id", supportsAllDrives=True).execute()
    log.info("Map aangemaakt: %s", name)
    return created["id"]


def _upload_markdown(service, title: str, content: str, folder_id: str) -> str:
    """Upload Markdown als plain-text .md bestand. Overschrijft bestaand bestand met zelfde naam.

    Aslander IA-principe: plain text is de universele taal — geen Google Doc conversie.
    """
    from googleapiclient.http import MediaIoBaseUpload

    md_title = title if title.endswith(".md") else f"{title}.md"

    # Check of er al een bestand met deze naam bestaat
    res = service.files().list(
        q=f"'{folder_id}' in parents and name='{md_title}' and trashed=false",
        fields="files(id,name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    existing = res.get("files", [])

    media = MediaIoBaseUpload(
        io.BytesIO(content.encode("utf-8")), mimetype="text/plain", resumable=False
    )

    if existing:
        doc = service.files().update(
            fileId=existing[0]["id"],
            media_body=media,
            fields="id,webViewLink",
            supportsAllDrives=True,
        ).execute()
        log.info("Bijgewerkt: %s", md_title)
    else:
        meta = {
            "name": md_title,
            "mimeType": "text/plain",
            "parents": [folder_id],
        }
        doc = service.files().create(
            body=meta, media_body=media, fields="id,webViewLink", supportsAllDrives=True
        ).execute()
        log.info("Aangemaakt: %s", md_title)

    return doc.get("webViewLink", "")


def _resolve_folder_chain(service, root_id: str, *names: str) -> str:
    """Maak een keten van mappen aan (root → naam1 → naam2 → ...) en geef het laatste ID terug."""
    current = root_id
    for name in names:
        current = _get_or_create_folder(service, name, current)
    return current


# ---------------------------------------------------------------------------
# Slack helpers
# ---------------------------------------------------------------------------

def _slack_client():
    if not SLACK_TOKEN:
        log.error("SLACK_BOT_TOKEN niet gevonden in .env")
        sys.exit(1)
    from slack_sdk import WebClient
    return WebClient(token=SLACK_TOKEN)


def _list_public_channels(client) -> list[dict]:
    """Haal alle publieke kanalen op (gepagineerd)."""
    channels = []
    cursor = None
    while True:
        kwargs = {"types": "public_channel", "limit": 200, "exclude_archived": True}
        if cursor:
            kwargs["cursor"] = cursor
        resp = client.conversations_list(**kwargs)
        channels.extend(resp["channels"])
        cursor = resp.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            break
        time.sleep(_API_SLEEP)
    return channels


def _fetch_history(client, channel_id: str, oldest: float = 0.0) -> list[dict]:
    """Haal alle berichten op voor een kanaal (gepagineerd, inclusief thread-replies)."""
    messages = []
    cursor = None
    while True:
        kwargs = {
            "channel": channel_id,
            "limit": 200,
            "oldest": str(oldest) if oldest else "0",
        }
        if cursor:
            kwargs["cursor"] = cursor
        try:
            resp = client.conversations_history(**kwargs)
        except Exception as exc:
            log.warning("conversations_history mislukt voor %s: %s", channel_id, exc)
            break
        msgs = resp.get("messages", [])
        for msg in msgs:
            if msg.get("thread_ts") and msg.get("reply_count", 0) > 0:
                replies = _fetch_replies(client, channel_id, msg["thread_ts"])
                msg["_replies"] = replies
            messages.append(msg)
        cursor = resp.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            break
        time.sleep(_API_SLEEP)
    return messages


def _fetch_replies(client, channel_id: str, thread_ts: str) -> list[dict]:
    try:
        resp = client.conversations_replies(channel=channel_id, ts=thread_ts, limit=200)
        time.sleep(_API_SLEEP)
        return resp.get("messages", [])[1:]  # skip parent
    except Exception as exc:
        log.warning("conversations_replies mislukt: %s", exc)
        return []


def _resolve_user_names(client, user_ids: set) -> dict[str, str]:
    """Zet Slack user IDs om naar weergavenamen."""
    names = {}
    for uid in user_ids:
        try:
            resp = client.users_info(user=uid)
            profile = resp["user"]["profile"]
            names[uid] = profile.get("display_name") or profile.get("real_name") or uid
            time.sleep(0.5)
        except Exception:
            names[uid] = uid
    return names


# ---------------------------------------------------------------------------
# Markdown formatting
# ---------------------------------------------------------------------------

def _ts_to_dt(ts: str) -> datetime:
    return datetime.fromtimestamp(float(ts), tz=timezone.utc)


def _format_messages_as_markdown(
    messages: list[dict],
    channel_name: str,
    year_month: str,
    user_names: dict,
    jorgen_id: str,
) -> str:
    lines = [
        f"# Slack — #{channel_name} — {year_month}",
        f"_Bron: Slack workspace Minkowski | Geëxporteerd op {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')}_",
        f"_Bakje: slack/{channel_name} | Gebruik dit bestand als onafhankelijke databron_",
        "",
    ]

    for msg in sorted(messages, key=lambda m: float(m.get("ts", 0))):
        if msg.get("subtype"):
            continue  # skip join/leave/bot berichten
        ts = msg.get("ts", "")
        dt = _ts_to_dt(ts).strftime("%Y-%m-%d %H:%M")
        uid = msg.get("user", "")
        name = user_names.get(uid, uid or "bot")
        text = msg.get("text", "").strip()
        if not text:
            continue

        # Jörgen's berichten krijgen een markering zodat de extractie-agent ze zwaarder weegt
        prefix = "> [Jörgen] " if (jorgen_id and uid == jorgen_id) else ""
        lines.append(f"**{dt} — {name}**")
        for line in text.split("\n"):
            lines.append(f"{prefix}{line}" if prefix else line)

        # Thread-replies ingesprongen weergeven
        for reply in msg.get("_replies", []):
            r_uid = reply.get("user", "")
            r_name = user_names.get(r_uid, r_uid)
            r_text = reply.get("text", "").strip()
            r_dt = _ts_to_dt(reply.get("ts", ts)).strftime("%H:%M")
            r_prefix = "  > [Jörgen] " if (jorgen_id and r_uid == jorgen_id) else "  > "
            if r_text:
                lines.append(f"  > _{r_dt} {r_name}:_")
                for rline in r_text.split("\n"):
                    lines.append(f"{r_prefix}{rline}")

        lines.append("")

    return "\n".join(lines)


def _group_by_month(messages: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for msg in messages:
        ts = msg.get("ts", "")
        if ts:
            ym = _ts_to_dt(ts).strftime("%Y-%m")
            groups[ym].append(msg)
    return dict(groups)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Slack → Markdown → Drive scraper")
    parser.add_argument("--channels", nargs="*", help="Kanaal-IDs om te scrapen (default: alle publieke)")
    parser.add_argument("--since", help="Startdatum YYYY-MM-DD (default: alles)")
    parser.add_argument("--jorgen-id", help="Jörgens Slack user ID voor markering (overschrijft JORGEN_SLACK_ID)")
    parser.add_argument("--dry-run", action="store_true", help="Geen upload — print Markdown naar stdout")
    args = parser.parse_args()

    jorgen_id = args.jorgen_id or JORGEN_SLACK_ID

    oldest_ts = 0.0
    if args.since:
        oldest_ts = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()

    client = _slack_client()
    drive = None if args.dry_run else _get_drive_service()

    # Bepaal doelmap in Drive: 06_Marketing/_bronmateriaal/slack
    slack_folder_id = None
    if drive:
        marketing_folder = _resolve_folder_chain(drive, SHARED_DRIVE_ID, "06_Marketing")
        bronmateriaal_folder = _resolve_folder_chain(drive, marketing_folder, "_bronmateriaal")
        slack_folder_id = _resolve_folder_chain(drive, bronmateriaal_folder, "slack")
        log.info("Doelmap in Drive gereed: 06_Marketing/_bronmateriaal/slack")

    # Bepaal kanalen
    if args.channels:
        channels = [{"id": cid, "name": cid} for cid in args.channels]
    else:
        log.info("Kanalen ophalen...")
        channels = _list_public_channels(client)
        log.info("%d publieke kanalen gevonden", len(channels))

    for ch in channels:
        ch_id = ch["id"]
        ch_name = ch.get("name", ch_id)
        log.info("Kanaal scrapen: #%s (%s)", ch_name, ch_id)

        messages = _fetch_history(client, ch_id, oldest_ts)
        if not messages:
            log.info("  Geen berichten gevonden — overgeslagen")
            continue

        # Verzamel alle user IDs voor naamsresolutie
        user_ids = {m.get("user") for m in messages if m.get("user")}
        for m in messages:
            for r in m.get("_replies", []):
                if r.get("user"):
                    user_ids.add(r["user"])
        user_names = _resolve_user_names(client, user_ids)

        monthly_groups = _group_by_month(messages)
        for year_month, msgs in sorted(monthly_groups.items()):
            title = f"slack_{ch_name}_{year_month}"
            content = _format_messages_as_markdown(msgs, ch_name, year_month, user_names, jorgen_id)

            if args.dry_run:
                print(f"\n{'='*60}\n{title}\n{'='*60}")
                print(content[:2000])
            else:
                _upload_markdown(drive, title, content, slack_folder_id)
                time.sleep(0.5)

        log.info("  %d berichten in %d maanden", len(messages), len(monthly_groups))

    log.info("Klaar.")


if __name__ == "__main__":
    main()
