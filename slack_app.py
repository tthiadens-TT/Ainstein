#!/usr/bin/env python3
"""
Ainstein Slack Bot — Minkowski commercial intelligence layer in Slack.

Setup:
    1. Create a Slack app at https://api.slack.com/apps
    2. Enable Socket Mode and generate an App-Level Token (xapp-...)
    3. Add Bot Token Scopes: app_mentions:read, chat:write, channels:history, im:history, im:write, im:read
    4. Enable Event Subscriptions: app_mention, message.im
    5. Install the app to your workspace
    6. Copy .env.example to .env and fill in the tokens
    7. Run: python slack_app.py

Usage in Slack:
    @Ainstein [your message]         — mention in any channel
    DM Ainstein directly             — private conversation
"""

import os
import re
import ssl
import sys
import threading
import tempfile
import traceback
import certifi


def _configure_ssl() -> None:
    """Force certifi bundle on macOS python.org builds so TLS handshakes work.

    NOTE: this MUST run before `App(token=...)` is constructed, because
    slack-bolt's App.__init__ does a live auth.test call. So we can't defer
    it to __main__ — it's called at module top. Kept in a function anyway
    so the side effects are explicit and grep-able, not scattered across
    module-level imports.
    """
    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
    os.environ["WEBSOCKET_CLIENT_CA_BUNDLE"] = certifi.where()
    ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())


_configure_ssl()

from dotenv import load_dotenv
import anthropic
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from agent import run_agent
from memory import load as mem_load, save as mem_save

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

_anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
_slack_bot_token = os.environ.get("SLACK_BOT_TOKEN", "").strip()

if not _anthropic_key:
    raise SystemExit("ANTHROPIC_API_KEY not set or empty in .env")
if not _slack_bot_token:
    raise SystemExit("SLACK_BOT_TOKEN not set or empty in .env")

print(f"ANTHROPIC_API_KEY loaded: {_anthropic_key[:12]}... (length {len(_anthropic_key)})")
print(f"SLACK_BOT_TOKEN loaded: {_slack_bot_token[:10]}... (length {len(_slack_bot_token)})")

app = App(token=_slack_bot_token)

_lock = threading.Lock()

ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=_anthropic_key, max_retries=1)


def _clean_text(text: str, bot_user_id: str) -> str:
    """Strip the bot mention and clean whitespace."""
    text = re.sub(rf"<@{bot_user_id}>", "", text)
    return text.strip()


def _detect_skill(text: str) -> str | None:
    """Auto-detect skill from message content."""
    t = text.lower()
    if any(w in t for w in ["opportunity", "lead", "brief", "prospect", "client ask"]):
        return "analyse_opportunity"
    if any(w in t for w in ["proposal", "voorstel", "draft", "offer", "pitch"]):
        return "build_proposal"
    if any(w in t for w in ["expert", "facilitator", "who should", "team", "match"]):
        return "match_experts"
    return None


def _run_and_reply(channel: str, thread_ts: str, user_text: str, say, skill: str | None = None):
    with _lock:
        messages = mem_load(thread_ts)

    messages.append({"role": "user", "content": user_text})
    if skill is None:
        skill = _detect_skill(user_text)

    try:
        response = run_agent(messages, ANTHROPIC_CLIENT, skill=skill)
    except Exception as e:
        try:
            fallback_messages = [{"role": "user", "content": (
                f"I tried to answer this question: '{user_text}'\n\n"
                f"But ran into a technical issue: {e}\n\n"
                "Please reflect on what you would need to answer this properly. "
                "What is missing from the source layer? What would make you more useful here?"
            )}]
            response = run_agent(fallback_messages, ANTHROPIC_CLIENT)
        except Exception as fallback_err:
            # Log both original and fallback failure so we never lose context
            print(
                f"[slack_app] fallback run_agent also failed: "
                f"{type(fallback_err).__name__}: {fallback_err}",
                file=sys.stderr,
                flush=True,
            )
            traceback.print_exc(file=sys.stderr)
            response = (
                "Ik kon deze vraag nu niet beantwoorden. "
                "Controleer of de juiste bestanden in de bronmappen staan en probeer het opnieuw."
            )

    mem_save(thread_ts, messages)
    print(f"[reply] posting {len(response)} chars to Slack", flush=True)
    _send_chunked(say, response, channel, thread_ts)
    print(f"[reply] done", flush=True)


def _send_chunked(say, text: str, channel: str, thread_ts: str, limit: int = 2900):
    """Split long responses into chunks so Slack never truncates them."""
    if len(text) <= limit:
        say(text=text, thread_ts=thread_ts, channel=channel, mrkdwn=True)
        return
    lines = text.split("\n")
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 1 > limit:
            say(text=chunk.strip(), thread_ts=thread_ts, channel=channel, mrkdwn=True)
            chunk = line + "\n"
        else:
            chunk += line + "\n"
    if chunk.strip():
        say(text=chunk.strip(), thread_ts=thread_ts, channel=channel, mrkdwn=True)


