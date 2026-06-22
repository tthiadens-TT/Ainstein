#!/usr/bin/env python3
"""
Minkowski Agent — Commercial intelligence layer for Minkowski agency.

Usage:
    python agent.py                         # auto-detect skill from input
    python agent.py --skill qualify_lead    # start in a specific skill
    python agent.py --help                  # see all available skills
"""

import os
import sys
import argparse
import textwrap
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_AMS = ZoneInfo("Europe/Amsterdam")
from pathlib import Path

import anthropic
from dotenv import load_dotenv

# Load .env from the repo root so ANTHROPIC_API_KEY etc. are available
# regardless of caller's working directory.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

import log_setup
from prompts import SYSTEM_PROMPT, SKILL_PROMPTS
from tools import TOOL_SCHEMAS, dispatch

logger = log_setup.get_logger("agent")

MODEL = "claude-sonnet-4-6"

SKILL_INTROS = {
    # Top-level skills
    "analyse_opportunity": (
        "I'm ready to analyse an opportunity. Share the client brief, meeting notes, "
        "or whatever context you have — and I'll work through it."
    ),
    "build_proposal": (
        "I'm ready to build or improve a proposal. Share the brief, existing draft, "
        "or the key details — and I'll retrieve relevant source material and structure a response."
    ),
    "match_experts": (
        "I'm ready to match experts to a challenge. Describe the client need, project context, "
        "or role requirements — and I'll search the expert profiles and recommend a shortlist."
    ),
    # Sales sub-skills
    "qualify_lead": (
        "I'm ready to qualify a lead. Share what came in — the brief, referral message, "
        "email, or call summary — and I'll give a clear verdict with critical unknowns and a next action."
    ),
    "prepare_discovery": (
        "I'm ready to prepare for a discovery conversation. Share what you know about the client, "
        "the stated ask, and the moment — and I'll build themed questions, listen-for signals, and an opening."
    ),
    "map_objections": (
        "I'm ready to map likely objections. Share the proposal, deal context, or competitive situation — "
        "and I'll identify objections, root causes, response angles, and high-risk signals."
    ),
    "client_discovery_debrief": (
        "I'm ready to turn raw call notes into a structured strategic debrief. Share the notes, "
        "transcript, or recap — and I'll produce the 11-section debrief with Minkowski diagnosis."
    ),
    # Marketing sub-skills
    "sharpen_positioning": (
        "I'm ready to sharpen positioning. Share the current language, the audience, and the medium — "
        "and I'll audit, identify what's generic, and rewrite for specificity."
    ),
    "create_content": (
        "I'm ready to create a content asset. Tell me the format (LinkedIn post, email, one-pager, article), "
        "the audience, and the angle — and I'll produce the actual asset, not an outline."
    ),
    "adapt_messaging": (
        "I'm ready to adapt Minkowski's messaging for a specific sector or audience. Share the target "
        "(sector + role + moment) — and I'll translate the positioning into language that lands for them."
    ),
    "debrief_to_messaging": (
        "I'm ready to extract marketing intelligence from a Client Discovery Debrief. Share the debrief — "
        "and I'll produce a client language glossary, pain point map, audience framing, and content opportunities."
    ),
    # Meta-skill
    "review_feedback": (
        "I'm ready to review the feedback log. I'll read `07_Feedback/gaps.md`, group entries into patterns, "
        "and propose one concrete edit per pattern — with file paths Thomas can act on."
    ),
}


def print_separator():
    print("\n" + "─" * 60 + "\n")


def print_agent(text: str):
    print(f"\033[1;36mMinkowski Agent\033[0m")
    print(textwrap.fill(text, width=80, subsequent_indent="  ") if len(text) < 200 else text)
    print()


def print_tool_use(name: str, input_preview: str):
    print(f"\033[2m  [{name}] {input_preview}\033[0m")


_MAX_INPUT_CHARS = 1_000_000  # empirically ~700k tokens @ ~1.4 chars/token (JSON tool results skew low)
# Note: 3.5 chars/token holds for plain prose; serialised tool results + JSON overhead
# bring the actual ratio to ~1.4. Observed: 2.4M chars → 1.7M tokens (2026-06-09).


