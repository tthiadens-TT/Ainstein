#!/usr/bin/env python3
"""Ainstein Management Dashboard — leest logs/, schrijft dashboard/index.html"""
import json
import pathlib
from datetime import datetime, timezone, timedelta

BASE = pathlib.Path(__file__).parent.parent
DECISIONS_LOG = BASE / "logs" / "decisions.jsonl"
DRIVE_SNAPSHOT = BASE / "logs" / "drive_snapshot_latest.json"
OUTPUT = pathlib.Path(__file__).parent / "index.html"

# Sonnet 4.6 pricing (USD/M tokens)
COST_PER_M_INPUT = 3.0
COST_PER_M_OUTPUT = 15.0
AVG_INPUT_TOKENS_PER_ITER = 2000
OUTPUT_TOKENS_PER_CHAR = 0.25  # 4 chars/token
EUR_RATE = 0.92


def load_decisions():
    if not DECISIONS_LOG.exists():
        return []
    entries = []
    with open(DECISIONS_LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def parse_ts(ts_str):
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def compute_metrics(entries):
    now = datetime.now(timezone.utc)
    window_7d = now - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    parsed = [(parse_ts(e.get("timestamp", "")), e) for e in entries]
    parsed = [(ts, e) for ts, e in parsed if ts is not None]
    parsed.sort(key=lambda x: x[0])

    last_ts = parsed[-1][0] if parsed else None
    last_age_hours = (now - last_ts).total_seconds() / 3600 if last_ts else None

    recent_7d = [(ts, e) for ts, e in parsed if ts >= window_7d]
    messages_7d = len(recent_7d)
    meetings_7d = sum(1 for _, e in recent_7d if e.get("skill") == "meeting_reviewer")

    skill_counts = {}
    for _, e in recent_7d:
        s = e.get("skill") or "(geen skill)"
        skill_counts[s] = skill_counts.get(s, 0) + 1
    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    cost_usd = 0.0
    for ts, e in parsed:
        if ts >= month_start:
            iters = e.get("iterations", 1)
            answer_chars = e.get("answer_chars", 0)
            input_tokens = iters * AVG_INPUT_TOKENS_PER_ITER
            output_tokens = answer_chars * OUTPUT_TOKENS_PER_CHAR
            cost_usd += (input_tokens * COST_PER_M_INPUT + output_tokens * COST_PER_M_OUTPUT) / 1_000_000

    extract_skills = {"extract_knowledge", "extract_knowledge_distilleer", "extract_knowledge_merge"}
    knowledge_entries = [(ts, e) for ts, e in parsed if e.get("skill") in extract_skills]
    last_knowledge_ts = knowledge_entries[-1][0] if knowledge_entries else None
    knowledge_age_days = (now - last_knowledge_ts).days if last_knowledge_ts else None

    outcomes_filled = False
    if DRIVE_SNAPSHOT.exists():
        try:
            snapshot = json.loads(DRIVE_SNAPSHOT.read_text())
            outcomes_real = [k for k in snapshot if "08_Outcomes" in k and "TEMPLATE" not in k]
            outcomes_filled = len(outcomes_real) > 0
        except Exception:
            pass

    return {
        "generated_at": now.strftime("%d %b %Y, %H:%M UTC"),
        "last_activity": last_ts.strftime("%d %b %Y, %H:%M") if last_ts else None,
        "last_age_hours": last_age_hours,
        "messages_7d": messages_7d,
        "meetings_7d": meetings_7d,
        "top_skills": top_skills,
        "cost_eur": cost_usd * EUR_RATE,
        "cost_month_label": now.strftime("%B %Y"),
        "last_knowledge_run": last_knowledge_ts.strftime("%d %b %Y") if last_knowledge_ts else None,
        "knowledge_age_days": knowledge_age_days,
        "outcomes_filled": outcomes_filled,
        "total_entries": len(entries),
    }


def _status(age_hours):
    if age_hours is None:
        return "#C0392B", "Geen data"
    if age_hours < 24:
        return "#2A7A5A", "Actief"
    if age_hours < 72:
        return "#E67E22", "Inactief (>24u)"
    return "#C0392B", "Inactief (>72u)"


def render(m):
    status_col, status_label = _status(m["last_age_hours"])

    skills_html = ""
    for skill, count in m["top_skills"]:
        bar_pct = int(count / max(1, m["messages_7d"]) * 100)
        skills_html += f"""
        <div class="skill-row">
          <span class="skill-name">{skill}</span>
          <span class="skill-count">{count}×</span>
        </div>"""
    if not skills_html:
        skills_html = '<div class="skill-row muted">Geen activiteit</div>'

    cost_str = f"≈ €{m['cost_eur']:.2f}" if m["cost_eur"] >= 0.01 else "< €0.01"
    cost_note = "schatting — gebruik ×" + str(m["total_entries"]) + " aanroepen totaal"

    inactive_alert = ""
    if m["last_age_hours"] is None or m["last_age_hours"] >= 72:
        inactive_alert = '<div class="alert">Controleer of ainstein.service actief is.</div>'

    if m["last_knowledge_run"] is None:
        kl_col, kl_label, kl_note = "#C0392B", "Nooit gedraaid", "Start run_kennisextractie.py handmatig"
    elif m["knowledge_age_days"] and m["knowledge_age_days"] > 30:
        kl_col = "#E67E22"
        kl_label = f"Laatste run: {m['last_knowledge_run']}"
        kl_note = f"{m['knowledge_age_days']} dagen geleden — vernieuwen aanbevolen"
    else:
        kl_col = "#2A7A5A"
        kl_label = f"Laatste run: {m['last_knowledge_run']}"
        kl_note = "actueel"

    out_col = "#2A7A5A" if m["outcomes_filled"] else "#C0392B"
    out_label = "Gevuld" if m["outcomes_filled"] else "Leeg — actie vereist"
    out_note = "win/loss records beschikbaar" if m["outcomes_filled"] else "NN IC + Cathalijne invullen (5 min)"

    last_activity = m["last_activity"] or "onbekend"

    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ainstein Dashboard</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  background: #F5F3EE;
  color: #1B2E5E;
  min-height: 100vh;
}}
header {{
  background: #1B2E5E;
  color: #F5F3EE;
  padding: 22px 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}}
