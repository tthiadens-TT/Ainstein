# 07_Feedback

Learning loop for Ainstein. Every time someone reacts 👎 on a bot answer in Slack,
the bot asks one follow-up question — "what could be better?" — and the reply is
appended to `gaps.md`.

This folder is part of the source layer. `search_files` reads it on every
retrieval, so the next time a similar question comes up, past gaps are in context.

## Why markdown, not a database

Because you can:
- read it without SQL,
- edit it directly when you want to sharpen a note,
- version it in git,
- grep it from the command line.

If the log grows past ~500 entries, consider rolling monthly files (`gaps_2026-04.md`).

## How to read `gaps.md`

Each entry has:
- Timestamp + thread reference
- User
- The skill that was active (if detected)
- Excerpt of the bot's original answer
- The user's one-line critique

Patterns that show up multiple times = source-layer gaps. Act on them by
editing the relevant folder (`03_Pricing/`, `04_Experts/`, etc.) — that is
the real learning.