def _estimate_chars(messages: list) -> int:
    total = 0
    for m in messages:
        c = m.get("content", "")
        if isinstance(c, str):
            total += len(c)
        elif isinstance(c, list):
            for block in c:
                if isinstance(block, dict):
                    total += len(str(block.get("text", "") or block.get("content", "")))
    return total


def _trim_messages(messages: list) -> list:
    """Trim messages so the estimated char count stays under _MAX_INPUT_CHARS.

    Strategy (in order):
    1. Truncate large tool_result content blocks (> 50k chars) to a summary.
    2. Drop oldest user+assistant pairs from the front (preserve at least the
       last user message so the agent always has the current question).
    """
    import copy
    msgs = copy.deepcopy(messages)

    # Step 1: truncate oversized tool results
    _TOOL_RESULT_CAP = 50_000
    for msg in msgs:
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_result":
                continue
            inner = block.get("content", "")
            if isinstance(inner, str) and len(inner) > _TOOL_RESULT_CAP:
                block["content"] = inner[:_TOOL_RESULT_CAP] + f"\n\n[... {len(inner) - _TOOL_RESULT_CAP} chars truncated to stay within context limit ...]"

    # Step 2: drop oldest pairs until we're under budget
    while _estimate_chars(msgs) > _MAX_INPUT_CHARS and len(msgs) > 1:
        # Always keep the last message (current user question)
        # Remove from the front in user+assistant pairs
        if msgs[0]["role"] == "user" and len(msgs) > 1:
            msgs.pop(0)
            if msgs and msgs[0]["role"] == "assistant":
                msgs.pop(0)
        else:
            msgs.pop(0)

    return msgs


