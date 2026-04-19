# Ainstein — Minkowski Commercial Intelligence Bot

Slack-based AI assistant that turns Minkowski's proposal history, expert
network, pricing logic, and positioning into a usable commercial layer.

For product intent, tone, and operating rules see [`CLAUDE.md`](./CLAUDE.md).
This README covers *how to run it*.

## Architecture at a glance

```
Slack event ──► slack_app.py (Bolt + Socket Mode)
                   │
                   ├── memory.py ◄─► conversations.db  (SQLite, per-thread)
                   │
                   └── agent.py (Anthropic tool loop, max 15 iterations)
                          │
                          └── tools.py (list_folder / read_file / search_files / web_search)
                                   │
                                   └── source layer (local + Google Drive)
```

## Source layer

Two locations, always searched in order:

1. **Primary — Google Drive**
   `/Users/thomasthiadens/Library/CloudStorage/GoogleDrive-tthiadens@gmail.com/.shortcut-targets-by-id/1ziMd8Zmhgpqq_iHyoz3-59_KwL7kbm7e/Thomas /AInstein`
2. **Secondary — local repo** (`01_Proposals/` … `06_Marketing/`)

When a folder exists in both, the Google Drive version wins *if* it has content.
See `tools._resolve_folder`.

| Folder | Content |
|---|---|
| `01_Proposals` | Past proposals — reused for wording, module combos, pricing |
| `02_Tools` | Canonical frameworks + facilitation formats (`02_Tools_Agent_README.md`) |
| `03_Pricing` | Decision matrix, worked examples, discount/escalation rules |
| `04_Experts` | Expert profiles (docx), decision layer JSON — lives mostly in Google Drive |
| `05_Venues` | Venue profiles + comparison matrix |
| `06_Marketing` | Positioning, message pillars, LinkedIn themes, one-pager template |
| `07_Feedback` | `gaps.md` — auto-appended by the 👎 feedback loop |

## Local setup

```bash
# 1. Clone & enter
cd Ainstein

# 2. (Optional but recommended) Git LFS for PDF attachments
#    .gitattributes already configured; binary activates once lfs is installed.
brew install git-lfs && git lfs install

# 3. Virtualenv
python3 -m venv .venv
source .venv/bin/activate

# 4. Install pinned deps
pip install -r requirements.lock

# 5. Configure secrets
cp .env.example .env
# edit .env — fill in ANTHROPIC_API_KEY, SLACK_BOT_TOKEN, SLACK_APP_TOKEN

# 6. Run
python slack_app.py
```

Logs go to stdout. For background runs we use:

```bash
nohup python3 -u slack_app.py > /tmp/ainstein_slack.log 2>&1 &
disown
```

The `-u` flag disables Python's stdout buffering — without it, errors and
timing logs do not appear in the file until the process exits.

## Slack app configuration

Enable Socket Mode and generate an App-Level Token (`xapp-…`).

**Bot scopes:** `app_mentions:read`, `chat:write`, `channels:history`,
`im:history`, `im:write`, `im:read`, `files:read` (for attachment parsing),
`reactions:read` (for the 👎 feedback loop), `users:read` (to capture the
reviewer's name in feedback entries).

**Event subscriptions:** `app_mention`, `message.im`, `reaction_added`.

**Slash commands:** `/analyse`, `/voorstel`, `/experts` — each maps to one of
the three primary skills in `CLAUDE.md`.

## Running tests

```bash
python3 -m pytest tests/ -q
```

Start by adding a test whenever you touch `memory.py` or the agent loop —
the 2026-04-18 `TextBlock is not JSON serializable` outage lived in that gap.

## Adding a new skill

1. Add the prompt to `prompts.py::SKILL_PROMPTS`.
2. Add auto-detection keywords to `slack_app._detect_skill`.
3. Wire a slash command in `slack_app.py` (follow `cmd_analyse` pattern).
4. Document the skill in `CLAUDE.md` under "Your Primary Skills".

## Operational notes

- **`web_search`** (DuckDuckGo) breaks regularly when the scraper changes shape.
  Failures now log loudly to stderr. See `tools.py::web_search`.
- **`_read_text` cache** is in-process and keyed by `(abspath, mtime)`. Across a
  single agent turn the same PDF is parsed once; across restarts the cache
  resets. Max 256 entries, FIFO eviction.
- **Conversation memory** is keyed by Slack `thread_ts`. `conversations.db`
  is in `.gitignore`; wipe it if the schema version bumps below the code
  version and you don't care about history.
- **SSL on macOS python.org builds**: `slack_app._configure_ssl()` is called
  from `__main__` only — importing `slack_app` as a module has no TLS side
  effects.

## Files that matter

| File | Role |
|---|---|
| `slack_app.py` | Bolt app, event handlers, slash commands, file attachments |
| `agent.py` | Anthropic tool loop with `max_iterations=15`, per-call `timeout=90s` |
| `tools.py` | `list_folder`, `read_file`, `search_files`, `web_search` + schemas |
| `prompts.py` | `SYSTEM_PROMPT` + per-skill prompts |
| `memory.py` | SQLite persistence with SDK-block serialization + schema versioning |
| `feedback.py` | 👎 reaction → "what could be better?" → `07_Feedback/gaps.md` |
| `CLAUDE.md` | Product and tone guidance (read by the agent at runtime) |
| `reviews/` | Daily commit review reports |

## Feedback loop

Users react 👎 on any bot answer in DM. The bot replies in-thread asking what
could be better. The user's next message in that thread is captured and
appended to `07_Feedback/gaps.md`. That folder is part of the source layer,
so future retrievals surface past gaps automatically.

Pending-feedback state is in-memory only — on bot restart it's lost. That's
acceptable: the user reacts again and gets re-prompted.
