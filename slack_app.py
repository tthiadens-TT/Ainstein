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

import io
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

import time
from collections import defaultdict, deque

import log_setup
from agent import run_agent
from memory import load as mem_load, save as mem_save

logger = log_setup.get_logger("slack_app")
from feedback import (
    register_pending,
    pop_pending,
    has_pending,
    capture_feedback,
    increment_and_check,
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

# ---------------------------------------------------------------------------
# Rate limiting — max calls per user per hour
# ---------------------------------------------------------------------------
_RATE_LIMIT_MAX = int(os.environ.get("RATE_LIMIT_MAX", "10"))
_RATE_LIMIT_WINDOW = 3600  # seconden (1 uur)
_user_call_times: dict[str, deque] = defaultdict(lambda: deque())
_rate_lock = threading.Lock()


def _is_rate_limited(user_id: str) -> bool:
    """Geeft True als de user het limiet heeft bereikt, anders False.

    Bijwerking: logt de huidige call-timestamp voor de user.
    """
    if not user_id:
        return False
    now = time.monotonic()
    with _rate_lock:
        timestamps = _user_call_times[user_id]
        # Verwijder calls buiten het tijdvenster
        while timestamps and now - timestamps[0] > _RATE_LIMIT_WINDOW:
            timestamps.popleft()
        if len(timestamps) >= _RATE_LIMIT_MAX:
            return True
        timestamps.append(now)
        return False


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
    # "content" is intentionally excluded — too generic (e.g. "content van dit voorstel").
    # Trigger on explicit format words, or on "content" + an action verb.
    if any(w in t for w in ["linkedin", "artikel", "article", "nurture", "newsletter", "one-pager", "onepager"]):
        return "create_content"
    if "content" in t and any(w in t for w in ["schrijf", "maak", "genereer", "create", "post", "publiceer"]):
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

    # DVV/AUB quality check — must come before proposal/content triggers to avoid false routing
    if any(w in t for w in ["dvv", "check op dvv", "dvv check", "dvv-check", "beoordeel op dvv",
                             "duidelijk volledig verleidelijk"]):
        return "dvv_check"

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


def _run_and_reply(channel: str, thread_ts: str | None, user_text: str, say, skill: str | None = None, user_id: str = ""):
    # Rate limiting — geef vriendelijke melding als user limiet bereikt heeft
    if _is_rate_limited(user_id):
        logger.warning("Rate limit bereikt voor user=%s", user_id)
        _send_chunked(
            say,
            f"_Je hebt het maximum van {_RATE_LIMIT_MAX} verzoeken per uur bereikt. Probeer het over een tijdje opnieuw._",
            channel,
            thread_ts,
        )
        return

    # When a slash command has no thread context, use channel as memory key so
    # the conversation history is still persisted (one conversation per channel).
    mem_key = thread_ts or channel
    with _lock:
        messages = mem_load(mem_key)

    messages.append({"role": "user", "content": user_text})
    if skill is None:
        # For multi-modal content lists, extract text blocks for skill detection
        if isinstance(user_text, list):
            _text_for_skill = " ".join(
                b.get("text", "") for b in user_text if isinstance(b, dict) and b.get("type") == "text"
            )
        else:
            _text_for_skill = user_text
        skill = _detect_skill(_text_for_skill)

    try:
        response, trace = run_agent(messages, ANTHROPIC_CLIENT, skill=skill)
    except Exception as e:
        logger.exception("run_agent failed for thread=%s: %s", thread_ts, e)
        # Context-too-long: the history itself is the problem — don't append more to it.
        # Reset to just the current question so the fallback can at least respond.
        _is_context_overflow = (
            isinstance(e, anthropic.BadRequestError)
            and "prompt is too long" in str(e)
        )
        if _is_context_overflow:
            logger.warning("context overflow — resetting to bare question for fallback (thread=%s)", thread_ts)
            fallback_messages = [{"role": "user", "content": user_text}]
        else:
            # Keep thread history in the fallback so the agent knows what was asked.
            # Do NOT include the raw exception in the prompt — brain.md: never expose
            # technical error details to end users. The exception is already in server logs.
            fallback_messages = messages + [{"role": "user", "content": (
                "Er was een technisch probleem bij het beantwoorden van de vorige vraag.\n\n"
                "Laat de gebruiker weten dat er iets mis ging en wat ze nu het best kunnen doen."
            )}]
        try:
            response, trace = run_agent(fallback_messages, ANTHROPIC_CLIENT)
        except Exception as fallback_err:
            logger.exception("fallback run_agent also failed: %s", fallback_err)
            response = (
                "Ik kon deze vraag nu niet beantwoorden. "
                "Controleer of de juiste bestanden in de bronmappen staan en probeer het opnieuw."
            )
            trace = {}
            _notify_failure(fallback_err, channel, thread_ts)

    trace["thread_ts"] = thread_ts
    trace["channel"] = channel
    trace["user_id"] = user_id
    log_setup.append_decision_trace(trace)

    # Persist bot response so future messages in this thread have full context.
    messages.append({"role": "assistant", "content": response})
    # Trim before saving so the DB doesn't accumulate bloated tool-result history.
    from agent import _estimate_chars, _trim_messages, _MAX_INPUT_CHARS
    if _estimate_chars(messages) > _MAX_INPUT_CHARS:
        messages = _trim_messages(messages)
        logger.info("trimmed history before mem_save for thread=%s", mem_key)
    mem_save(mem_key, messages)

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


def _md_to_mrkdwn(text: str) -> str:
    """Convert markdown inline formatting to Slack mrkdwn."""
    # Protect bold markers before processing italic
    text = re.sub(r'\*\*(.+?)\*\*', lambda m: f'\x00B\x00{m.group(1)}\x00/B\x00', text, flags=re.DOTALL)
    text = re.sub(r'__(.+?)__', lambda m: f'\x00B\x00{m.group(1)}\x00/B\x00', text, flags=re.DOTALL)
    # Italic: single * not adjacent to another *
    text = re.sub(r'(?<![*_])\*([^*\n]+)\*(?![*_])', r'_\1_', text)
    # Restore bold
    text = text.replace('\x00B\x00', '*').replace('\x00/B\x00', '*')
    # Strikethrough
    text = re.sub(r'~~(.+?)~~', r'~\1~', text, flags=re.DOTALL)
    # Hyperlinks: [label](url) → <url|label>
    text = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'<\2|\1>', text)
    return text