def _apply_cache_breakpoint(messages: list) -> None:
    """Mark ONLY the last user message with cache_control.

    The Anthropic API allows a maximum of 4 cache_control blocks per request.
    System already uses 1–2 (SYSTEM_PROMPT + optional skill prompt).
    We must therefore ensure that at most 1 message block carries cache_control.

    Strategy:
      1. Strip cache_control from ALL existing message content blocks first.
      2. Add cache_control to the last block of the last user message only.

    Render order is tools → system → messages.  The system block already caches
    tools + system prompt.  This covers the growing conversation history so each
    iteration in the tool-use loop only sends the new content uncached.
    """
    # Step 1: remove any lingering cache_control from previous turns
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    block.pop("cache_control", None)

    # Step 2: mark only the last user message
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if msg["role"] != "user":
            continue
        content = msg["content"]
        if isinstance(content, str):
            messages[i] = {**msg, "content": [
                {"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}
            ]}
        elif isinstance(content, list) and content:
            last = content[-1]
            if isinstance(last, dict):
                last["cache_control"] = {"type": "ephemeral"}
        break


def run_agent(
    messages: list,
    client: anthropic.Anthropic,
    skill: str | None = None,
    verbose: bool = False,
    max_iterations: int = 15,
    max_tokens: int = 8192,
    request_timeout: float = 180.0,
) -> tuple[str, dict]:
    """Run one turn of the agent loop. Returns (final text, trace dict)."""

    _t_start = time.time()
    trace: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "skill": skill,
        "tools_called": [],
        "files_read": [],
        "iterations": 0,
        "total_duration_s": 0.0,
        "answer_chars": 0,
        "answer_preview": "",
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
    }

    system = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": datetime.now(_AMS).strftime("Today's date is %Y-%m-%d. Current time: %H:%M %Z (Amsterdam)."),
        },
    ]
    if skill and skill in SKILL_PROMPTS:
        system.append({
            "type": "text",
            "text": SKILL_PROMPTS[skill],
            "cache_control": {"type": "ephemeral"},
        })

    # Inject recent feedback so the agent avoids known failure patterns.
    # Not cached with cache_control — content changes as new feedback arrives.
    try:
        from feedback import load_gaps_context
        gaps_ctx = load_gaps_context()
        if gaps_ctx.strip():
            system.append({
                "type": "text",
                "text": (
                    "## Feedback log (07_Feedback/gaps.md)\n\n"
                    "Recente 👎-feedback van gebruikers op eerdere antwoorden. "
                    "Verwerk dit als context: vermijd patroonfouten die hier benoemd zijn, "
                    "en houd rekening met open items bij het formuleren van je antwoord.\n\n"
                    + gaps_ctx
                ),
            })
    except Exception as _gaps_err:
        logger.warning("gaps.md inject failed (non-fatal): %s", _gaps_err)

    # Inject kennis_laag.md — triangulated Minkowski knowledge confirmed across sources.
    try:
        from tools import load_kennis_context
        kennis_ctx = load_kennis_context()
        if kennis_ctx.strip():
            system.append({
                "type": "text",
                "text": (
                    "## Kennis-laag (06_Marketing/_kennis/kennis_laag.md)\n\n"
                    "Getrianguleerde Minkowski-kennis — bevestigd over meerdere onafhankelijke bronnen. "
                    "Gebruik als feitelijke achtergrond bij voorstellen, expert-matching en positioneringsvragen. "
                    "Zekerder naarmate meer onafhankelijke oorsprongen overeenstemmen.\n\n"
                    + kennis_ctx
                ),
            })
    except Exception as _kennis_err:
        logger.warning("kennis_laag inject failed (non-fatal): %s", _kennis_err)

    def _finish(text: str) -> tuple[str, dict]:
        trace["iterations"] = iteration
        trace["total_duration_s"] = round(time.time() - _t_start, 2)
        trace["answer_chars"] = len(text)
        trace["answer_preview"] = text[:600]
        return text, trace

    iteration = 0
    while True:
        iteration += 1
        if iteration > max_iterations:
            logger.warning("max_iterations (%d) reached — forcing final answer", max_iterations)
            messages.append({
                "role": "user",
                "content": (
                    "Je hebt genoeg bronmateriaal opgehaald. "
                    "Geef nu het eindantwoord zonder verdere tool-aanroepen."
                ),
            })
            _apply_cache_breakpoint(messages)
            final = client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                timeout=request_timeout,
            )
            text = "\n".join(b.text for b in final.content if b.type == "text").strip()
            messages.append({"role": "assistant", "content": final.content})
            trace["input_tokens"] += getattr(final.usage, "input_tokens", 0)
            trace["output_tokens"] += getattr(final.usage, "output_tokens", 0)
            trace["cache_creation_tokens"] += getattr(final.usage, "cache_creation_input_tokens", 0)
            trace["cache_read_tokens"] += getattr(final.usage, "cache_read_input_tokens", 0)
            return _finish(text or "Ik kon geen sluitend antwoord formuleren — probeer de vraag specifieker te stellen.")

        _api_t0 = time.time()
        input_chars = _estimate_chars(messages)
        logger.info("iteration %d — calling API (input ≈%d chars)", iteration, input_chars)
        if input_chars > _MAX_INPUT_CHARS:
            logger.warning("context too large (%d chars) — trimming before API call", input_chars)
            messages[:] = _trim_messages(messages)
            logger.info("after trim: %d chars", _estimate_chars(messages))
        _apply_cache_breakpoint(messages)

        # Retry up to 3× on rate-limit (429) with exponential backoff
        _retry_delays = [15, 45]
        for _attempt, _delay in enumerate(([0] + _retry_delays)):
            if _delay:
                logger.warning("rate limit hit — waiting %ds before retry %d/2", _delay, _attempt)
                time.sleep(_delay)
            try:
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=max_tokens,
                    system=system,
                    tools=TOOL_SCHEMAS,
                    messages=messages,
                    timeout=request_timeout,
                )
                break  # success
            except anthropic.RateLimitError:
                if _attempt < len(_retry_delays):
                    continue
                raise  # all retries exhausted
        logger.info(
            "iteration %d — API returned in %.1fs, stop_reason=%s | "
            "tokens: in=%d out=%d cache_created=%d cache_read=%d",
            iteration,
            time.time() - _api_t0,
            response.stop_reason,
            getattr(response.usage, "input_tokens", 0),
            getattr(response.usage, "output_tokens", 0),
            getattr(response.usage, "cache_creation_input_tokens", 0),
            getattr(response.usage, "cache_read_input_tokens", 0),
        )
        trace["input_tokens"] += getattr(response.usage, "input_tokens", 0)
        trace["output_tokens"] += getattr(response.usage, "output_tokens", 0)
        trace["cache_creation_tokens"] += getattr(response.usage, "cache_creation_input_tokens", 0)
        trace["cache_read_tokens"] += getattr(response.usage, "cache_read_input_tokens", 0)

        # Collect text from this response
        text_parts = []
        tool_uses = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        # If no tool calls, we're done
        if response.stop_reason == "end_turn" or not tool_uses:
            full_text = "\n".join(text_parts).strip()
            messages.append({"role": "assistant", "content": response.content})
            return _finish(full_text)

        # Stream partial text if any
        if text_parts and verbose:
            for part in text_parts:
                if part.strip():
                    print(f"\033[2m{part.strip()}\033[0m\n")

        # Process tool calls
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for tool_use in tool_uses:
            name = tool_use.name
            inp = tool_use.input

            preview = ", ".join(f"{k}={repr(v)[:40]}" for k, v in inp.items())
            print_tool_use(name, preview)

            _t0 = time.time()
            result = dispatch(name, inp)
            _dt = round(time.time() - _t0, 2)
            logger.info("[tool] %s took %.1fs, returned %d chars", name, _dt, len(result))

            trace["tools_called"].append({
                "name": name,
                "input_preview": preview[:200],
                "duration_s": _dt,
                "output_chars": len(result),
            })
            if name == "read_file" and "path" in inp:
                trace["files_read"].append(inp["path"])

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})


