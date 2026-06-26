"""Agent pipeline for processing meeting transcripts from Jamie (and future tools).

process_transcript() runs in a daemon thread. It:
1. Detects meeting type (client call / internal / follow-up)
2. Builds a prompt and runs run_agent with the appropriate skill
3. Posts results + actions to Slack

Clients are injected via set_clients() to avoid circular imports with slack_app.py.
"""

import logging
import os
import re
import traceback

from agent import run_agent
from jamie import infer_client_name, lookup_participant_slack_ids
from log_setup import append_decision_trace, get_logger
from models import TranscriptEvent

logger = get_logger(__name__)

_TRANSCRIPT_CHANNEL = ""

# Max characters of transcript to send to the agent (cost + token safety)
_MAX_TRANSCRIPT_CHARS = 24_000  # ~6k tokens; head + tail strategy above this

# DM channel → doc_id mapping for pending Insights additions
_pending_insights: dict[str, str] = {}


def register_insights_pending(channel_id: str, doc_id: str) -> None:
    _pending_insights[channel_id] = doc_id


def pop_insights_pending(channel_id: str) -> str | None:
    return _pending_insights.pop(channel_id, None)


def process_transcript(
    event: TranscriptEvent,
    slack_client,
    anthropic_client,
) -> None:
    """Full processing pipeline. Catches all exceptions so the daemon never silently dies."""
    transcript_channel = os.environ.get("AINSTEIN_TRANSCRIPT_CHANNEL", "").strip()
    try:
        _save_transcript_bakje(event)  # bewaar ruwe bron eerst (Aslander) — mag de pijplijn nooit breken
        meeting_type = _detect_meeting_type(event)
        skill = _skill_for_type(meeting_type)
        prompt = _build_agent_prompt(event, meeting_type)
        messages = [{"role": "user", "content": prompt}]

        logger.info(
            "Processing transcript: meeting_id=%s title=%r type=%s skill=%s",
            event.meeting_id,
            event.title,
            meeting_type,
            skill,
        )

        debrief_text, trace = run_agent(messages, anthropic_client, skill=skill)
        trace["meeting_id"] = event.meeting_id
        trace["meeting_title"] = event.title
        append_decision_trace(trace)
        logger.info(
            "Agent done for meeting_id=%s — output %d chars",
            event.meeting_id, len(debrief_text),
        )

        meetingnote_result = _create_meetingnote(event, anthropic_client)

        participant_slack_ids = lookup_participant_slack_ids(event.participants, slack_client)
        logger.info(
            "Minkowski deelnemers gevonden: %s",
            list(participant_slack_ids.keys()) or "geen",
        )
        _post_slack_notification(
            event, debrief_text, participant_slack_ids, meeting_type, slack_client,
            transcript_channel, meetingnote_result,
        )

    except Exception:
        logger.exception("transcript_processor: unhandled error for meeting_id=%s", event.meeting_id)
        _post_failure_to_slack(event, traceback.format_exc(), slack_client, transcript_channel)


def _save_transcript_bakje(event: TranscriptEvent) -> None:
    """Bewaar de ruwe transcript als platte-tekst .md-bakje in 06_Marketing/_bronmateriaal/jamie/.

    Aslander: de ruwe bron — met klant-, expert- en collega-stemmen — is het goud dat we bewaren;
    de AI-samenvatting is afgeleid en wegwerpbaar. Dit bakje voedt de kennis-laag
    (run_kennisextractie) met een wekelijkse, onafhankelijke, meerstemmige bron.
    Eigen try/except: een Drive-fout mag het verwerken van de meeting nooit breken.
    """
    raw = (event.transcript or "").strip()
    if not raw:
        logger.info("Geen transcript-tekst om als bakje te bewaren (meeting_id=%s)", event.meeting_id)
        return
    try:
        from tools import save_text_bakje

        meeting_type = _detect_meeting_type(event)
        context = infer_client_name(event) if meeting_type != "internal" else "intern Minkowski-overleg"
        participants_str = ", ".join(p.get("name", p.get("email", "?")) for p in event.participants)
        date_str = (event.started_at or "")[:10] or "onbekend"
        safe_title = re.sub(r"[^a-zA-Z0-9_\- ]", "_", event.title or "meeting").strip()[:60]
        mid = re.sub(r"[^a-zA-Z0-9]", "", str(event.meeting_id or ""))[:8]
        bakje_title = "_".join(part for part in [date_str, safe_title, mid] if part)

        content = (
            f"# {event.title}\n"
            f"_Bron: Jamie transcript | meeting_id: {event.meeting_id}_\n"
            f"_Datum: {event.started_at} | Type: {meeting_type} | Klant/context: {context}_\n"
            f"_Deelnemers: {participants_str}_\n"
            f"_Ruwe transcript — onafhankelijke bron, NIET de AI-samenvatting._\n\n"
            f"{raw}\n"
        )
        result = save_text_bakje(["06_Marketing", "_bronmateriaal", "jamie"], bakje_title, content)
        if result.get("error"):
            logger.warning("Transcript-bakje niet opgeslagen (meeting_id=%s): %s", event.meeting_id, result["error"])
        else:
            logger.info("Transcript-bakje opgeslagen: %s (meeting_id=%s)", result.get("name"), event.meeting_id)
    except Exception:
        logger.exception("Transcript-bakje opslaan mislukt (meeting_id=%s)", event.meeting_id)


