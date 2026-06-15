"""Jamie-specific webhook parser and verification utilities.

This module is the only place that knows about Jamie's payload format.
Everything else in the codebase works with TranscriptEvent from models.py.
"""

import hashlib
import hmac
import json
import logging
import os

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
    """Verify HMAC-SHA256 signature sent by Jamie in X-Jamie-Signature header."""
    if not header or not secret:
        return False
    try:
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        # Jamie may send "sha256=<hex>" or just "<hex>"
        received = header.removeprefix("sha256=")
        return hmac.compare_digest(expected, received)
    except Exception:
        return False


def parse_jamie_payload(body: dict) -> TranscriptEvent | None:
    """Parse a Jamie webhook payload into a TranscriptEvent.

    Returns None on any parse error — caller is responsible for
    posting the raw payload to Slack so it can be inspected.
    """
    try:
        # Jamie's payload shape is inferred from their public docs.
        # Field names may need adjustment after the first real webhook arrives.
        meeting_id = str(body["id"])
        title = body.get("title") or body.get("name") or "Naamloos gesprek"
        started_at = body.get("startedAt") or body.get("started_at") or ""
        participants = _parse_participants(body)
        transcript = _extract_transcript(body)
        summary = body.get("summary") or body.get("shortSummary") or ""
        recording_url = body.get("recordingUrl") or body.get("recording_url")
        language = body.get("language") or body.get("lang") or ""
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
    raw = body.get("participants") or body.get("attendees") or []
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


def infer_participant_slack_ids(
    participants: list[dict],
    staff_map: dict[str, str],
) -> dict[str, str]:
    """Return {name: slack_id} for Minkowski staff who were in this meeting.

    staff_map = {email: slack_id} loaded from MINKOWSKI_STAFF_MAP env var.
    Client participants (non-Minkowski email domains) are filtered out.
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
        slack_id = staff_map.get(email)
        if slack_id:
            result[name] = slack_id
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


def load_staff_map() -> dict[str, str]:
    """Load MINKOWSKI_STAFF_MAP from env var. Returns empty dict on error."""
    raw = os.environ.get("MINKOWSKI_STAFF_MAP", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {k.lower(): v for k, v in parsed.items()}
    except json.JSONDecodeError as exc:
        logger.warning("MINKOWSKI_STAFF_MAP is not valid JSON: %s", exc)
    return {}
