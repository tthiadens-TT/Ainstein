"""
Tests for transcript_processor._strip_code_fence() — verwijdert een omringend
```-codeblok dat Haiku soms om de hele Meetingnote-respons zet (de skill toont
zijn eigen outputtemplate binnen een fence, en het model reproduceert die
soms letterlijk). Eerst gevlagd: daily-review 2026-07-07/08.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from transcript_processor import _strip_code_fence  # noqa: E402


def test_strips_plain_fence():
    text = "```\n# Meetingnote — X\n\ninhoud\n```"
    assert _strip_code_fence(text) == "# Meetingnote — X\n\ninhoud"


def test_strips_language_tagged_fence():
    text = "```markdown\n# Meetingnote — X\n\ninhoud\n```"
    assert _strip_code_fence(text) == "# Meetingnote — X\n\ninhoud"


def test_leaves_content_without_fence_untouched():
    text = "# Meetingnote — X\n\ninhoud zonder fence"
    assert _strip_code_fence(text) == text


def test_leaves_inline_code_snippet_untouched():
    """Een losse code-snippet MIDDENIN de inhoud (niet de hele respons
    omvattend) mag niet verminkt worden."""
    text = "# Meetingnote\n\nEen voorbeeld: ```rid = \"rIdSenEB\"``` in de code."
    assert _strip_code_fence(text) == text


def test_handles_empty_string():
    assert _strip_code_fence("") == ""