# ---------------------------------------------------------------------------
# Meetingnote generation
# ---------------------------------------------------------------------------

def _create_meetingnote(event: TranscriptEvent, anthropic_client) -> dict | None:
    """Generate a Meetingnote Google Doc for this meeting.

    Makes a direct, cheap API call (Haiku) — no tool loop needed.
    Returns {"url": str, "doc_id": str} or None on failure.
    """
    logger.info("_create_meetingnote: gestart voor meeting_id=%s", event.meeting_id)
    try:
        content = _generate_meetingnote_content(event, anthropic_client)
        logger.info("_create_meetingnote: content gegenereerd (%d chars)", len(content) if content else 0)
        if not content:
            return None
        from gdoc_tools import create_doc_via_drive, find_or_create_meetingnotes_folder
        client_name = infer_client_name(event)
        # Build list of search terms: client name first, then email domain keywords as fallback
        # infer_client_name can return a person name — domain gives a better company signal
        domain_keywords = [
            p["email"].split("@")[-1].split(".")[0].split("-")[0]
            for p in event.participants
            if "@" in p.get("email", "")
            and not any(d in p["email"] for d in ("minkowski.org", "minkowski.nl"))
        ]
        search_terms = [t for t in [client_name] + domain_keywords if t and len(t) >= 3]
        folder_id = find_or_create_meetingnotes_folder(search_terms)
        date_str = (event.started_at or "")[:10] or "onbekend"
        safe_title = re.sub(r"[^a-zA-Z0-9_\- ]", "_", event.title or "meeting").strip()[:60]
        doc_title = f"Meetingnote {date_str} — {safe_title}"
        result = create_doc_via_drive(doc_title, content, folder_id)
        logger.info("Meetingnote aangemaakt: %s (meeting_id=%s)", result.get("url"), event.meeting_id)
        return result
    except Exception:
        logger.exception("Meetingnote aanmaken mislukt (meeting_id=%s)", event.meeting_id)
        return None


def _generate_meetingnote_content(event: TranscriptEvent, anthropic_client) -> str:
    """Single Haiku API call to fill in the Meetingnote template."""
    from prompts import SKILL_PROMPTS
    skill_prompt = SKILL_PROMPTS.get("briefing_writer", "")

    lang = event.language or "nl"
    lang_instruction = (
        "Schrijf de Meetingnote volledig in het Nederlands."
        if lang == "nl"
        else "Write the Meetingnote entirely in English."
    )

    participants_str = ", ".join(p.get("name", p.get("email", "?")) for p in event.participants)
    client_name = infer_client_name(event)
    tasks_text = _format_tasks(event)
    summary_text = event.summary or "Geen samenvatting beschikbaar."
    transcript_text = _truncate_transcript(event.transcript or "")

    user_prompt = (
        f"{lang_instruction}\n\n"
        f"Meeting: {event.title}\n"
        f"Datum: {event.started_at}\n"
        f"Deelnemers: {participants_str}\n"
        f"Klant/organisatie: {client_name}\n\n"
        f"--- Jamie's samenvatting ---\n{summary_text}\n\n"
        f"--- Jamie's taken ---\n{tasks_text or 'Geen taken gelogd.'}\n\n"
        f"--- Transcript ---\n{transcript_text}\n\n"
        f"Vul de Meetingnote-template in op basis van bovenstaande informatie."
    )

    logger.info("_generate_meetingnote_content: API aanroep starten")
    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system=skill_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text.strip()
    except Exception:
        logger.exception("_generate_meetingnote_content: API call mislukt")
        return ""


