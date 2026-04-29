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
from feedback import (
    register_pending,
    pop_pending,
    has_pending,
    append_feedback,
)

# Slack reactions we treat as 👎 feedback triggers
_NEGATIVE_REACTIONS = {"thumbsdown", "-1", "x", "no_entry_sign"}

# Placeholder prefixes the bot posts during processing — never treat these
# as the "answer" when someone reacts to them.
_BOT_PLACEHOLDER_PREFIXES = (
    "_Searching source layer",
    "_Bestand ontvangen",
    "_Genoteerd",
    "_Dank voor de 👎",
    "_Gebruik:",
    "_Kon",
)

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
    """Auto-detect skill from message content. Order = specificity first."""
    t = text.lower()

    # debrief_to_messaging needs to win over plain 'debrief' — check first
    if "debrief" in t and any(w in t for w in ["messaging", "marketing", "glossary", "content opport"]):
        return "debrief_to_messaging"

    # Sales sub-skills
    if any(w in t for w in ["kwalifice", "qualify", "past dit", "is dit een fit"]):
        return "qualify_lead"
    if any(w in t for w in ["discovery", "call prep", "gesprek voorbereiden", "discovery vragen"]):
        return "prepare_discovery"
    if any(w in t for w in ["bezwaar", "bezwaren", "objection", "weerstand", "obstakel"]):
        return "map_objections"
    if any(w in t for w in ["debrief", "recap", "call notes", "transcriptie"]):
        return "client_discovery_debrief"

    # Marketing sub-skills (specificity first: asset words > action verbs > topic words)
    if any(w in t for w in ["linkedin", "artikel", "article", "nurture", "newsletter", "one-pager", "onepager", "content"]):
        return "create_content"
    if any(w in t for w in ["adapt messaging", "vertaal naar", "sector messaging", "audience messaging"]):
        return "adapt_messaging"
    # sharpen_positioning: action verb required, never bare topic word.
    # Match: explicit verbs (scherper/sharpen/aanscherpen), contiguous "scherp aan",
    # OR "scherp" co-occurring with "positioning"/"positionering" (catches Dutch
    # split-verb constructions like "scherp deze positionering aan").
    # Slash /positioning remains the unambiguous trigger for any sharpen intent.
    if (
        any(w in t for w in ["scherper", "sharpen", "aanscherpen", "scherp aan"])
        or ("scherp" in t and ("positioning" in t or "positionering" in t))
    ):
        return "sharpen_positioning"

    # Existing top-level skills
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


# Sales sub-skills
@app.command("/qualify")
def cmd_qualify(body, ack, say):
    _slash_handler("qualify_lead", body, ack, say)


@app.command("/discovery")
def cmd_discovery(body, ack, say):
    _slash_handler("prepare_discovery", body, ack, say)


@app.command("/objections")
def cmd_objections(body, ack, say):
    _slash_handler("map_objections", body, ack, say)


@app.command("/debrief")
def cmd_debrief(body, ack, say):
    _slash_handler("client_discovery_debrief", body, ack, say)


# Marketing sub-skills
@app.command("/positioning")
def cmd_positioning(body, ack, say):
    _slash_handler("sharpen_positioning", body, ack, say)


@app.command("/content")
def cmd_content(body, ack, say):
    _slash_handler("create_content", body, ack, say)


@app.command("/adapt")
def cmd_adapt(body, ack, say):
    _slash_handler("adapt_messaging", body, ack, say)


@app.command("/debrief-messaging")
def cmd_debrief_messaging(body, ack, say):
    _slash_handler("debrief_to_messaging", body, ack, say)


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
    user_id = event.get("user", "")

    # If this user has a pending feedback request in this thread, capture
    # their reply as feedback instead of dispatching to the agent.
    if caption and not files and user_id and has_pending(channel, user_id, thread_ts):
        state = pop_pending(channel, user_id, thread_ts)
        if state:
            user_name = None
            try:
                info = client.users_info(user=user_id)
                user_name = (
                    info.get("user", {}).get("real_name")
                    or info.get("user", {}).get("name")
                )
            except Exception as e:
                print(
                    f"[slack_app] users_info lookup failed ({e}); continuing with id only",
                    file=sys.stderr,
                    flush=True,
                )
            append_feedback(
                thread_ts=thread_ts,
                user_id=user_id,
                user_name=user_name,
                skill=None,
                bot_excerpt=state["bot_excerpt"],
                user_comment=caption,
            )
            say(
                text=(
                    "_Genoteerd. ✅ Opgeslagen in `07_Feedback/gaps.md` — "
                    "volgende vergelijkbare vraag komt dit in context._"
                ),
                thread_ts=thread_ts,
                channel=channel,
                mrkdwn=True,
            )
            return

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


@app.event("reaction_added")
def handle_reaction(event, client):
    """Capture 👎 on a bot answer and ask the user what could be better."""
    reaction = event.get("reaction", "")
    if reaction not in _NEGATIVE_REACTIONS:
        return

    item = event.get("item", {})
    if item.get("type") != "message":
        return

    channel = item.get("channel")
    message_ts = item.get("ts")
    user_id = event.get("user")
    if not channel or not message_ts or not user_id:
        return

    try:
        bot_user_id = client.auth_test()["user_id"]

        # Retrieve the message the user reacted to
        resp = client.conversations_history(
            channel=channel,
            latest=message_ts,
            inclusive=True,
            limit=1,
        )
        messages = resp.get("messages", [])
        if not messages:
            return
        msg = messages[0]

        # Only act on our own bot's messages
        msg_user = msg.get("user")
        msg_bot_id = msg.get("bot_id")
        if msg_user != bot_user_id and not msg_bot_id:
            return

        bot_text = msg.get("text", "") or ""
        if not bot_text.strip() or bot_text.startswith(_BOT_PLACEHOLDER_PREFIXES):
            # Ignore reactions on placeholders or empty text
            return

        thread_ts = msg.get("thread_ts") or message_ts

        register_pending(
            channel=channel,
            user_id=user_id,
            thread_ts=thread_ts,
            bot_message_ts=message_ts,
            bot_excerpt=bot_text,
        )

        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=(
                "_Dank voor de 👎. Wat had hier beter gekund? "
                "Antwoord in deze thread — één regel is genoeg. "
                "Komt terecht in `07_Feedback/gaps.md` zodat Ainstein er scherper van wordt._"
            ),
            mrkdwn=True,
        )
        print(
            f"[feedback] registered pending for user={user_id} thread={thread_ts}",
            flush=True,
        )
    except Exception as e:
        print(
            f"[slack_app] reaction_added handler failed: {type(e).__name__}: {e}",
            file=sys.stderr,
            flush=True,
        )
        traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        raise SystemExit("SLACK_APP_TOKEN not set. See .env.example.")
    handler = SocketModeHandler(app, app_token)
    print("Ainstein is running in Slack. Press Ctrl+C to stop.")
    handler.start()
