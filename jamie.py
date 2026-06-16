"""Jamie-specific webhook parser and verification utilities.

This module is the only place that knows about Jamie's payload format.
Everything else in the codebase works with TranscriptEvent from models.py.
"""

import hashlib
import hmac
import logging

from models import TranscriptEvent

logger = logging.getLogger(__name__)

_MINKOWSKI_DOMAINS = {"minkowski.org", "minkowski.nl"}

# NL / EN stopwords for language detection heuristic
_NL_WORDS = {"de", "het", "een", "en", "van", "dat", "is", "op", "te", "in", "we", "ik", "je", "ze"}
_EN_WORDS = {"the", "a", "an", "and", "of", "that", "is", "on", "to", "in", "we", "i", "you", "they"}


def detect_language(text: str) -> str:
    """Detect 'nl' or 'en' from the first 500 characters of text."""
    sample = text[:500].lower().split()
    nl = sum(1 for w in sample if w in _NL_WORDS)
    en = sum(1 for w in sample if w in _EN_WORDS)
    return "en" if en > nl else "nl"


def verify_jamie_signature(raw_body: bytes, header: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature sent by Jamie in x-jamie-signature header.

    Jamie uses the format: t=<timestamp>,v0=<hex_signature>
    The signed payload is: f"{timestamp}.{raw_body_as_string}"
    """
    if not header or not secret:
        return False
    try:
        parts = dict(part.split("=", 1) for part in header.split(",") if "=" in part)
        timestamp = parts.get("t", "")
        received_sig = parts.get("v0", "")
        if not timestamp or not received_sig:
            return False
        signed_payload = f"{timestamp}.".encode() + raw_body
        expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, received_sig)
    except Exception:
        return False


def parse_jamie_payload(body: dict) -> TranscriptEvent | None:
    """Parse a Jamie webhook payload into a TranscriptEvent.

    Jamie payload structure (from docs):
      data.event.title, data.event.id, data.event.startTime
      data.summary.markdown
      data.tasks[].content
      data.participants[].name / .email

    Returns None on any parse error — caller is responsible for
    posting the raw payload to Slack so it can be inspected.
    """
    try:
        data = body.get("data") or body  # handle both wrapped and flat payloads
        event = data.get("event") or {}

        meeting_id = str(event.get("id") or data.get("id") or body.get("id") or "unknown")
        title = (event.get("title") or data.get("title") or body.get("title")
                 or body.get("name") or "Naamloos gesprek")
        started_at = (event.get("startTime") or event.get("startedAt")
                      or data.get("startedAt") or "")

        participants = _parse_participants(data)
        transcript = _extract_transcript(data)

        # Jamie sends summary as markdown under data.summary.markdown
        summary_obj = data.get("summary") or {}
        if isinstance(summary_obj, dict):
            summary = summary_obj.get("markdown") or summary_obj.get("text") or ""
        else:
            summary = str(summary_obj) if summary_obj else ""

        # Append tasks to summary so the agent sees them
        tasks = data.get("tasks") or []
        if tasks:
            task_lines = "\n".join(f"- {t.get('content', t)}" for t in tasks if t)
            summary = f"{summary}\n\n**Taken:**\n{task_lines}".strip()

        recording_url = (event.get("recordingUrl") or data.get("recordingUrl")
                         or body.get("recordingUrl"))
        language = (event.get("language") or data.get("language")
                    or body.get("language") or "")
        if not language and transcript:
            language = detect_language(transcript)
        elif not language and summary:
            language = detect_language(summary)

        return TranscriptEvent(
            meeting_id=meeting_id,
            title=title,
            started_at=started_at,
            participants=participants,
            transcript=transcript,
            summary=summary,
            recording_url=recording_url,
            language=language or "nl",
            source_tool="jamie",
            raw_payload=body,
        )
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("jamie parse error: %s", exc)
        return None


def _parse_participants(body: dict) -> list[dict]:
    """Extract participants list, normalising to [{"name": str, "email": str}]."""
    raw = (body.get("participants") or body.get("attendees")
           or (body.get("data") or {}).get("participants") or [])
    result = []
    for p in raw:
        if isinstance(p, dict):
            name = p.get("name") or p.get("displayName") or ""
            email = (p.get("email") or p.get("emailAddress") or "").lower()
            result.append({"name": name, "email": email})
        elif isinstance(p, str):
            result.append({"name": p, "email": ""})
    return result


def _extract_transcript(body: dict) -> str:
    """Extract transcript text from various possible payload shapes."""
    # Try plain string first
    if isinstance(body.get("transcript"), str):
        return body["transcript"]
    # Try list of segments: [{"speaker": ..., "text": ...}]
    segments = body.get("transcript") or body.get("transcriptSegments") or []
    if isinstance(segments, list):
        lines = []
        for seg in segments:
            if isinstance(seg, dict):
                speaker = seg.get("speaker") or seg.get("name") or ""
                text = seg.get("text") or seg.get("content") or ""
                lines.append(f"{speaker}: {text}" if speaker else text)
            elif isinstance(seg, str):
                lines.append(seg)
        return "\n".join(lines)
    return ""


def lookup_participant_slack_ids(
    participants: list[dict],
    slack_client,
) -> dict[str, str]:
    """Return {name: slack_id} for Minkowski staff who were in this meeting.

    Queries Slack directly via users.lookupByEmail — no static mapping needed.
    Requires the users:read.email OAuth scope on the Slack app.
    Client participants (non-Minkowski email domains) are skipped silently.
    """
    result = {}
    for p in participants:
        email = p.get("email", "").lower()
        name = p.get("name", "")
        if not email:
            continue
        domain = email.split("@")[-1] if "@" in email else ""
        if domain not in _MINKOWSKI_DOMAINS:
            continue
        try:
            resp = slack_client.users_lookupByEmail(email=email)
            slack_id = resp["user"]["id"]
            result[name] = slack_id
        except Exception as exc:
            logger.warning("Could not resolve Slack ID for %s: %s", email, exc)
    return result


def infer_client_name(event: TranscriptEvent) -> str:
    """Guess the client name from participants or meeting title."""
    for p in event.participants:
        email = p.get("email", "")
        domain = email.split("@")[-1] if "@" in email else ""
        if domain and domain not in _MINKOWSKI_DOMAINS:
            return p.get("name") or domain
    # Fall back to first 3 words of title
    words = event.title.split()
    return " ".join(words[:3]) if words else "Onbekende klant"