# ---------------------------------------------------------------------------
# Meeting type detection
# ---------------------------------------------------------------------------

_INTERNAL_KEYWORDS = {"intern", "internal", "team", "retrospective", "retro", "standup", "sync", "planning"}
_CHECKIN_KEYWORDS = {"check in", "check-in", "checkin", "check up", "voortgang", "update", "status", "progress"}
_FOLLOWUP_KEYWORDS = {"follow-up", "followup", "follow up", "opvolg", "offerte", "proposal"}
_MINKOWSKI_DOMAINS = {"minkowski.org", "minkowski.nl"}


def _detect_meeting_type(event: TranscriptEvent) -> str:
    """Return 'discovery', 'check_in', 'follow_up', or 'internal'."""
    title_lower = event.title.lower()

    # Internal: all participants have Minkowski email domains
    non_minkowski = [
        p for p in event.participants
        if "@" in p.get("email", "") and p["email"].split("@")[-1] not in _MINKOWSKI_DOMAINS
    ]
    if not non_minkowski:
        return "internal"
    if any(kw in title_lower for kw in _INTERNAL_KEYWORDS):
        return "internal"

    if any(kw in title_lower for kw in _CHECKIN_KEYWORDS):
        return "check_in"
    if any(kw in title_lower for kw in _FOLLOWUP_KEYWORDS):
        return "follow_up"
    return "discovery"


def _skill_for_type(meeting_type: str) -> str:
    # All meeting types now use the reviewer skill — it adapts via the prompt
    return "meeting_reviewer"


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def _build_agent_prompt(event: TranscriptEvent, meeting_type: str) -> str:
    lang = event.language or "nl"
    lang_instruction = (
        "Schrijf je output volledig in het Nederlands."
        if lang == "nl"
        else "Write your output entirely in English."
    )

    participants_str = ", ".join(
        p.get("name", p.get("email", "?")) for p in event.participants
    )
    tasks_text = _format_tasks(event)
    summary_text = event.summary or ""
    transcript_text = _truncate_transcript(event.transcript or "")

    # Transcript first — Ainstein reads independently before seeing Jamie's conclusions
    transcript_block = f"\n---\nTranscript:\n{transcript_text}" if transcript_text else ""
    jamie_block = (
        f"**Jamie's samenvatting:**\n{summary_text}\n\n"
        f"**Jamie's taken:**\n{tasks_text or 'Geen taken gelogd door Jamie.'}\n"
    )

    header = (
        f"{lang_instruction}\n\n"
        f"**Meeting:** {event.title}\n"
        f"**Datum:** {event.started_at} | **Deelnemers:** {participants_str}\n"
    )

    if meeting_type == "internal":
        return (
            header
            + "\nDit is een intern Minkowski-overleg.\n"
            + transcript_block
            + "\n\n---\n"
            + jamie_block
            + "\nVolg de meeting_reviewer skill. Geen klantcontext nodig — "
            + "lees het transcript zelf, extraheer je eigen takenlijst, vergelijk met Jamie, "
            + "sla een notitie op via save_note."
        )

    client_name = infer_client_name(event)
    type_hints = {
        "check_in": "check-in / voortgangsgesprek (mid-programma of mid-traject)",
        "follow_up": "follow-up op offerte of voorstel",
        "discovery": "eerste contact / intake / kennismaking",
    }
    type_hint = type_hints.get(meeting_type, "gesprek met externe partij")

    return (
        header
        + f"**Klant:** {client_name} | **Type:** {type_hint}\n"
        + transcript_block
        + "\n\n---\n"
        + jamie_block
        + "\nVolg de meeting_reviewer skill:\n"
        + "1. Lees het transcript zelf en extraheer je EIGEN takenlijst (onafhankelijk van Jamie).\n"
        + "2. Vergelijk daarna met Jamie's taken — wat klopt, wat mist, wat verschilt?\n"
        + "3. Zoek relevante context in de bronnenlaag (01_Proposals, 02_Tools, 04_Experts).\n"
        + "4. Sla gespreksnotities op via save_note (folder_hint = klantnaam indien bekend).\n"
        + "5. Formuleer wat JIJ direct kunt oppakken."
    )


