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
from typing import Literal

import anthropic
from dotenv import load_dotenv

# Load .env from the repo root so ANTHROPIC_API_KEY etc. are available
# regardless of caller's working directory.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

from prompts import SYSTEM_PROMPT, SKILL_PROMPTS
from tools import TOOL_SCHEMAS, dispatch

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
}


def print_separator():
    print("\n" + "─" * 60 + "\n")


def print_agent(text: str):
    print(f"\033[1;36mMinkowski Agent\033[0m")
    print(textwrap.fill(text, width=80, subsequent_indent="  ") if len(text) < 200 else text)
    print()


def print_tool_use(name: str, input_preview: str):
    print(f"\033[2m  [{name}] {input_preview}\033[0m")


def run_agent(
    messages: list,
    client: anthropic.Anthropic,
    skill: str | None = None,
    verbose: bool = False,
    max_iterations: int = 15,
) -> str:
    """Run one turn of the agent loop. Returns the final text response."""

    system = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    if skill and skill in SKILL_PROMPTS:
        system.append({
            "type": "text",
            "text": SKILL_PROMPTS[skill],
            "cache_control": {"type": "ephemeral"},
        })

    iteration = 0
    while True:
        iteration += 1
        if iteration > max_iterations:
            print(f"[agent] max_iterations ({max_iterations}) reached — forcing final answer", flush=True)
            # Nudge the model to wrap up without more tool calls
            messages.append({
                "role": "user",
                "content": (
                    "Je hebt genoeg bronmateriaal opgehaald. "
                    "Geef nu het eindantwoord zonder verdere tool-aanroepen."
                ),
            })
            final = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=system,
                messages=messages,
            )
            text = "\n".join(b.text for b in final.content if b.type == "text").strip()
            messages.append({"role": "assistant", "content": final.content})
            return text or "Ik kon geen sluitend antwoord formuleren — probeer de vraag specifieker te stellen."

        import time as _time
        _api_t0 = _time.time()
        input_chars = sum(
            len(str(m.get("content", ""))) for m in messages
        )
        print(f"[agent] iteration {iteration} — calling API (input ≈{input_chars} chars)", flush=True)
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system,
            tools=TOOL_SCHEMAS,
            messages=messages,
            timeout=90.0,
        )
        print(f"[agent] iteration {iteration} — API returned in {_time.time()-_api_t0:.1f}s, stop_reason={response.stop_reason}", flush=True)

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
            return full_text

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

            # Show what's being retrieved
            preview = ", ".join(f"{k}={repr(v)[:40]}" for k, v in inp.items())
            print_tool_use(name, preview)

            import time as _time
            _t0 = _time.time()
            result = dispatch(name, inp)
            _dt = _time.time() - _t0
            print(f"[tool] {name} took {_dt:.1f}s, returned {len(result)} chars", flush=True)
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
            response_text = run_agent(messages, client, skill=skill, verbose=True)

            print_separator()
            print_agent(response_text)
            print_separator()

        except (KeyboardInterrupt, EOFError):
            print("\n\nExiting Minkowski Agent.")
            break


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
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set. Pass --api-key or set the env var.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    chat_loop(skill=args.skill, client=client)


if __name__ == "__main__":
    main()
