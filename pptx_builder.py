"""
Minkowski-branded PPTX builder for Ainstein.

Converts a proposal (as sections dict or Google Doc text) into a
Minkowski-styled PowerPoint deck using python-pptx.

Brand values are hard-coded from confirmed Minkowski decks:
  Navy:   #001C40    Cyan:  #53E4FF
  Yellow: #FEEC00    Light: #F7F7F7
  Font:   Arial      Slide: 13.33" × 7.5" (16:9)

Usage:
    sections = parse_proposal_sections(doc_text)
    pptx_bytes = build_proposal_deck(sections, client_name="NN Group")
    Path("voorstel.pptx").write_bytes(pptx_bytes)
"""

import io
import re
import textwrap
from typing import Optional

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

# ---------------------------------------------------------------------------
# Brand constants
# ---------------------------------------------------------------------------

BRAND = {
    "slide_width": Inches(13.33),
    "slide_height": Inches(7.5),
    "color_dark": RGBColor(0x00, 0x1C, 0x40),       # #001C40 deep navy
    "color_light": RGBColor(0xF7, 0xF7, 0xF7),       # #F7F7F7 near-white
    "color_white": RGBColor(0xFF, 0xFF, 0xFF),
    "color_accent": RGBColor(0x53, 0xE4, 0xFF),       # #53E4FF cyan
    "color_yellow": RGBColor(0xFE, 0xEC, 0x00),       # #FEEC00
    "color_gray": RGBColor(0x99, 0x99, 0x99),
    "font": "Arial",
    "pt_title": Pt(36),
    "pt_heading": Pt(22),
    "pt_body": Pt(13),
    "pt_small": Pt(9),
    "pt_label": Pt(11),
    "margin": Inches(0.7),
    "accent_bar_h": Inches(0.06),
}

# Sections that get a dark (navy) background
DARK_SECTIONS = {"commercial notes", "commerciële notities", "risks / weak spots", "risico's"}

