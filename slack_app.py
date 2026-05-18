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

import log_setup
from agent import run_agent
from memory import load as mem_load, save as mem_save

logger = log_setup.get_logger("slack_app")
from feedback import (
    register_pending,
    pop_pending,
    has_pending,
    capture_feedback,
    FEEDBACK_TYPES,
    TECHNICAL_CATEGORIES,
    QUALITATIVE_CATEGORIES,
    ALL_CATEGORIES,
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

logger.info("ANTHROPIC_API_KEY loaded: %s... (length %d)", _anthropic_key[:12], len(_anthropic_key))
logger.info("SLACK_BOT_TOKEN loaded: %s... (length %d)", _slack_bot_token[:10], len(_slack_bot_token))

app = App(token=_slack_bot_token)

_lock = threading.Lock()

ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=_anthropic_key, max_retries=1)

# Cheap, fast model for one-shot feedback classification — keeps latency low
# and cost predictable. Mismatch with main agent model is intentional.
_CLASSIFIER_MODEL = "claude-haiku-4-5-20251001"


def _classify_feedback(bot_excerpt: str, user_comment: str) -> tuple[str, str]:
    """Auto-label feedback into (type, category) using the fixed labelset.

    Falls back to a safe default on any failure — never raises into the
    Slack handler. The agent + Thomas can still correct in gaps.md later.
    """
    types_str = " | ".join(FEEDBACK_TYPES)
    tech_str = ", ".join(TECHNICAL_CATEGORIES)
    qual_str = ", ".join(QUALITATIVE_CATEGORIES)

    prompt = (
        "Classify the feedback below into ONE type and ONE category.\n\n"
        f"Type (pick one): {types_str}\n"
        f"  - technical = bot misunderstood, hallucinated, picked wrong source, "
        "or had a tool/file issue. Categories: " + tech_str + "\n"
        f"  - qualitative = answer was technically correct but commercially or "
        "qualitatively weak. Categories: " + qual_str + "\n\n"
        "Output EXACTLY two lines, no prose:\n"
        "Type: <type>\n"
        "Category: <category>\n\n"
        "--- BOT ANSWER (excerpt) ---\n"
        f"{bot_excerpt[:1500]}\n\n"
        "--- USER FEEDBACK ---\n"
        f"{user_comment[:1500]}\n"
    )

    try:
        resp = ANTHROPIC_CLIENT.messages.create(
            model=_CLASSIFIER_MODEL,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
    except Exception as e:
        logger.error("classifier failed: %s: %s", type(e).__name__, e)
        return "qualitative", "missende-inhoud"

    ftype, cat = "qualitative", "missende-inhoud"
    for line in text.splitlines():
        low = line.strip().lower()
        if low.startswith("type:"):
            val = low.split(":", 1)[1].strip()
            if val in FEEDBACK_TYPES:
                ftype = val
        elif low.startswith("category:"):
            val = line.split(":", 1)[1].strip()
            if val in ALL_CATEGORIES:
                cat = val
    return ftype, cat


def _clean_text(text: str, bot_user_id: str) -> str:
    """Strip the bot mention and clean whitespace."""
    text = re.sub(rf"<@{bot_user_id}>", "", text)
    return text.strip()


def _detect_skill(text: str) -> str | None:
    """Auto-detect skill from message content. Order = specificity first."""
    t = text.lower()

    # review_feedback — explicit phrasing only, never trigger on stray "feedback"
    if any(w in t for w in ["feedback review", "review feedback", "feedback patronen", "feedback-review"]):
        return "review_feedback"

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
    if any(w in t for w in ["verwerk de comments", "refine comments", "verwerk feedback", "update de doc", "refine_proposal"]):
        return "refine_proposal"
    if any(w in t for w in ["proposal", "voorstel", "draft", "offer", "pitch"]):
        return "build_proposal"
    # "team" and "match" are too generic on their own — require a companion word
    # to avoid false positives like "team meeting" or "plan matcht niet".
    _team_match = (
        ("team" in t and any(w in t for w in ["expert", "facilitator", "samenstell", "wie", "who", "bezetting"]))
        or ("match" in t and any(w in t for w in ["expert", "facilitator", "profiel", "wie past"]))
    )
    if any(w in t for w in ["expert", "facilitator", "who should"]) or _team_match:
        return "match_experts"
    return None


def _run_and_reply(channel: str, thread_ts: str, user_text: str, say, skill: str | None = None, user_id: str = ""):
    with _lock:
        messages = mem_load(thread_ts)

    messages.append({"role": "user", "content": user_text})
    if skill is None:
        skill = _detect_skill(user_text)

    try:
        response, trace = run_agent(messages, ANTHROPIC_CLIENT, skill=skill)
    except Exception as e:
        logger.exception("run_agent failed for thread=%s: %s", thread_ts, e)
        try:
            fallback_messages = [{"role": "user", "content": (
                f"I tried to answer this question: '{user_text}'\n\n"
                f"But ran into a technical issue: {e}\n\n"
                "Please reflect on what you would need to answer this properly. "
                "What is missing from the source layer? What would make you more useful here?"
            )}]
            response, trace = run_agent(fallback_messages, ANTHROPIC_CLIENT)
        except Exception as fallback_err:
            logger.exception("fallback run_agent also failed: %s", fallback_err)
            response = (
                "Ik kon deze vraag nu niet beantwoorden. "
                "Controleer of de juiste bestanden in de bronmappen staan en probeer het opnieuw."
            )
            trace = {}

    trace["thread_ts"] = thread_ts
    trace["channel"] = channel
    trace["user_id"] = user_id
    log_setup.append_decision_trace(trace)

    mem_save(thread_ts, messages)

    # Upload any files queued by tools (e.g. export_proposal_deck)
    from tools import get_pending_uploads
    for upload in get_pending_uploads():
        try:
            app.client.files_upload_v2(
                channel=channel,
                file=upload["path"],
                filename=upload["filename"],
                title=upload["title"],
                thread_ts=thread_ts,
            )
            logger.info("uploaded %s to thread=%s", upload["filename"], thread_ts)
        except Exception as _ue:
            logger.warning("file upload failed for %s: %s", upload["filename"], _ue)
        finally:
            try:
                os.unlink(upload["path"])
            except OSError:
                pass

    logger.info("posting %d chars to Slack thread=%s", len(response), thread_ts)
    _send_chunked(say, response, channel, thread_ts)
    logger.info("reply done thread=%s", thread_ts)


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
        kwargs={"user_id": event.get("user", "")},
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
        kwargs={"user_id": body.get("user_id", "")},
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


@app.command("/refine-comments")
def cmd_refine_comments(body, ack, say):
    """Process open comments on a Google Doc proposal draft."""
    _slash_handler("refine_proposal", body, ack, say)


@app.command("/export-deck")
def cmd_export_deck(body, ack, say):
    """Generate a Minkowski-branded PPTX from a Google Doc proposal."""
    ack()
    parts = body.get("text", "").strip().split(None, 1)
    if not parts:
        say(
            text="_Gebruik: `/export-deck [doc_id of doc_url] [klantnaam]`_",
            channel=body["channel_id"],
        )
        return

    doc_id_or_url = parts[0]
    client_name = parts[1].strip() if len(parts) > 1 else "Client"
    channel = body["channel_id"]

    say(text=f"_Generating Minkowski deck voor {client_name}…_", channel=channel, mrkdwn=True)

    t = threading.Thread(
        target=_build_and_upload_deck,
        args=(doc_id_or_url, client_name, channel),
        daemon=True,
    )
    t.start()


def _build_and_upload_deck(doc_id_or_url: str, client_name: str, channel: str) -> None:
    """Read a Google Doc, build a PPTX, and upload it to Slack."""
    try:
        from gdoc_tools import get_doc_content, _extract_doc_id
        from pptx_builder import build_proposal_deck, parse_proposal_sections

        doc_id = _extract_doc_id(doc_id_or_url)
        doc_text = get_doc_content(doc_id)
        if not doc_text.strip():
            app.client.chat_postMessage(
                channel=channel,
                text="⚠️ Document is leeg of kon niet worden gelezen.",
            )
            return

        sections = parse_proposal_sections(doc_text)
        if not sections:
            app.client.chat_postMessage(
                channel=channel,
                text=(
                    "⚠️ Geen secties gevonden in het document. "
                    "Zorg dat het voorstel koppen gebruikt (# Context, # Proposal Logic, etc.)."
                ),
            )
            return

        pptx_bytes = build_proposal_deck(sections, client_name=client_name)
        filename = f"Voorstel_{client_name.replace(' ', '_')}.pptx"

        app.client.files_upload_v2(
            channel=channel,
            content=pptx_bytes,
            filename=filename,
            title=f"Voorstel {client_name} — Minkowski",
        )

    except Exception as e:
        import traceback as _tb
        app.client.chat_postMessage(
            channel=channel,
            text=f"⚠️ PPTX genereren mislukt: {e}\n```{_tb.format_exc()[-800:]}```",
        )


@app.command("/feedback-review")
def cmd_feedback_review(body, ack, say):
    """Trigger the review_feedback skill. Empty input is allowed — the skill
    just reads gaps.md and proposes actions."""
    ack()
    user_text = body.get("text", "").strip() or "Doe een feedback review."
    channel = body["channel_id"]
    thread_ts = body.get("thread_ts", body.get("ts", channel))
    say(text="_Reviewing feedback patterns…_", channel=channel, mrkdwn=True)
    t = threading.Thread(
        target=_run_and_reply,
        args=(channel, thread_ts, user_text, say, "review_feedback"),
        daemon=True,
    )
    t.start()


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
                logger.warning("refusing to attach bot token to non-Slack host: %s", host)
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
    # Ignore bot's own messages and unsupported subtypes
    if event.get("bot_id"):
        return
    subtype = event.get("subtype", "")
    if subtype and subtype != "file_share":
        return

    channel_type = event.get("channel_type")
    files = event.get("files", [])
    caption = event.get("text", "").strip()

    if not files and not caption:
        return

    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])
    user_id = event.get("user", "")

    # Pending-feedback capture works in EVERY channel type (DM, public, private),
    # so a 👎 in a channel + reply-in-thread is just as valid as in a DM. Without
    # this, channel feedback was silently dropped because the rest of this
    # handler only dispatches DM messages to the agent.
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
                logger.warning("users_info lookup failed (%s); continuing with id only", e)
            ftype, cat = _classify_feedback(state["bot_excerpt"], caption)
            capture_feedback(
                thread_id=thread_ts,
                user_id=user_id,
                user_name=user_name,
                skill=None,
                bot_excerpt=state["bot_excerpt"],
                user_comment=caption,
                feedback_type=ftype,
                category=cat,
                source="slack",
            )
            say(
                text=(
                    f"_Genoteerd ✅ als `{ftype} / {cat}` in `07_Feedback/gaps.md`. "
                    "Auto-classified door Ainstein — corrigeer het label direct in "
                    "`gaps.md` als het niet klopt. Volgende vergelijkbare vraag "
                    "komt dit in context, en `/feedback-review` haalt patronen eruit._"
                ),
                thread_ts=thread_ts,
                channel=channel,
                mrkdwn=True,
            )
            return

    # In channels (public/private), normal chat is NOT auto-dispatched to the
    # agent — users address Ainstein via @mention there. Only DMs get the
    # full agent treatment for every message.
    if channel_type != "im":
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
            _run_and_reply(channel, thread_ts, user_text, say, skill=skill, user_id=user_id)
        threading.Thread(target=process, daemon=True).start()
    else:
        say(text="_Searching source layer…_", thread_ts=thread_ts, channel=channel, mrkdwn=True)
        threading.Thread(
            target=_run_and_reply,
            args=(channel, thread_ts, caption, say),
            kwargs={"user_id": user_id},
            daemon=True,
        ).start()