.brand {{ font-size: 18px; font-weight: 700; letter-spacing: -0.01em; }}
.brand em {{ color: #F5C842; font-style: normal; }}
.subtitle {{ font-size: 12px; opacity: 0.55; margin-top: 3px; letter-spacing: 0.04em; text-transform: uppercase; }}
.generated {{ font-size: 11px; opacity: 0.45; text-align: right; line-height: 1.5; }}
main {{
  max-width: 960px;
  margin: 36px auto;
  padding: 0 24px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
}}
.card {{
  background: #fff;
  border-radius: 8px;
  padding: 26px 28px;
  box-shadow: 0 1px 3px rgba(27,46,94,0.07), 0 4px 16px rgba(27,46,94,0.04);
  border-top: 3px solid transparent;
}}
.card-label {{
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #9AA5BE;
  margin-bottom: 14px;
}}
.big {{ font-size: 32px; font-weight: 700; letter-spacing: -0.02em; line-height: 1; }}
.meta {{ font-size: 13px; color: #7A89A8; margin-top: 6px; }}
.dot {{
  display: inline-block;
  width: 9px; height: 9px;
  border-radius: 50%;
  margin-right: 7px;
  vertical-align: middle;
  position: relative; top: -1px;
}}
.kpi-row {{ display: flex; gap: 24px; margin-top: 12px; }}
.kpi-num {{ font-size: 30px; font-weight: 700; letter-spacing: -0.02em; color: #1B2E5E; }}
.kpi-label {{ font-size: 11px; color: #9AA5BE; margin-top: 3px; text-transform: uppercase; letter-spacing: 0.05em; }}
.skills-list {{ margin-top: 18px; border-top: 1px solid #F0EDE6; padding-top: 14px; }}
.skill-row {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  font-size: 13px;
  border-bottom: 1px solid #F7F5F0;
}}
.skill-row:last-child {{ border-bottom: none; }}
.skill-name {{ color: #1B2E5E; }}
.skill-count {{ font-weight: 600; color: #1B2E5E; }}
.skill-row.muted {{ color: #9AA5BE; font-style: italic; justify-content: center; }}
.divider {{ border-top: 1px solid #F0EDE6; margin: 16px 0; }}
.alert {{
  margin-top: 12px;
  background: #FEF2E8;
  border-left: 3px solid #E67E22;
  border-radius: 4px;
  padding: 9px 12px;
  font-size: 12px;
  color: #7A4500;
}}
.hint {{
  margin-top: 10px;
  font-size: 11px;
  color: #B0BAD4;
  line-height: 1.5;
}}
footer {{
  text-align: center;
  padding: 28px;
  font-size: 11px;
  color: #9AA5BE;
}}
footer a {{ color: #1B2E5E; text-decoration: none; opacity: 0.7; }}
footer a:hover {{ opacity: 1; }}
@media (max-width: 620px) {{
  main {{ grid-template-columns: 1fr; margin: 20px auto; }}
  header {{ padding: 16px 20px; flex-wrap: wrap; }}
}}
</style>
</head>
<body>

<header>
  <div>
    <div class="brand">Minkowski <em>/</em> Ainstein</div>
    <div class="subtitle">Management Dashboard</div>
  </div>
  <div class="generated">Gegenereerd op<br>{m['generated_at']}</div>
</header>

<main>

  <!-- Systeemstatus -->
  <div class="card" style="border-top-color:{status_col}">
    <div class="card-label">Systeemstatus</div>
    <div class="big" style="color:{status_col}">
      <span class="dot" style="background:{status_col}"></span>{status_label}
    </div>
    <div class="meta">Laatste activiteit: {last_activity}</div>
    {inactive_alert}
  </div>

  <!-- Gebruik 7 dagen -->
  <div class="card" style="border-top-color:#6BDBD8">
    <div class="card-label">Gebruik — afgelopen 7 dagen</div>
    <div class="kpi-row">
      <div>
        <div class="kpi-num">{m['messages_7d']}</div>
        <div class="kpi-label">berichten</div>
      </div>
      <div>
        <div class="kpi-num">{m['meetings_7d']}</div>
        <div class="kpi-label">meetings (Jamie)</div>
      </div>
    </div>
    <div class="skills-list">{skills_html}
    </div>
  </div>

  <!-- Kosten -->
  <div class="card" style="border-top-color:#F5C842">
    <div class="card-label">Kosten — {m['cost_month_label']}</div>
    <div class="big">{cost_str}</div>
    <div class="meta">{cost_note}</div>
    <div class="hint">Schatting op basis van iteraties en antwoordlengte.<br>
    Exacte tracking: usage tokens toevoegen aan decisions.jsonl.</div>
  </div>

  <!-- Kennislaag -->
  <div class="card" style="border-top-color:{kl_col}">
    <div class="card-label">Kennislaag</div>
    <div class="big" style="color:{kl_col}; font-size:20px; line-height:1.3">{kl_label}</div>
    <div class="meta">{kl_note}</div>
    <div class="divider"></div>
    <div style="font-size:10px; font-weight:700; letter-spacing:0.1em; text-transform:uppercase; color:#9AA5BE; margin-bottom:8px;">08_Outcomes</div>
    <div>
      <span class="dot" style="background:{out_col}"></span>
      <strong style="color:{out_col}; font-size:14px">{out_label}</strong>
    </div>
    <div class="meta" style="margin-top:4px">{out_note}</div>
  </div>

</main>

<footer>
  <strong>ainstein-vm</strong> · GCP · 35.253.206.86 &nbsp;·&nbsp;
  <a href="https://ainstein.duckdns.org" target="_blank">ainstein.duckdns.org</a>
  &nbsp;·&nbsp;
  <a href="slack://channel?team=T0B0ABL6T&id=C0B6B69Q812">#ainstein-status</a>
</footer>

</body>
</html>"""


def main():
    print("Ainstein dashboard generator...")
    entries = load_decisions()
    print(f"  {len(entries)} entries geladen")
    m = compute_metrics(entries)
    html = render(m)
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"  Gegenereerd: {OUTPUT}")
    print(f"  Status: {m['last_activity'] or 'onbekend'}")
    print(f"  Gebruik 7d: {m['messages_7d']} berichten, {m['meetings_7d']} meetings")
    print(f"  Kosten {m['cost_month_label']}: €{m['cost_eur']:.4f}")
    print(f"  08_Outcomes gevuld: {m['outcomes_filled']}")


if __name__ == "__main__":
    main()