def _format_tasks(event: TranscriptEvent) -> str:
    """Format Jamie's tasks from the raw payload into a readable list."""
    tasks = (event.raw_payload or {}).get("data", {}).get("tasks") or []
    if not tasks:
        return ""
    lines = []
    for t in tasks:
        if isinstance(t, dict):
            content = t.get("content") or t.get("text") or str(t)
            assignee = t.get("assignee") or t.get("owner") or ""
            line = f"- {content}"
            if assignee:
                line += f" ({assignee})"
            lines.append(line)
        elif isinstance(t, str):
            lines.append(f"- {t}")
    return "\n".join(lines)


def _truncate_transcript(text: str) -> str:
    """Keep head + tail when transcript is too long."""
    if len(text) <= _MAX_TRANSCRIPT_CHARS:
        return text
    half = _MAX_TRANSCRIPT_CHARS // 2
    return (
        text[:half]
        + f"\n\n[... {len(text) - _MAX_TRANSCRIPT_CHARS} tekens weggelaten om tokenlimiet te respecteren ...]\n\n"
        + text[-half:]
    )


# ---------------------------------------------------------------------------
# Slack communication
# ---------------------------------------------------------------------------

def _post_slack_notification(
    event: TranscriptEvent,
    debrief_text: str,
    participant_slack_ids: dict[str, str],
    meeting_type: str,
    slack_client,
    transcript_channel: str,
    meetingnote_result: dict | None = None,
) -> None:
    doc_url = meetingnote_result.get("url") if meetingnote_result else None
    doc_id = meetingnote_result.get("doc_id") if meetingnote_result else None

    doc_link_line = f"\n\n:page_facing_up: <{doc_url}|Meetingnote openen>" if doc_url else ""
    insights_line = "\n_Voeg je Insights toe: reply met_ `Insights: [jouw tekst]`" if doc_url else ""
    full_message = debrief_text + doc_link_line + insights_line

    sent_dms: list[tuple[str, str]] = []
    failed_dms: list[str] = []

    # 1. Primair: DM naar Minkowski-deelnemers — volledige debrief + Meetingnote-link
    for name, slack_id in participant_slack_ids.items():
        try:
            resp_dm = slack_client.chat_postMessage(
                channel=slack_id,
                text=full_message,
                mrkdwn=True,
            )
            logger.info("DM verstuurd aan %s (%s) voor '%s'", name, slack_id, event.title)
            sent_dms.append((name, slack_id))
            if doc_url and doc_id:
                register_insights_pending(resp_dm["channel"], doc_id)
        except Exception as exc:
            logger.error("Failed to DM %s (%s): %s", name, slack_id, exc)
            failed_dms.append(name)

    # 2. Fallback: geen Minkowski-deelnemers → klant-specifiek kanaal op naam
    if not participant_slack_ids:
        client_channel = _find_client_channel(event, slack_client)
        if client_channel:
            try:
                slack_client.chat_postMessage(
                    channel=client_channel,
                    text=full_message,
                    mrkdwn=True,
                )
                logger.info("Fallback: bericht verstuurd naar klantkanaal %s voor '%s'", client_channel, event.title)
            except Exception as exc:
                logger.error("Failed to post to client channel %s: %s", client_channel, exc)
        else:
            logger.warning("Geen Minkowski-deelnemers en geen klantkanaal gevonden voor '%s'", event.title)

    # 3. CC: één regel naar ainstein-status — geen analyse, geen thread
    if not transcript_channel:
        logger.warning("AINSTEIN_TRANSCRIPT_CHANNEL niet ingesteld — CC overgeslagen")
    else:
        try:
            client_name = infer_client_name(event)
            date_str = (event.started_at or "")[:10]
            cc_text = f":white_check_mark: *{event.title}*"
            if client_name and client_name != event.title:
                cc_text += f"  ·  {client_name}"
            if date_str:
                cc_text += f"  ·  {date_str}"
            blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": cc_text}}]
            if doc_url:
                blocks.append({"type": "actions", "elements": [{
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Meetingnote", "emoji": True},
                    "url": doc_url,
                }]})
            if sent_dms:
                names = ", ".join(f"<@{sid}>" for _, sid in sent_dms)
                blocks.append({"type": "context", "elements": [
                    {"type": "mrkdwn", "text": f"DM verstuurd aan {names}"}
                ]})
            slack_client.chat_postMessage(
                channel=transcript_channel,
                text=f"Verwerkt: {event.title}",
                blocks=blocks,
            )
            logger.info("CC naar ainstein-status geslaagd voor '%s'", event.title)
        except Exception as exc:
            logger.error("Failed to post CC to %s: %s", transcript_channel, exc)


