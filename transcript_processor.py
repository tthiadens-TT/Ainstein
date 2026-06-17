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


# ---------------------------------------------------------------------------
# Meeting type detection
# ---------------------------------------------------------------------------

_INTERNAL_KEYWORDS = {"intern", "internal", "team", "retrospective", "retro", "standup", "sync", "planning"}
_FOLLOWUP_KEYWORDS = {"follow", "follow-up", "followup", "opvolg", "voortgang", "update", "check-in"}
_MINKOWSKI_DOMAINS = {"minkowski.org", "minkowski.nl"}


def _detect_meeting_type(event: TranscriptEvent) -> str:
    """Return 'client_call', 'follow_up', or 'internal'."""
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
    if any(kw in title_lower for kw in _FOLLOWUP_KEYWORDS):
        return "follow_up"
    return "client_call"


def _skill_for_type(meeting_type: str) -> str:
    return {
        "client_call": "client_discovery_debrief",
        "follow_up": "client_discovery_debrief",
        "internal": "create_content",
    }.get(meeting_type, "client_discovery_debrief")


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def _build_agent_prompt(event: TranscriptEvent, meeting_type: str) -> str:
    lang = event.language or "nl"
    lang_instruction = (
        "Schrijf je analyse volledig in het Nederlands."
        if lang == "nl"
        else "Write your analysis entirely in English."
    )

    transcript_text = _truncate_transcript(event.transcript or event.summary or "")

    if meeting_type == "internal":
        return (
            f"{lang_instruction}\n\n"
            f"Dit is een intern Minkowski-overleg: **{event.title}**\n"
            f"Datum: {event.started_at}\n\n"
            f"Maak een beknopt verslag met:\n"
            f"- Wat is besproken\n"
            f"- Besluiten die zijn genomen\n"
            f"- Actiepunten per persoon\n\n"
            f"---\n{transcript_text}"
        )

    client_name = infer_client_name(event)
    participants_str = ", ".join(
        p.get("name", p.get("email", "?")) for p in event.participants
    )
    type_hint = "Dit is een follow-up gesprek." if meeting_type == "follow_up" else "Dit is een eerste kennismakings- of intakegesprek."

    return (
        f"{lang_instruction}\n\n"
        f"Je rol: Ainstein — proactieve denkpartner, geen notulist (dat is Jamie's taak).\n"
        f"Jouw waarde zit in wat je TOEVOEGT aan dit gesprek, niet in wat er gezegd is.\n\n"
        f"**Meeting:** {event.title}\n"
        f"**Klant:** {client_name}\n"
        f"**Datum:** {event.started_at}\n"
        f"**Deelnemers:** {participants_str}\n"
        f"**Type:** {type_hint}\n\n"
        f"Analyseer dit gesprek met de 11 secties van client_discovery_debrief. Maar doe actief meer:\n"
        f"- DAAG UIT: welke aannames zijn gemaakt die het bevragen waard zijn?\n"
        f"- VOEG TOE: wat weet je vanuit de Minkowski bronnenlaag dat relevant is maar niet ter sprake kwam?\n"
        f"- DENK VERDER: welke richting of aanpak zou beter werken dan besproken?\n\n"
        f"Voeg na sectie 11 de sectie 'Proactieve Voorstellen' toe zoals beschreven in de skill.\n\n"
        f"---\n{transcript_text}"
    )


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
            # Post full debrief as threaded reply to keep the channel clean
            slack_client.chat_postMessage(
                channel=transcript_channel,
                thread_ts=thread_ts,
                text=debrief_text[:3000],
                mrkdwn=True,
            )
        except Exception as exc:
            logger.error("Failed to post to transcript channel: %s", exc)

    proposals = _extract_proactive_proposals(debrief_text)

    # 2. DM per Minkowski-deelnemer in this meeting
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
        except Exception as exc:
            logger.error("Failed to DM %s (%s): %s", name, slack_id, exc)


def _extract_next_step(debrief_text: str) -> str:
    """Extract section 11 (Recommended Next Step) from a debrief."""
    pattern = re.compile(
        r"(?:#{1,3}\s*11[.\s]|(?:\*{1,2})11[.\s]).*?(?=(?:#{1,3}\s*(?:Proactieve|12|\d+)|$))",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(debrief_text)
    if match:
        return match.group(0).strip()[:1000]
    return ""


def _extract_proactive_proposals(debrief_text: str) -> str:
    """Extract the Proactieve Voorstellen section from a debrief."""
    pattern = re.compile(
        r"(?:#{1,3}\s*Proactieve Voorstellen|Proactieve Voorstellen\b).*?(?=(?:#{1,3}\s*[A-Z]|\Z))",
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