@app.event("reaction_added")
def handle_reaction(event, client):
    """Capture 👎 on a bot answer and ask the user what could be better."""
    reaction = event.get("reaction", "")
    item_type = event.get("item", {}).get("type", "?")
    logger.info(
        "reaction_added: emoji=%r item_type=%s user=%s channel=%s",
        reaction, item_type, event.get("user"), event.get("item", {}).get("channel"),
    )
    if reaction not in _NEGATIVE_REACTIONS:
        logger.debug("reaction_added ignored: %r not in %s", reaction, _NEGATIVE_REACTIONS)
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

        # Fast-path bot author check via event metadata — avoids fetching the
        # message just to filter out reactions on user messages.
        item_user = event.get("item_user")
        if item_user and item_user != bot_user_id:
            logger.debug("reaction_added ignored: item_user=%s is not our bot", item_user)
            return

        # Fetch the reacted-on message. We use conversations.replies (not
        # .history) because bot replies are posted with thread_ts even in DMs,
        # so they live in a thread — and .history returns only top-level
        # messages, not thread replies.
        msg = None
        try:
            resp = client.conversations_replies(
                channel=channel, ts=message_ts, limit=1, inclusive=True,
            )
            for m in resp.get("messages", []):
                if m.get("ts") == message_ts:
                    msg = m
                    break
        except Exception as e:
            logger.warning("reaction_added: conversations_replies failed: %s", e)

        # Fallback for true top-level messages (e.g. mentions in a channel):
        if msg is None:
            try:
                resp = client.conversations_history(
                    channel=channel, latest=message_ts, oldest=message_ts,
                    inclusive=True, limit=1,
                )
                cands = resp.get("messages", [])
                if cands and cands[0].get("ts") == message_ts:
                    msg = cands[0]
            except Exception as e:
                logger.warning("reaction_added: conversations_history fallback failed: %s", e)

        if msg is None:
            logger.warning("reaction_added ignored: could not retrieve message %s", message_ts)
            return

        # Confirm bot authorship from the fetched message too — defence in depth
        # for the case where item_user was missing.
        msg_user = msg.get("user")
        msg_bot_id = msg.get("bot_id")
        if msg_user != bot_user_id and not msg_bot_id:
            logger.debug(
                "reaction_added ignored: message from user=%s bot_id=%s, not our bot (%s)",
                msg_user, msg_bot_id, bot_user_id,
            )
            return

        bot_text = msg.get("text", "") or ""
        if not bot_text.strip() or bot_text.startswith(_BOT_PLACEHOLDER_PREFIXES):
            logger.debug("reaction_added ignored: placeholder/empty text (starts: %r)", bot_text[:40])
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
        logger.info("feedback pending registered for user=%s thread=%s", user_id, thread_ts)
    except Exception as e:
        logger.exception("reaction_added handler failed: %s: %s", type(e).__name__, e)


if __name__ == "__main__":
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        raise SystemExit("SLACK_APP_TOKEN not set. See .env.example.")
    handler = SocketModeHandler(app, app_token)
    logger.info("Ainstein is running in Slack. Press Ctrl+C to stop.")
    handler.start()