@app.event("app_mention")
def handle_mention(event, say, client):
    bot_info = client.auth_test()
    bot_user_id = bot_info["user_id"]

    raw_text = event.get("text", "")
    user_text = _clean_text(raw_text, bot_user_id)
    if not user_text:
        return

    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])

    # Acknowledge immediately
    say(text="_Searching source layer…_", thread_ts=thread_ts, channel=channel, mrkdwn=True)

    t = threading.Thread(
        target=_run_and_reply,
        args=(channel, thread_ts, user_text, say),
        daemon=True,
    )
    t.start()


def _slash_handler(skill: str, body, ack, say):
    ack()
    user_text = body.get("text", "").strip()
    channel = body["channel_id"]
    thread_ts = body.get("thread_ts", body.get("ts", channel))
    if not user_text:
        say(text=f"_Gebruik: `/{skill.replace('_',' ')} [jouw vraag of briefing]`_", channel=channel)
        return
    say(text="_Searching source layer…_", channel=channel, mrkdwn=True)
    t = threading.Thread(
        target=_run_and_reply,
        args=(channel, thread_ts, user_text, say, skill),
        daemon=True,
    )
    t.start()


@app.command("/analyse")
def cmd_analyse(body, ack, say):
    _slash_handler("analyse_opportunity", body, ack, say)


@app.command("/voorstel")
def cmd_voorstel(body, ack, say):
    _slash_handler("build_proposal", body, ack, say)


@app.command("/experts")
def cmd_experts(body, ack, say):
    _slash_handler("match_experts", body, ack, say)


_SLACK_FILE_HOSTS = {"files.slack.com", "slack-files.com"}


def _download_files(files: list) -> str:
    """Download and read Slack file attachments. Returns combined text."""
    from tools import _read_text
    from pathlib import Path
    from urllib.parse import urlparse
    import requests as _req

    parts = []
    for f in files:
        filename = f.get("name", "bestand")
        url = f.get("url_private_download") or f.get("url_private")
        if not url:
            continue
        try:
            host = urlparse(url).hostname or ""
            # Only attach the bot token when the URL is a known Slack file host.
            # Prevents token leakage if Slack ever returns a redirect-style URL.
            if host in _SLACK_FILE_HOSTS:
                headers = {"Authorization": f"Bearer {_slack_bot_token}"}
            else:
                print(
                    f"[slack_app] refusing to attach bot token to non-Slack host: {host}",
                    file=sys.stderr,
                    flush=True,
                )
                headers = {}
            r = _req.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            suffix = Path(filename).suffix.lower()
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(r.content)
                tmp_path = tmp.name
            content = _read_text(Path(tmp_path))
            os.unlink(tmp_path)
            parts.append(f"--- Bijlage: {filename} ---\n{content}")
        except Exception as e:
            parts.append(f"[Kon {filename} niet lezen: {e}]")
    return "\n\n".join(parts)


@app.event("message")
def handle_dm(event, say, client):
    # Only handle direct messages (channel type "im"), ignore bot messages
    if event.get("channel_type") != "im":
        return
    if event.get("bot_id"):
        return
    subtype = event.get("subtype", "")
    if subtype and subtype != "file_share":
        return

    files = event.get("files", [])
    caption = event.get("text", "").strip()

    if not files and not caption:
        return

    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])

    if files:
        say(text="_Bestand ontvangen, even lezen…_", thread_ts=thread_ts, channel=channel, mrkdwn=True)
        def process():
            file_content = _download_files(files)
            if not file_content:
                say(text="_Kon de bijlage(n) niet verwerken._", thread_ts=thread_ts, channel=channel, mrkdwn=True)
                return
            user_text = f"{caption}\n\n{file_content}".strip() if caption else file_content
            skill = _detect_skill(caption) if caption else None
            _run_and_reply(channel, thread_ts, user_text, say, skill=skill)
        threading.Thread(target=process, daemon=True).start()
    else:
        say(text="_Searching source layer…_", thread_ts=thread_ts, channel=channel, mrkdwn=True)
        threading.Thread(
            target=_run_and_reply,
            args=(channel, thread_ts, caption, say),
            daemon=True,
        ).start()


if __name__ == "__main__":
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        raise SystemExit("SLACK_APP_TOKEN not set. See .env.example.")
    handler = SocketModeHandler(app, app_token)
    print("Ainstein is running in Slack. Press Ctrl+C to stop.")
    handler.start()