def _split_mrkdwn(text: str, limit: int = 3000) -> list[str]:
    """Split mrkdwn text into chunks ≤ limit, breaking on newlines."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        cut = text.rfind('\n', 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip('\n')
    return chunks


def _md_to_blocks(text: str) -> list[dict]:
    """Convert markdown to Slack Block Kit blocks."""
    blocks: list[dict] = []
    pending: list[str] = []

    def flush() -> None:
        if not pending:
            return
        content = '\n'.join(pending).strip()
        pending.clear()
        if not content:
            return
        content = _md_to_mrkdwn(content)
        for chunk in _split_mrkdwn(content):
            blocks.append({'type': 'section', 'text': {'type': 'mrkdwn', 'text': chunk}})

    for line in text.split('\n'):
        # H1 / H2 → header block
        m = re.match(r'^#{1,2} (.+)$', line)
        if m:
            flush()
            raw = re.sub(r'\*+(.+?)\*+', r'\1', m.group(1)).strip()
            blocks.append({
                'type': 'header',
                'text': {'type': 'plain_text', 'text': raw[:150], 'emoji': True},
            })
            continue

        # H3 → own bold section block (flush first to keep sections clean)
        m = re.match(r'^### (.+)$', line)
        if m:
            flush()
            blocks.append({'type': 'section', 'text': {'type': 'mrkdwn', 'text': f'*{m.group(1).strip()}*'}})
            continue

        # Horizontal rule → divider
        if re.match(r'^[-*_]{3,}\s*$', line.strip()):
            flush()
            blocks.append({'type': 'divider'})
            continue

        # Table separator → skip
        if re.match(r'^\|[\s\-:|]+\|', line):
            continue

        # Table data row → inline bullets
        if re.match(r'^\|.+\|', line):
            cells = [c.strip() for c in line.strip('|').split('|') if c.strip()]
            pending.append('• ' + ' · '.join(cells))
            continue

        pending.append(line)

    flush()
    return blocks or [{'type': 'section', 'text': {'type': 'mrkdwn', 'text': text[:3000]}}]


def _is_structured(text: str) -> bool:
    """True when text has markdown structure worth converting to Block Kit."""
    return bool(
        re.search(r'^#{1,3} ', text, re.MULTILINE)
        or re.search(r'^\|.+\|', text, re.MULTILINE)
        or (len(text) > 600 and re.search(r'\*\*.+\*\*', text))
    )


def _send_chunked(say, text: str, channel: str, thread_ts: str | None, limit: int = 2900):
    """Post response to Slack. Uses Block Kit for structured content."""

    def _post_raw(msg: str) -> None:
        kwargs = dict(text=msg, channel=channel, mrkdwn=True)
        if thread_ts:
            kwargs["thread_ts"] = thread_ts
        say(**kwargs)

    def _post_blocks(blocks: list[dict]) -> None:
        # Keep first 1500 chars as plain fallback (used for feedback excerpts)
        fallback = re.sub(r'#+ |[*_~`|]', '', text)[:1500].strip()
        for i in range(0, len(blocks), 50):  # Slack max = 50 blocks per message
            kwargs = dict(blocks=blocks[i:i + 50], text=fallback, channel=channel)
            if thread_ts:
                kwargs["thread_ts"] = thread_ts
            say(**kwargs)

    if not text or not text.strip():
        _post_raw("_Ik kon geen antwoord formuleren. Controleer de logs of probeer de vraag opnieuw._")
        return

    if _is_structured(text):
        _post_blocks(_md_to_blocks(text))
        return

    # Plain text path for short / unstructured messages
    if len(text) <= limit:
        _post_raw(text)
        return
    lines = text.split("\n")
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 1 > limit:
            _post_raw(chunk.strip())
            chunk = line + "\n"
        else:
            chunk += line + "\n"
    if chunk.strip():
        _post_raw(chunk.strip())


@app.event("app_mention")
def handle_mention(event, say, client):
    bot_info = client.auth_test()
    bot_user_id = bot_info["user_id"]

    raw_text = event.get("text", "")
    user_text = _clean_text(raw_text, bot_user_id)
    files = event.get("files", [])

    # Nothing to process if there's no text and no files
    if not user_text and not files:
        return

    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])
    user_id = event.get("user", "")

    if files:
        # Acknowledge with file-specific message so user knows it's being read
        say(text="_Bestand ontvangen, even lezen…_", thread_ts=thread_ts, channel=channel, mrkdwn=True)

        def process_with_files():
            file_blocks = _download_files(files)
            if not file_blocks:
                say(
                    text="_Kon het bijgevoegde bestand niet lezen. Kun je de inhoud plakken?_",
                    thread_ts=thread_ts,
                    channel=channel,
                    mrkdwn=True,
                )
                return
            # Build multi-modal content: text caption + file/image blocks
            if user_text:
                content = [{"type": "text", "text": user_text}] + file_blocks
            else:
                content = file_blocks
            _run_and_reply(channel, thread_ts, content, say, user_id=user_id)

        t = threading.Thread(target=process_with_files, daemon=True)
    else:
        # Acknowledge immediately
        say(text="_Searching source layer…_", thread_ts=thread_ts, channel=channel, mrkdwn=True)

        t = threading.Thread(
            target=_run_and_reply,
            args=(channel, thread_ts, user_text, say),
            kwargs={"user_id": user_id},
            daemon=True,
        )
    t.start()


def _slash_handler(skill: str, body, ack, say):
    ack()
    user_text = body.get("text", "").strip()
    channel = body["channel_id"]
    # Slash commands have no valid thread_ts — only use one if it looks like a
    # real Slack timestamp (epoch.microseconds, e.g. "1748349600.123456").
    _raw_ts = body.get("thread_ts") or body.get("ts")
    thread_ts = _raw_ts if isinstance(_raw_ts, str) and "." in _raw_ts else None
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


@app.command("/transcript")
def cmd_transcript(body, ack, say):
    _slash_handler("client_discovery_debrief", body, ack, say)


# Quality checks
@app.command("/dvv")
def cmd_dvv(body, ack, say):
    _slash_handler("dvv_check", body, ack, say)


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
            file=io.BytesIO(pptx_bytes),
            filename=filename,
            title=f"Voorstel {client_name} — Minkowski",
        )

    except Exception as e:
        logger.error("PPTX export failed: %s", e, exc_info=True)
        app.client.chat_postMessage(
            channel=channel,
            text="⚠️ Exporteren mislukt. Controleer het document-ID en probeer opnieuw.",
        )


@app.command("/feedback-review")
def cmd_feedback_review(body, ack, say):
    """Trigger the review_feedback skill. Empty input is allowed — the skill
    just reads gaps.md and proposes actions."""
    ack()
    user_text = body.get("text", "").strip() or "Doe een feedback review."
    channel = body["channel_id"]
    _raw_ts = body.get("thread_ts") or body.get("ts")
    thread_ts = _raw_ts if isinstance(_raw_ts, str) and "." in _raw_ts else None
    say(text="_Reviewing feedback patterns…_", channel=channel, mrkdwn=True)
    t = threading.Thread(
        target=_run_and_reply,
        args=(channel, thread_ts, user_text, say, "review_feedback"),
        kwargs={"user_id": body.get("user_id", "")},
        daemon=True,
    )
    t.start()


@app.command("/kennisbronnen")
def cmd_kennisbronnen(body, ack, say):
    """Ad-hoc cross-source kennis-analyse: verrijken + bevestigen over onafhankelijke oorsprongen."""
    ack()
    channel = body["channel_id"]
    _raw_ts = body.get("thread_ts") or body.get("ts")
    thread_ts = _raw_ts if isinstance(_raw_ts, str) and "." in _raw_ts else None
    say(
        text=(
            "_Kennis-analyse gestart (ad-hoc). Ik kruis de databronnen en kijk waar "
            "verkondigd en verkocht uiteenlopen. Even geduld — dit kan een paar minuten duren._\n"
            "_Let op: dit is een blik op scherm; de meegroeiende kennis-laag wordt alleen "
            "bijgewerkt via `run_kennisextractie.py`._"
        ),
        channel=channel,
        mrkdwn=True,
    )
    prompt = (
        "Voer een kennis-analyse uit volgens de extract_knowledge skill in ad-hoc modus "
        "(géén kennis-laag aanwezig, dus geen laag-mutatie en geen fenced blokken). "
        "Lees de databronnen en weeg bevestiging per onafhankelijke oorsprong, niet per bron: "
        "LinkedIn + Substack (`06_Marketing/_bronmateriaal/`) = oorsprong 'jorgen-published' (verkondigd); "
        "Slack (`06_Marketing/_bronmateriaal/slack/`) = 'minkowski-intern'; "
        "`01_Proposals` = 'commercieel' (verkocht); `08_Outcomes` = 'klant'. "
        "Geef als kop de twee gaten: verkondigd-niet-verkocht en verkocht-niet-verkondigd."
    )
    t = threading.Thread(
        target=_run_and_reply,
        args=(channel, thread_ts, prompt, say, "extract_knowledge"),
        kwargs={"user_id": body.get("user_id", "")},
        daemon=True,
    )
    t.start()


_SLACK_FILE_HOSTS = {"files.slack.com", "slack-files.com"}


_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
_IMAGE_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _download_files(files: list) -> list[dict]:
    """Download Slack file attachments. Returns a list of Claude API content blocks.

    Images (jpg/jpeg/png/gif/webp) → base64 image blocks for vision.
    All other files → text blocks via _read_text.
    """
    import base64
    from tools import _read_text
    from pathlib import Path
    from urllib.parse import urlparse
    import requests as _req

    blocks: list[dict] = []
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

            if suffix in _IMAGE_EXTS:
                # Vision: encode as base64 image block
                media_type = _IMAGE_MIME[suffix]
                b64 = base64.standard_b64encode(r.content).decode("ascii")
                blocks.append({"type": "text", "text": f"Bijlage: {filename}"})
                blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64,
                    },
                })
                logger.info("image block added for %s (%d bytes)", filename, len(r.content))
            else:
                # Text/doc: extract content as before
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(r.content)
                    tmp_path = tmp.name
                content = _read_text(Path(tmp_path))
                os.unlink(tmp_path)
                blocks.append({"type": "text", "text": f"--- Bijlage: {filename} ---\n{content}"})
        except Exception as e:
            blocks.append({"type": "text", "text": f"[Kon {filename} niet lezen: {e}]"})
    return blocks


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

            if ftype == "technical" and cat == "hallucinatie":
                # Feitelijke fout: direct verifiëren, niet alleen noteren.
                say(
                    text=(
                        f"_Genoteerd ✅ als `{ftype} / {cat}`. "
                        "Dit klinkt als een feitelijke fout — ik ga dit direct verifiëren._"
                    ),
                    thread_ts=thread_ts,
                    channel=channel,
                    mrkdwn=True,
                )
                verify_prompt = (
                    f"Een gebruiker gaf 👎 op een antwoord van Ainstein en meldde:\n\n"
                    f"> {caption}\n\n"
                    f"Het originele antwoord (fragment):\n\n"
                    f"> {state['bot_excerpt'][:600]}\n\n"
                    f"Verifieer de bewering van de gebruiker via de bronnenlaag. "
                    f"Als de fout bevestigd wordt: erken het expliciet, leg uit wat er misging, "
                    f"en geef het correcte antwoord. "
                    f"Als je het niet kunt bevestigen of weerleggen: zeg dat expliciet."
                )
                t = threading.Thread(
                    target=_run_and_reply,
                    args=(channel, thread_ts, verify_prompt, say),
                    daemon=True,
                )
                t.start()
            else:
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

            # Auto-trigger: stel review voor na elke 10 feedback-entries.
            if increment_and_check(threshold=10):
                _notify_status(
                    "_:bulb: 10 nieuwe feedback-entries geregistreerd in `07_Feedback/gaps.md`. "
                    "Overweeg `/feedback-review` te draaien om patronen te identificeren en "
                    "de bronnenlaag gericht te verbeteren._"
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
            file_blocks = _download_files(files)
            if not file_blocks:
                say(text="_Kon de bijlage(n) niet verwerken._", thread_ts=thread_ts, channel=channel, mrkdwn=True)
                return
            # Build multi-modal content: text caption + file/image blocks
            if caption:
                content = [{"type": "text", "text": caption}] + file_blocks
            else:
                content = file_blocks
            skill = _detect_skill(caption) if caption else None
            _run_and_reply(channel, thread_ts, content, say, skill=skill, user_id=user_id)
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


def _notify_status(text: str) -> None:
    """Post a status message to AINSTEIN_STATUS_CHANNEL if configured."""
    channel = os.environ.get("AINSTEIN_STATUS_CHANNEL", "").strip()
    if not channel:
        return
    try:
        app.client.chat_postMessage(channel=channel, text=text, mrkdwn=True)
    except Exception as e:
        logger.warning("status notification failed: %s", e)


def _notify_failure(err: Exception, channel: str, thread_ts: str | None) -> None:
    """Stuur een foutmelding naar AINSTEIN_STATUS_CHANNEL als een request volledig faalt."""
    status_channel = os.environ.get("AINSTEIN_STATUS_CHANNEL", "").strip()
    if not status_channel:
        return

    err_str = str(err).lower()
    if "credit balance" in err_str or "too low" in err_str:
        soort = "💳 Credits op"
        actie = "Ga naar *console.anthropic.com → Billing → Add funds*"
    elif "invalid api key" in err_str or "authentication" in err_str:
        soort = "🔑 Ongeldige API key"
        actie = "Ga naar *console.anthropic.com → API Keys* en maak een nieuwe key aan. Zet hem in `.env` op de VM en herstart de service."
    elif "rate limit" in err_str:
        soort = "⏱ Rate limit bereikt"
        actie = "Ainstein kon dit verzoek niet verwerken. Stuur het opnieuw als de rate limit is afgelopen."
    else:
        soort = f"⚠️ Onverwachte fout: `{type(err).__name__}`"
        actie = "Check `logs/ainstein.log` op de VM voor details."

    thread_link = f"thread `{thread_ts}`" if thread_ts else "onbekende thread"
    in_channel = f"channel `{channel}`" if channel else ""
    location = f"{in_channel} / {thread_link}".strip(" /")

    tekst = (
        f"*Ainstein kon niet reageren* — {soort}\n"
        f"*Locatie:* {location}\n"
        f"*Actie:* {actie}"
    )
    try:
        app.client.chat_postMessage(channel=status_channel, text=tekst, mrkdwn=True)
    except Exception as notify_err:
        logger.warning("failure notification kon niet worden verstuurd: %s", notify_err)


if __name__ == "__main__":
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        raise SystemExit("SLACK_APP_TOKEN not set. See .env.example.")

    import signal
    from datetime import datetime

    handler = SocketModeHandler(app, app_token)
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    status_channel = os.environ.get("AINSTEIN_STATUS_CHANNEL", "").strip()
    logger.info("Ainstein is running in Slack. Press Ctrl+C to stop.")
    logger.info("Status notifications: channel=%s", status_channel or "(niet geconfigureerd — stel AINSTEIN_STATUS_CHANNEL in)")
    _notify_status(f"_Ainstein gestart om {start_time} (Amsterdam). Klaar voor gebruik._")

    def _on_shutdown(signum, frame):
        shutdown_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        logger.info("Ainstein shutting down (signal %s)", signum)
        _notify_status(
            f"_Ainstein gestopt om {shutdown_time} (signaal {signum}). "
            "Bot is tijdelijk offline — herstart volgt automatisch via systemd._"
        )
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _on_shutdown)
    signal.signal(signal.SIGINT, _on_shutdown)

    if os.environ.get("JAMIE_WEBHOOK_SECRET"):
        from webhook_server import start_webhook_server
        webhook_port = int(os.environ.get("JAMIE_WEBHOOK_PORT", "8080"))
        threading.Thread(
            target=start_webhook_server,
            args=(webhook_port, app.client, ANTHROPIC_CLIENT),
            daemon=True,
        ).start()
        logger.info("Jamie webhook server gestart op poort %s", webhook_port)
    else:
        logger.info("JAMIE_WEBHOOK_SECRET niet ingesteld — webhook server uitgeschakeld")

    try:
        handler.start()
    except SystemExit:
        raise
    except Exception as e:
        crash_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        logger.exception("Ainstein crashed: %s", e)
        _notify_status(
            f"_Ainstein gecrasht om {crash_time}: `{type(e).__name__}: {e}`_\n"
            "Controleer de logs op de VM. Systemd herstart de bot automatisch."
        )
        raise