# Ordered slide layout for a standard Minkowski proposal
SECTION_ORDER = [
    "context",
    "proposal logic",
    "recommended structure",
    "team / expert setup",
    "commercial notes",
    "risks / weak spots",
    "draft text",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_proposal_deck(
    sections: dict[str, str],
    client_name: str = "Client",
    proposal_title: Optional[str] = None,
) -> bytes:
    """Build a branded Minkowski PPTX from a sections dict.

    sections: {"Context": "...", "Proposal Logic": "...", ...}
    Returns raw PPTX bytes.
    """
    prs = Presentation()
    prs.slide_width = BRAND["slide_width"]
    prs.slide_height = BRAND["slide_height"]

    title = proposal_title or f"Voorstel {client_name}"
    _add_cover_slide(prs, title, client_name)

    for key in SECTION_ORDER:
        for sec_name, sec_body in sections.items():
            if sec_name.lower().strip() == key:
                if not sec_body.strip():
                    break
                dark = key in DARK_SECTIONS
                _add_content_slides(prs, sec_name, sec_body, dark=dark)
                break

    # Any sections not in the standard order go at the end (light bg)
    ordered_lower = {k.lower().strip() for k in SECTION_ORDER}
    for sec_name, sec_body in sections.items():
        if sec_name.lower().strip() not in ordered_lower and sec_body.strip():
            _add_content_slides(prs, sec_name, sec_body, dark=False)

    _add_back_slide(prs)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def parse_proposal_sections(text: str) -> dict[str, str]:
    """Parse a Markdown-style proposal text into a sections dict.

    Splits on lines starting with # or ## headings.
    Returns {"Section Name": "body text", ...}.
    """
    sections: dict[str, str] = {}
    current_heading = None
    current_lines: list[str] = []

    for line in text.splitlines():
        heading_match = re.match(r"^#{1,3}\s+(.+)$", line)
        if heading_match:
            if current_heading is not None:
                body = "\n".join(current_lines).strip()
                if body:
                    sections[current_heading] = body
            current_heading = heading_match.group(1).strip()
            current_lines = []
        else:
            if current_heading is not None:
                current_lines.append(line)

    if current_heading is not None:
        body = "\n".join(current_lines).strip()
        if body:
            sections[current_heading] = body

    return sections


# ---------------------------------------------------------------------------
# Slide builders
# ---------------------------------------------------------------------------

def _blank_slide(prs: Presentation):
    """Add a truly blank slide (no placeholders)."""
    blank_layout = prs.slide_layouts[6]  # layout 6 is blank in default theme
    return prs.slides.add_slide(blank_layout)


def _fill_background(slide, color: RGBColor):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_text_box(
    slide,
    text: str,
    left, top, width, height,
    font_size: Pt,
    color: RGBColor,
    bold: bool = False,
    align=PP_ALIGN.LEFT,
    wrap: bool = True,
) -> None:
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = BRAND["font"]
    run.font.size = font_size
    run.font.color.rgb = color
    run.font.bold = bold


def _add_brand_footer(slide, prs: Presentation):
    """Add small 'Minkowski' wordmark at bottom-right of every slide."""
    w = prs.slide_width
    h = prs.slide_height
    _add_text_box(
        slide, "Minkowski",
        left=w - Inches(1.8),
        top=h - Inches(0.35),
        width=Inches(1.6),
        height=Inches(0.3),
        font_size=BRAND["pt_small"],
        color=BRAND["color_gray"],
        align=PP_ALIGN.RIGHT,
    )


def _add_cyan_accent_bar(slide, prs: Presentation):
    """Add a thin cyan horizontal bar at the top of content slides."""
    from pptx.util import Emu
    bar = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        left=Emu(0),
        top=Emu(0),
        width=prs.slide_width,
        height=BRAND["accent_bar_h"],
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = BRAND["color_accent"]
    bar.line.fill.background()


def _add_cover_slide(prs: Presentation, title: str, client_name: str):
    slide = _blank_slide(prs)
    _fill_background(slide, BRAND["color_dark"])

    w = prs.slide_width
    h = prs.slide_height
    margin = BRAND["margin"]

    # Cyan accent bar at top
    _add_cyan_accent_bar(slide, prs)

    # Main title
    _add_text_box(
        slide, title,
        left=margin,
        top=Inches(2.2),
        width=w - 2 * margin,
        height=Inches(1.6),
        font_size=BRAND["pt_title"],
        color=BRAND["color_white"],
        bold=True,
    )

    # Client name / subtitle
    _add_text_box(
        slide, client_name,
        left=margin,
        top=Inches(3.9),
        width=w - 2 * margin,
        height=Inches(0.6),
        font_size=BRAND["pt_label"],
        color=BRAND["color_accent"],
    )

    _add_brand_footer(slide, prs)


def _add_content_slides(prs: Presentation, heading: str, body: str, dark: bool = False):
    """Add one or more content slides for a section, splitting at ~1200 chars."""
    bg_color = BRAND["color_dark"] if dark else BRAND["color_light"]
    text_color = BRAND["color_white"] if dark else BRAND["color_dark"]
    heading_color = BRAND["color_accent"] if dark else BRAND["color_dark"]

    # Split body into chunks of ~1200 chars at paragraph boundaries
    chunks = _split_body(body, max_chars=1200)

    for i, chunk in enumerate(chunks):
        slide = _blank_slide(prs)
        _fill_background(slide, bg_color)

        w = prs.slide_width
        h = prs.slide_height
        margin = BRAND["margin"]

        if not dark:
            _add_cyan_accent_bar(slide, prs)

        # Section heading (first slide shows full heading, continuations add "vervolg")
        label = heading if i == 0 else f"{heading} (vervolg)"
        _add_text_box(
            slide, label,
            left=margin,
            top=Inches(0.25) if not dark else Inches(0.7),
            width=w - 2 * margin,
            height=Inches(0.65),
            font_size=BRAND["pt_heading"],
            color=heading_color,
            bold=True,
        )

        # Body text
        _add_text_box(
            slide, chunk,
            left=margin,
            top=Inches(1.1),
            width=w - 2 * margin,
            height=h - Inches(1.8),
            font_size=BRAND["pt_body"],
            color=text_color,
        )

        _add_brand_footer(slide, prs)


def _add_back_slide(prs: Presentation):
    slide = _blank_slide(prs)
    _fill_background(slide, BRAND["color_dark"])

    w = prs.slide_width
    h = prs.slide_height
    margin = BRAND["margin"]

    _add_cyan_accent_bar(slide, prs)

    _add_text_box(
        slide, "Minkowski",
        left=margin,
        top=Inches(2.8),
        width=w - 2 * margin,
        height=Inches(0.9),
        font_size=BRAND["pt_title"],
        color=BRAND["color_white"],
        bold=True,
        align=PP_ALIGN.CENTER,
    )

    _add_text_box(
        slide, "Agency for Applied Futures",
        left=margin,
        top=Inches(3.7),
        width=w - 2 * margin,
        height=Inches(0.5),
        font_size=BRAND["pt_label"],
        color=BRAND["color_accent"],
        align=PP_ALIGN.CENTER,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _split_body(text: str, max_chars: int = 1200) -> list[str]:
    """Split text into chunks of at most max_chars, breaking at paragraphs."""
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) > max_chars and current_parts:
            chunks.append("\n\n".join(current_parts))
            current_parts = [para]
            current_len = len(para)
        else:
            current_parts.append(para)
            current_len += len(para)

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks or [text]
