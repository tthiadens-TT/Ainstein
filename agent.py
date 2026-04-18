#!/usr/bin/env python3
"""
Minkowski Agent — Commercial intelligence layer for Minkowski agency.

Usage:
    python agent.py
    python agent.py --skill analyse_opportunity
    python agent.py --skill build_proposal
    python agent.py --skill match_experts
"""

import os
import sys
import argparse
import textwrap
from typing import Literal

import anthropic

from prompts import SYSTEM_PROMPT, SKILL_PROMPTS
from tools import TOOL_SCHEMAS, dispatch

MODEL = "claude-sonnet-4-6"

SKILL_INTROS = {
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
        choices=["analyse_opportunity", "build_proposal", "match_experts"],
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
