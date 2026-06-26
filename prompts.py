"""Prompt loader for AInstein.

Brain and skills live as plain markdown files in this repo:
  - brain.md          → SYSTEM_PROMPT (who AInstein is, how it works)
  - skills/<name>.md  → SKILL_PROMPTS (one file per skill)

Edit those files directly to change AInstein's behaviour.
This module only loads them — do not put prompt content here.
"""

from pathlib import Path

_HERE = Path(__file__).parent


def _load(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# Brain — AInstein's identity, operating rules, and source-layer description
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = _load(_HERE / "brain.md")


# ---------------------------------------------------------------------------
# Skill registry — maps skill names to their Slack display labels
# ---------------------------------------------------------------------------

SKILL_LABELS = {
    "analyse_opportunity": "ANALYSE_OPPORTUNITY",
    "build_proposal": "BUILD_PROPOSAL",
    "refine_proposal": "REFINE_PROPOSAL",
    "match_experts": "MATCH_EXPERTS",
    "qualify_lead": "QUALIFY_LEAD",
    "prepare_discovery": "PREPARE_DISCOVERY",
    "map_objections": "MAP_OBJECTIONS",
    "client_discovery_debrief": "CLIENT_DISCOVERY_DEBRIEF",
    "sharpen_positioning": "SHARPEN_POSITIONING",
    "create_content": "CREATE_CONTENT",
    "adapt_messaging": "ADAPT_MESSAGING",
    "debrief_to_messaging": "DEBRIEF_TO_MESSAGING",
    "review_feedback": "REVIEW_FEEDBACK",
    "dvv_check": "DVV_CHECK",
    "meeting_reviewer": "MEETING_REVIEWER",
    "briefing_writer": "BRIEFING_WRITER",
    "extract_knowledge": "EXTRACT_KNOWLEDGE",
    "extract_knowledge_distilleer": "EXTRACT_KNOWLEDGE_DISTILLEER",
    "extract_knowledge_merge": "EXTRACT_KNOWLEDGE_MERGE",
    "extract_style_patterns": "EXTRACT_STYLE_PATTERNS",
}


# ---------------------------------------------------------------------------
# Skills — loaded from skills/<name>.md at startup
# ---------------------------------------------------------------------------

_SKILLS_DIR = _HERE / "skills"

# Skills die altijd de Minkowski schrijfstijl als prefix krijgen.
_VOICE_SKILLS = {
    "analyse_opportunity",
    "build_proposal",
    "refine_proposal",
    "sharpen_positioning",
    "create_content",
    "adapt_messaging",
    "debrief_to_messaging",
    "meeting_reviewer",
    "briefing_writer",
}

_VOICE = _load(_SKILLS_DIR / "minkowski_voice.md")

SKILL_PROMPTS: dict[str, str] = {
    name: (
        f"{_VOICE}\n\n---\n\n{_load(_SKILLS_DIR / f'{name}.md')}"
        if name in _VOICE_SKILLS
        else _load(_SKILLS_DIR / f"{name}.md")
    )
    for name in SKILL_LABELS
}
