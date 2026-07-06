# What's Your Future? Facilitator Guide

## What This Is

A live discovery instrument for Minkowski facilitators to run with executive leadership teams in their first conversation. The tool walks through three futures (probable, plausible, preferable) via the Cone of Possibilities, captures the leadership team's signals on confidence, urgency, and readiness, and surfaces a Futures Readiness stance that opens the next conversation. The tool is never sent to clients as a self-service link. A Minkowski facilitator drives it on the meeting room display.

## Open It in 60 Seconds

Double-click `index.html`. The tool works offline, no installation needed. Open it full screen on the meeting room display. Before the meeting, step through the flow once to check the sector and theme options load correctly, and test that the summary copy-to-clipboard function works.

## Running the Conversation

**Setup**: Enter the organisation name at the start. This appears on all screens and the final summary.

**Sector and Theme**: Let the client choose. The choice is diagnostic. What they pick tells you what's on their minds; what they skip tells you what they are not thinking about. Ask "why that sector?" and "what makes this theme urgent for you now?" Record their answers mentally.

**Each Scenario Screen** (Probable, Plausible, Preferable): Read the scenario aloud. Sit with the leadership question. Silence is fine. Leadership teams often need space to think. Once they answer, move on. Do not re-read.

**The Three Sliders**: The client answers each. When they move a slider, ask "Why not one higher? Why not one lower?" Their reasoning is more valuable than the number. The first two sliders ask how prepared the organisation is for the probable and plausible futures; the third asks how actively they are shaping the preferable one. That difference matters: preparing is not the same as shaping.

**The Signal Screen**: The tool generates a Futures Readiness stance. Hand it to the client neutrally. Say what it says. Do not interpret it. Use it as a conversation opener: "What would it take to move this? What's the one thing we need to focus on first?"

## After the Meeting

Press "Copy session summary" (button on the final screen). Paste it into Minkowski Slack `#ainstein-status` so Ainstein, Minkowski's AI colleague, can pick it up as discovery input and prepare next steps. Use the "Print" button to give the client a take-home single page.

## Keeping the Scenarios Current

Scenario texts are hardcoded in `data.js` with a visible "Signals as of" date. Refresh them quarterly. Ask Ainstein to regenerate the scenario set against fresh signals (new market data, emerging risks, shifts in leadership thinking), then replace `data.js`. Never let the date run more than a quarter behind reality.

## Files

- **index.html**: Entry point. Loads styles and app logic. Opens full screen without navigation chrome.
- **styles.css**: Minkowski brand colors, typography, spacing. Card layouts for scenario cards and signal display.
- **app.js**: Application logic. Handles sector and theme selection, scenario progression, slider capture, summary generation, and copy-to-clipboard.
- **data.js**: Scenario texts, leadership questions, signal thresholds, and readiness language. Only file you need to refresh for content updates.
