"""Shared datamodels for tool-agnostic transcript processing."""

from dataclasses import dataclass, field


@dataclass
class TranscriptEvent:
    """Tool-agnostic representation of a completed meeting with transcript.

    Parsers for specific tools (jamie.py, etc.) produce this type.
    transcript_processor.py consumes it without knowing the source tool.
    """

    meeting_id: str
    title: str
    started_at: str           # ISO 8601
    participants: list[dict]  # [{"name": str, "email": str}]
    transcript: str           # empty string if not available in payload
    summary: str              # empty string if not available
    recording_url: str | None
    language: str             # "nl" / "en" / "" (empty = unknown, detect from text)
    source_tool: str          # "jamie" / future tools
    raw_payload: dict = field(default_factory=dict, repr=False)