def chat_loop(skill: str | None, client: anthropic.Anthropic):
    """Interactive chat loop."""
    messages = []

    print_separator()
    print(f"\033[1mMinkowski Agent\033[0m  —  Commercial intelligence layer")
    print(f"Model: {MODEL}")
    if skill:
        print(f"Skill: {skill.upper()}")
    print("\nType your message. Enter a blank line to submit. Ctrl+C to exit.\n")

    # If a skill was specified, prime the conversation
    if skill and skill in SKILL_INTROS:
        intro = SKILL_INTROS[skill]
        print_agent(intro)
        messages.append({
            "role": "assistant",
            "content": intro,
        })

    while True:
        try:
            print("\033[1;33mYou\033[0m")
            lines = []
            while True:
                line = input()
                if line == "" and lines:
                    break
                lines.append(line)

            user_input = "\n".join(lines).strip()
            if not user_input:
                continue

            messages.append({"role": "user", "content": user_input})

            print()
            response_text, _trace = run_agent(messages, client, skill=skill, verbose=True)

            print_separator()
            print_agent(response_text)
            print_separator()

        except (KeyboardInterrupt, EOFError):
            print("\n\nExiting Minkowski Agent.")
            break


def export_conversations(since: str | None = None) -> None:
    """Dump conversations.db to logs/conversations_export_YYYY-MM-DD.jsonl."""
    import json as _json
    import sqlite3
    from memory import DB_PATH

    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    out_path = logs_dir / f"conversations_export_{today}.jsonl"

    with sqlite3.connect(DB_PATH) as con:
        if since:
            rows = con.execute(
                "SELECT thread_ts, messages, updated_at FROM conversations "
                "WHERE updated_at >= ? ORDER BY updated_at",
                (since,),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT thread_ts, messages, updated_at FROM conversations ORDER BY updated_at"
            ).fetchall()

    count = 0
    with out_path.open("w", encoding="utf-8") as f:
        for thread_ts, messages_json, updated_at in rows:
            record = {
                "thread_ts": thread_ts,
                "updated_at": updated_at,
                "messages": _json.loads(messages_json),
            }
            f.write(_json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    print(f"Exported {count} conversation(s) to {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Minkowski Agent — Commercial intelligence for Minkowski agency"
    )
    parser.add_argument(
        "--skill",
        choices=sorted(SKILL_PROMPTS.keys()),
        help="Start in a specific skill mode.",
    )
    parser.add_argument(
        "--api-key",
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var).",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export conversation history to logs/conversations_export_YYYY-MM-DD.jsonl and exit.",
    )
    parser.add_argument(
        "--since",
        metavar="YYYY-MM-DD",
        help="Only export conversations updated on or after this date (use with --export).",
    )
    args = parser.parse_args()

    if args.export:
        export_conversations(since=args.since)
        sys.exit(0)

    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set. Pass --api-key or set the env var.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    chat_loop(skill=args.skill, client=client)


if __name__ == "__main__":
    main()
