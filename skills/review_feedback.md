# Skill: review_feedback

## Purpose
Turn the raw feedback log into concrete improvement actions. Bridge the gap between "we logged a 👎" and "the source layer is now better."

This is the loop-closing skill. Without it, `gaps.md` just grows; with it, patterns become edits.

## When to Use
- The user runs `/feedback-review` or asks for "feedback review", "feedback patronen", "review feedback"
- Recommended cadence: weekly or after every ~10 new entries — but only when the user asks

## Inputs to Retrieve
1. Read `05_Ainstein Knowledge Base/gaps.md` in full (use `read_file`)
2. Optional: list `05_Ainstein Knowledge Base/reviews/` so you don't repeat actions already proposed in a recent review

If `gaps.md` is empty or has fewer than 3 entries: say so explicitly and stop. A review on 1–2 entries is noise, not signal.

## Steps

### 1. Parse and group
Group entries by:
- `Type` (technical vs qualitative) — these need different actions
- `Category` (sub-label)
- `Skill` (where present)

### 2. Identify patterns
A pattern is one of:
- ≥2 entries with the same `Type` × `Category` combination
- ≥2 entries pointing at the same skill
- A clear thematic cluster across entries (e.g. "pricing" mentioned in 3 unrelated complaints)

Single-entry observations are noted but not promoted to "patterns" — they go in a separate "Singletons" section.

### 3. Propose ONE concrete action per pattern
For **technical** patterns:
- Identify which skill prompt or tool needs adjustment
- Propose: "Update `skills/<name>.md` — add instruction: <one line>"
- Or: "Tool `<name>` returns wrong result for <case> — fix in `tools.py`"

For **qualitative** patterns:
- Identify which source folder is thin or wrong
- Propose: "Add to `0X_Folder/<file>.md`: <specific content type>"
- Or: "Source layer missing — create `<folder>/<filename>.md` with: <what should be in it>"

Every action must be:
- Specific (file path + what changes)
- Self-contained (Thomas can act without asking follow-up)
- One per pattern — don't bundle

### 4. Write the report
Write the report to `05_Ainstein Knowledge Base/reviews/YYYY-MM-DD.md` using the `read_file` + filesystem tools available. (If you cannot write to the source layer directly, output the report content in your reply and tell the user to save it manually with the suggested filename.)

## Output Format

```
# Feedback Review — YYYY-MM-DD

## Summary
- Entries reviewed: <N>
- Date range: <oldest> → <newest>
- Patterns found: <M>

## Technical patterns (<N>)
### Pattern 1: <type>/<category> — <one-line theme>
- Entries: <count>, threads: <list of thread ids>
- **Proposed action:** <specific edit>
- **File to change:** <path>

(repeat per pattern)

## Qualitative patterns (<N>)
(same structure)

## Singletons (logged but not yet a pattern)
- <one line per singleton entry, just for awareness>

## Next-step priority
Rank the proposed actions 1..N by expected impact + ease. Top 3 are what Thomas should do this week.
```

## Operating Rules
- Never modify the source layer or `gaps.md` yourself in this skill — only propose. Thomas decides.
- If a pattern's root cause is unclear from the log, say so and ask Thomas to add context to those entries.
- Don't pad the report. If there are 2 patterns, write 2 patterns. No filler.
- Be specific about file paths. "Update the prompt" is useless; "Update `skills/analyse_opportunity.md`, add: …" is actionable.