def _find_client_channel(event: TranscriptEvent, slack_client) -> str | None:
    """Find a Slack channel whose name matches the client name (e.g. #jetske-ultee).

    Slugifies the client name (lowercase, spaces → hyphens) and checks if any
    channel name contains it. Returns the channel ID or None.
    """
    client_name = infer_client_name(event)
    if not client_name or client_name.lower() in ("onbekend", "unknown"):
        return None

    slug = re.sub(r"[^a-z0-9]+", "-", client_name.lower()).strip("-")
    if len(slug) < 3:
        return None

    try:
        cursor = None
        while True:
            kwargs = {"limit": 200, "exclude_archived": True}
            if cursor:
                kwargs["cursor"] = cursor
            resp = slack_client.conversations_list(**kwargs)
            for ch in resp.get("channels", []):
                ch_name = ch.get("name", "").lower()
                if slug in ch_name or ch_name in slug:
                    logger.info("_find_client_channel: '%s' → #%s (%s)", client_name, ch["name"], ch["id"])
                    return ch["id"]
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
    except Exception as exc:
        logger.warning("_find_client_channel: channel lookup mislukt: %s", exc)

    logger.info("_find_client_channel: geen kanaal gevonden voor '%s' (slug: %s)", client_name, slug)
    return None


def _build_channel_blocks(event: TranscriptEvent, actions: str, has_actions: bool, doc_url: str | None) -> list:
    """Block Kit layout for the #ainstein-status channel post — minimal notification."""
    client_name = infer_client_name(event)
    date_str = (event.started_at or "")[:10]
    header_text = f":microphone: *{event.title}*"
    if client_name and client_name != event.title:
        header_text += f"  ·  {client_name}"
    if date_str:
        header_text += f"  ·  {date_str}"

    blocks: list = [
        {"type": "section", "text": {"type": "mrkdwn", "text": header_text}},
    ]

    if doc_url:
        blocks.append({
            "type": "actions",
            "elements": [{
                "type": "button",
                "text": {"type": "plain_text", "text": "Meetingnote openen", "emoji": True},
                "url": doc_url,
                "style": "primary",
            }],
        })

    return blocks



def _post_dm_status(
    slack_client,
    channel: str,
    thread_ts: str,
    sent_dms: list[tuple[str, str]],
    failed_dms: list[str],
) -> None:
    """Post a thread reply confirming which DMs were actually delivered."""
    if not sent_dms and not failed_dms:
        text = ":bust_in_silhouette: *DM-status:* geen Minkowski-deelnemers herkend in deze meeting — geen DM verstuurd."
    else:
        lines = [":bust_in_silhouette: *DM-status:*"]
        for name, slack_id in sent_dms:
            lines.append(f"  ✅ DM verstuurd aan <@{slack_id}> ({name})")
        for name in failed_dms:
            lines.append(f"  ❌ DM mislukt voor {name}")
        text = "\n".join(lines)
    try:
        slack_client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=text,
            mrkdwn=True,
        )
    except Exception as exc:
        logger.error("Failed to post DM status to thread: %s", exc)


def _post_chunked(slack_client, channel: str, thread_ts: str, text: str, chunk_size: int = 3800) -> None:
    """Post long text as multiple threaded replies to stay within Slack's per-message limit."""
    for i in range(0, len(text), chunk_size):
        try:
            slack_client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=text[i : i + chunk_size],
                mrkdwn=True,
            )
        except Exception as exc:
            logger.error("Failed to post chunk %d to thread: %s", i // chunk_size, exc)
            break



def _post_failure_to_slack(
    event: TranscriptEvent,
    tb: str,
    slack_client,
    transcript_channel: str,
) -> None:
    if not transcript_channel:
        return
    preview = (event.transcript or event.summary or "")[:500]
    try:
        slack_client.chat_postMessage(
            channel=transcript_channel,
            text=(
                f":x: *Ainstein kon het transcript van '{event.title}' niet verwerken.*\n\n"
                f"```{tb[-1500:]}```\n\n"
                f"*Transcript preview:*\n```{preview}```"
            ),
            mrkdwn=True,
        )
    except Exception as exc:
        logger.error("Failed to post failure notification: %s", exc)
