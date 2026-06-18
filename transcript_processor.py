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
from log_setup import get_logger
from models import TranscriptEvent

logger = get_logger(__name__)

_TRANSCRIPT_CHANNEL = ""

# Max characters of transcript to send to the agent (cost + token safety)
_MAX_TRANSCRIPT_CHARS = 24_000  # ~6k tokens; head + tail strategy above this


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

        debrief_text, _trace = run_agent(messages, anthropic_client, skill=skill)
        logger.info(
            "Agent done for meeting_id=%s — output %d chars",
            event.meeting_id, len(debrief_text),
        )
        participant_slack_ids = lookup_participant_slack_ids(event.participants, slack_client)
        logger.info(
            "Minkowski deelnemers gevonden: %s",
            list(participant_slack_ids.keys()) or "geen",
        )
        _post_slack_notification(
            event, debrief_text, participant_slack_ids, meeting_type, slack_client, transcript_channel
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
) -> None:
    actions = _extract_next_step(debrief_text)
    has_actions = bool(actions)

    thread_ts = None

    # 1. Channel post — always
    if not transcript_channel:
        logger.warning("AINSTEIN_TRANSCRIPT_CHANNEL niet ingesteld — kanaalpost overgeslagen")
    else:
        meeting_label = f"*{event.title}*" if event.title else "gesprek"
        if has_actions:
            channel_intro = f":microphone: Ainstein heeft {meeting_label} verwerkt.\n\n{actions}"
        else:
            channel_intro = (
                f":microphone: Ainstein heeft {meeting_label} verwerkt. "
                f"Geen vervolgacties gevonden — klopt dit?"
            )
        try:
            resp = slack_client.chat_postMessage(
                channel=transcript_channel,
                text=channel_intro,
                mrkdwn=True,
            )
            thread_ts = resp["ts"]
            logger.info("Kanaalpost geslaagd: channel=%s ts=%s", transcript_channel, thread_ts)
            # Post full debrief as threaded replies (chunk to stay within Slack's ~40k char limit)
            _post_chunked(slack_client, transcript_channel, thread_ts, debrief_text)
        except Exception as exc:
            logger.error("Failed to post to transcript channel: %s", exc)

    proposals = _extract_proactive_proposals(debrief_text)

    # 2. DM per Minkowski-deelnemer in this meeting
    sent_dms: list[tuple[str, str]] = []   # (name, slack_id)
    failed_dms: list[str] = []

    if not participant_slack_ids:
        logger.warning("Geen Minkowski-deelnemers gevonden — geen DM verstuurd voor '%s'", event.title)
    for name, slack_id in participant_slack_ids.items():
        try:
            first_name = name.split()[0] if name else "daar"
            if proposals:
                dm_text = (
                    f":wave: Hoi {first_name}, ik heb *{event.title}* verwerkt.\n\n"
                    + (f"Aanbevolen volgende stap:\n{actions}\n\n" if has_actions else "")
                    + f"{proposals}\n\nWat wil je dat ik oppak?"
                )
            elif has_actions:
                dm_text = (
                    f":wave: Hoi {first_name}, ik heb *{event.title}* verwerkt.\n\n"
                    f"Aanbevolen volgende stap:\n{actions}"
                )
            else:
                dm_text = (
                    f":wave: Hoi {first_name}, ik heb *{event.title}* verwerkt. "
                    f"Ik vond geen concrete vervolgacties — klopt dat?"
                )
            slack_client.chat_postMessage(
                channel=slack_id,
                text=dm_text,
                mrkdwn=True,
            )
            logger.info("DM verstuurd aan %s (%s) voor '%s'", name, slack_id, event.title)
            sent_dms.append((name, slack_id))
        except Exception as exc:
            logger.error("Failed to DM %s (%s): %s", name, slack_id, exc)
            failed_dms.append(name)

    # 3. Thread reply with verified DM status
    if transcript_channel and thread_ts:
        _post_dm_status(slack_client, transcript_channel, thread_ts, sent_dms, failed_dms)


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


def _extract_next_step(debrief_text: str) -> str:
    """Extract the 'Ik kan direct oppakken' section from a meeting_reviewer output."""
    pattern = re.compile(
        r"(?:\*{1,2}Ik kan direct oppakken.*?\*{0,2}|I can immediately|"
        r"#{1,3}\s*Ik kan direct|#{1,3}\s*11[.\s]).*?(?=(?:#{1,3}\s*[A-Z]|\Z))",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(debrief_text)
    if match:
        return match.group(0).strip()[:1000]
    return ""


def _extract_proactive_proposals(debrief_text: str) -> str:
    """Extract the 'Uit de bronnenlaag' section from a meeting_reviewer output."""
    pattern = re.compile(
        r"(?:\*{1,2}Uit de bronnenlaag.*?\*{0,2}|From the source layer|"
        r"#{1,3}\s*Uit de bronnenlaag|Proactieve Voorstellen\b).*?(?=(?:#{1,3}\s*[A-Z]|\*{1,2}Ik kan|\Z))",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(debrief_text)
    if match:
        return match.group(0).strip()[:800]
    return ""


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
