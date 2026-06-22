#!/usr/bin/env python3
"""Ainstein Management Dashboard — leest logs/, schrijft dashboard/index.html"""
import json
import os
import pathlib
import re
import subprocess
from datetime import datetime, timezone, timedelta

BASE = pathlib.Path(__file__).parent.parent
DECISIONS_LOG = BASE / "logs" / "decisions.jsonl"
AINSTEIN_LOG = BASE / "logs" / "ainstein.log"
DRIVE_SNAPSHOT = BASE / "logs" / "drive_snapshot_latest.json"
OUTPUT = pathlib.Path(__file__).parent / "index.html"


COST_PER_M_INPUT = 3.0
COST_PER_M_OUTPUT = 15.0
AVG_INPUT_TOKENS_PER_ITER = 2000
OUTPUT_TOKENS_PER_CHAR = 0.25
EUR_RATE = 0.92


# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_ts(ts_str):
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def age_label(ts, now):
    """Human-readable age string from a timestamp."""
    if ts is None:
        return "onbekend"
    diff = now - ts
    hours = diff.total_seconds() / 3600
    if hours < 1:
        return "zojuist"
    if hours < 24:
        return f"{int(hours)}u geleden"
    days = diff.days
    if days == 1:
        return "gisteren"
    return f"{days} dagen geleden"


def traffic_light(age_hours):
    """Return (color, label) based on age in hours."""
    if age_hours is None:
        return "#C0392B", "onbekend"
    if age_hours < 24:
        return "#2A7A5A", "actief"
    if age_hours < 168:  # 7 days
        return "#E67E22", f"{int(age_hours / 24)}d geleden"
    return "#C0392B", f"{int(age_hours / 24)}d geleden"


def run_cmd(args, timeout=5):
    """Run a subprocess command, return stdout or None on failure."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def _dot(color, size=9):
    return f'<span style="display:inline-block;width:{size}px;height:{size}px;border-radius:50%;background:{color};margin-right:6px;vertical-align:middle;position:relative;top:-1px"></span>'


def _tip(content, tooltip):
    """Wrap content in a hover-tooltip span."""
    safe = tooltip.replace('"', '&quot;')
    return f'<span class="tip" data-tip="{safe}">{content}</span>'


SKILL_TIPS = {
    "analyse_opportunity": "Ainstein analyseerde een commerciële kans of klantbriefing.",
    "build_proposal": "Ainstein bouwde of verbeterde een voorstel.",
    "match_experts": "Ainstein zocht de juiste expert of facilitator.",
    "meeting_reviewer": "Ainstein analyseerde een vergaderverslag dat via Jamie binnenkwam.",
    "extract_knowledge": "Ainstein haalde nieuwe inzichten op uit Minkowski-bronnen.",
    "extract_knowledge_distilleer": "Ainstein verwerkte één bron naar gestructureerde kennis (stap 1 van 2).",
    "extract_knowledge_merge": "Ainstein combineerde alle distillaties tot een bijgewerkte kennislaag (stap 2 van 2).",
    "qualify_lead": "Ainstein beoordeelde of een lead het opvolgen waard is.",
    "prepare_discovery": "Ainstein bereidde een discovery-gesprek voor.",
    "map_objections": "Ainstein bracht bezwaren en tegenargumenten in kaart.",
    "client_discovery_debrief": "Ainstein verwerkte de uitkomsten van een discovery-gesprek.",
    "sharpen_positioning": "Ainstein scherpte de positionering van een aanbod aan.",
    "create_content": "Ainstein maakte content aan, zoals een artikel of LinkedIn-post.",
    "adapt_messaging": "Ainstein paste de boodschap aan op een specifieke doelgroep.",
    "debrief_to_messaging": "Ainstein vertaalde een debrief naar externe communicatie.",
    "refine_proposal": "Ainstein verfijnde een bestaand voorstel op basis van feedback.",
    "review_feedback": "Ainstein verwerkte feedback op een voorstel of document.",
    "dvv_check": "Ainstein controleerde een document op duidelijkheid, volledigheid en overtuigingskracht.",
    "(geen skill)": "Ainstein verwerkte een algemeen verzoek zonder specifieke werkvorm.",
}

SVC_TIPS = {
    "Anthropic API": "De AI-dienst achter Ainsteins intelligentie. Elke vraag die Ainstein verwerkt, gaat via Anthropic.",
    "Slack": "De chatverbinding waarmee Ainstein berichten ontvangt en verstuurt naar het team.",
    "Google Drive": "De documentenopslag met voorstellen, expertprofielen en methodologie. Ainstein zoekt hier altijd eerst.",
    "Jamie webhook": "De koppeling met Jamie. Na elke vergadering stuurt Jamie het transcript automatisch naar Ainstein.",
    "Tavily": "Een webzoekdienst voor actuele informatie buiten de eigen Minkowski-bronnen.",
    "SSL / DuckDNS": "Het beveiligingscertificaat en het domeinnaam-systeem. Beide zijn nodig om de Jamie-koppeling bereikbaar te houden.",
}


# ── Data loading ─────────────────────────────────────────────────────────────

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


def load_log_errors(max_lines=5000):
    """Parse ainstein.log for ERROR/CRITICAL lines. Returns list of (ts, msg)."""
    if not AINSTEIN_LOG.exists():
        return []
    errors = []
    pattern = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ \[.*?\] (ERROR|CRITICAL) (.+)$')
    try:
        lines = AINSTEIN_LOG.read_text(errors="replace").splitlines()
        for line in lines[-max_lines:]:
            m = pattern.match(line)
            if m:
                ts_str, level, msg = m.group(1), m.group(2), m.group(3)
                try:
                    ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                except ValueError:
                    ts = None
                errors.append((ts, level, msg[:200]))
    except Exception:
        pass
    return errors[-5:]


# ── VM health checks ──────────────────────────────────────────────────────────

def check_vm_health():
    """Run system checks. Returns dict with results (None = unavailable/local)."""
    result = {}

    svc = run_cmd(["systemctl", "is-active", "ainstein"])
    result["service_status"] = svc

    disk_raw = run_cmd(["df", "/home", "--output=pcent"])
    if disk_raw:
        lines = disk_raw.splitlines()
        pct_str = lines[-1].strip().replace("%", "") if lines else None
        try:
            result["disk_pct"] = int(pct_str)
        except (ValueError, TypeError):
            result["disk_pct"] = None
    else:
        result["disk_pct"] = None

    result["ssl_expires"] = None
    result["ssl_days"] = None
    cert_out = run_cmd(
        ["bash", "-c",
         "echo Q | openssl s_client -connect ainstein.duckdns.org:443"
         " -servername ainstein.duckdns.org 2>/dev/null"
         " | openssl x509 -enddate -noout 2>/dev/null"],
        timeout=10
    )
    if cert_out:
        m = re.search(r'notAfter=(.+)', cert_out)
        if m:
            try:
                exp = datetime.strptime(m.group(1).strip(), "%b %d %H:%M:%S %Y %Z")
                exp = exp.replace(tzinfo=timezone.utc)
                result["ssl_expires"] = exp
                result["ssl_days"] = (exp - datetime.now(timezone.utc)).days
            except ValueError:
                pass

    git_ts = run_cmd(["git", "-C", str(BASE), "log", "-1", "--format=%ai"])
    result["last_deploy"] = git_ts

    return result


# ── Service timestamps from decisions.jsonl ───────────────────────────────────

def extract_service_activity(entries, now):
    """Return last-seen timestamps for each external service."""
    svc = {
        "anthropic": None,
        "slack": None,
        "drive": None,
        "jamie": None,
        "tavily": None,
        "tavily_month": 0,
    }
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    for e in entries:
        ts = parse_ts(e.get("timestamp"))
        if ts is None:
            continue

        if svc["anthropic"] is None or ts > svc["anthropic"]:
            svc["anthropic"] = ts

        if e.get("user_id") or e.get("channel"):
            if svc["slack"] is None or ts > svc["slack"]:
                svc["slack"] = ts

        if e.get("files_read"):
            if svc["drive"] is None or ts > svc["drive"]:
                svc["drive"] = ts

        if e.get("skill") == "meeting_reviewer":
            if svc["jamie"] is None or ts > svc["jamie"]:
                svc["jamie"] = ts

        for tool in e.get("tools_called", []):
            if tool.get("name") == "web_search":
                if svc["tavily"] is None or ts > svc["tavily"]:
                    svc["tavily"] = ts
                if ts >= month_start:
                    svc["tavily_month"] += 1

    return svc


# ── Main metrics ─────────────────────────────────────────────────────────────

def compute_metrics(entries, vm, svc, errors, now):
    window_7d = now - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    parsed = [(parse_ts(e.get("timestamp")), e) for e in entries]
    parsed = [(ts, e) for ts, e in parsed if ts]
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
    kl_entries = [(ts, e) for ts, e in parsed if e.get("skill") in extract_skills]
    last_kl_ts = kl_entries[-1][0] if kl_entries else None
    kl_age_days = (now - last_kl_ts).days if last_kl_ts else None

    outcomes_filled = False
    if DRIVE_SNAPSHOT.exists():
        try:
            snapshot = json.loads(DRIVE_SNAPSHOT.read_text())
            real = [k for k in snapshot if "08_Outcomes" in k and "TEMPLATE" not in k]
            outcomes_filled = len(real) > 0
        except Exception:
            pass

    return {
        "generated_at": now.strftime("%d %b %Y, %H:%M UTC"),
        "last_activity": last_ts.strftime("%d %b %Y, %H:%M") if last_ts else None,
        "last_activity_ts": last_ts,
        "last_age_hours": last_age_hours,
        "messages_7d": messages_7d,
        "meetings_7d": meetings_7d,
        "top_skills": top_skills,
        "cost_eur": cost_usd * EUR_RATE,
        "cost_month_label": now.strftime("%B %Y"),
        "last_kl": last_kl_ts.strftime("%d %b %Y") if last_kl_ts else None,
        "kl_age_days": kl_age_days,
        "outcomes_filled": outcomes_filled,
        "total_entries": len(entries),
        "vm": vm,
        "svc": svc,
        "errors": errors,
        "now": now,
    }


# ── HTML rendering ────────────────────────────────────────────────────────────

def _status_color(age_hours):
    if age_hours is None:
        return "#C0392B", "Geen data"
    if age_hours < 24:
        return "#2A7A5A", "Actief"
    if age_hours < 72:
        return "#E67E22", "Inactief (>24u)"
    return "#C0392B", "Inactief (>72u)"


def render_card_status(m):
    vm = m["vm"]
    st_col, st_label = _status_color(m["last_age_hours"])

    if m["last_age_hours"] is None:
        st_tip = "Geen activiteit gevonden. Ainstein heeft nog geen verzoeken verwerkt, of het logboek is leeg."
    elif m["last_age_hours"] < 24:
        st_tip = "Ainstein heeft onlangs een verzoek ontvangen en verwerkt. Alles werkt normaal."
    elif m["last_age_hours"] < 72:
        st_tip = "Ainstein heeft meer dan een dag niets gedaan. Dit kan normaal zijn bij weinig gebruik — controleer wel even."
    else:
        st_tip = "Ainstein is al meer dan 3 dagen inactief. Controleer of de achtergrondservice nog draait op de server."

    svc_raw = vm.get("service_status")
    if svc_raw == "active":
        svc_col, svc_txt = "#2A7A5A", "actief"
    elif svc_raw == "inactive":
        svc_col, svc_txt = "#E67E22", "inactief"
    elif svc_raw == "failed":
        svc_col, svc_txt = "#C0392B", "gefaald"
    elif svc_raw is None:
        svc_col, svc_txt = "#8492A6", "n.v.t."
    else:
        svc_col, svc_txt = "#E67E22", svc_raw

    disk_pct = vm.get("disk_pct")
    if disk_pct is None:
        disk_col, disk_txt = "#8492A6", "n.v.t."
    elif disk_pct < 70:
        disk_col, disk_txt = "#2A7A5A", f"{disk_pct}%"
    elif disk_pct < 85:
        disk_col, disk_txt = "#E67E22", f"{disk_pct}% — let op"
    else:
        disk_col, disk_txt = "#C0392B", f"{disk_pct}% — vol!"

    ssl_days = vm.get("ssl_days")
    if ssl_days is None:
        ssl_col, ssl_txt = "#8492A6", "n.v.t."
    elif ssl_days > 30:
        ssl_col, ssl_txt = "#2A7A5A", f"geldig ({ssl_days}d)"
    elif ssl_days > 10:
        ssl_col, ssl_txt = "#E67E22", f"verloopt in {ssl_days}d"
    else:
        ssl_col, ssl_txt = "#C0392B", f"verloopt in {ssl_days}d!"

    deploy_txt = vm.get("last_deploy", "onbekend") or "onbekend"
    if deploy_txt and len(deploy_txt) > 16:
        deploy_txt = deploy_txt[:16]

    inactive_alert = ""
    if m["last_age_hours"] is None or m["last_age_hours"] >= 72:
        inactive_alert = '<div class="alert">Controleer of ainstein.service actief is op de VM.</div>'

    card_tip = "Geeft aan of Ainstein live en bereikbaar is. Gebaseerd op wanneer het systeem voor het laatst een verzoek verwerkte."
    svc_tip = "De achtergrondservice die Ainstein laat draaien. Stopt deze, dan reageert Ainstein nergens meer op — Slack noch Jamie."
    disk_tip = "Hoeveel opslagruimte er nog vrij is op de server. Bij meer dan 85% gebruik kan de server vastlopen en stopt Ainstein met reageren."
    ssl_tip = "Het beveiligingscertificaat voor HTTPS. Verloopt dit, dan werkt de koppeling met Jamie niet meer en geeft Slack een foutmelding."
    deploy_tip = "De datum van de laatste automatische code-update. Na elke wijziging in GitHub wordt dit automatisch bijgewerkt op de server."

    return f"""
  <div class="card" style="border-top-color:{st_col}">
    <div class="card-label">{_tip('Systeemstatus', card_tip)}</div>
    <div class="big" style="color:{st_col}">{_dot(st_col)}{_tip(st_label, st_tip)}</div>
    <div class="meta">Laatste activiteit: {m['last_activity'] or 'onbekend'}</div>
    {inactive_alert}
    <div class="divider"></div>
    <div class="row-items">
      <div class="row-item">
        <div class="row-label">{_tip('ainstein.service', svc_tip)}</div>
        <div class="row-val" style="color:{svc_col}">{_dot(svc_col, 8)}{svc_txt}</div>
      </div>
      <div class="row-item">
        <div class="row-label">{_tip('Schijfruimte', disk_tip)}</div>
        <div class="row-val" style="color:{disk_col}">{_dot(disk_col, 8)}{disk_txt}</div>
      </div>
      <div class="row-item">
        <div class="row-label">{_tip('SSL-certificaat', ssl_tip)}</div>
        <div class="row-val" style="color:{ssl_col}">{_dot(ssl_col, 8)}{ssl_txt}</div>
      </div>
      <div class="row-item">
        <div class="row-label">{_tip('Laatste deploy', deploy_tip)}</div>
        <div class="row-val">{deploy_txt}</div>
      </div>
    </div>
  </div>"""


def render_card_gebruik(m):
    card_tip = "Hoeveel Ainstein is gebruikt de afgelopen 7 dagen — berichten via Slack en vergaderingen via Jamie."
    msg_tip = "Het aantal keer dat iemand Ainstein een vraag of opdracht heeft gestuurd via Slack de afgelopen 7 dagen."
    meet_tip = "Het aantal vergaderingen dat Jamie automatisch heeft doorgestuurd naar Ainstein voor analyse en opvolging."

    skills_html = ""
    for skill, count in m["top_skills"]:
        tip = SKILL_TIPS.get(skill, "Een taak die Ainstein heeft uitgevoerd.")
        skills_html += f"""
      <div class="skill-row">
        <span class="skill-name">{_tip(skill, tip)}</span>
        <span class="skill-count">{count}×</span>
      </div>"""
    if not skills_html:
        skills_html = '<div class="skill-row muted">Geen activiteit</div>'

    return f"""
  <div class="card" style="border-top-color:#6BDBD8">
    <div class="card-label">{_tip('Gebruik — afgelopen 7 dagen', card_tip)}</div>
    <div class="kpi-row">
      <div>
        <div class="kpi-num">{m['messages_7d']}</div>
        <div class="kpi-label">{_tip('berichten', msg_tip)}</div>
      </div>
      <div>
        <div class="kpi-num">{m['meetings_7d']}</div>
        <div class="kpi-label">{_tip('meetings', meet_tip)}</div>
      </div>
    </div>
    <div class="skills-list">{skills_html}
    </div>
  </div>"""


def render_card_kosten(m):
    cost_str = f"≈ €{m['cost_eur']:.2f}" if m["cost_eur"] >= 0.01 else "< €0.01"
    tavily_pct = int(m["svc"]["tavily_month"] / 10)
    tavily_col = "#2A7A5A" if tavily_pct < 70 else "#E67E22" if tavily_pct < 90 else "#C0392B"

    card_tip = "Wat Ainstein deze maand heeft gekost aan externe diensten. Kosten voor de server (GCP) staan hier niet in."
    cost_tip = "Schatting op basis van het aantal aanroepen en de gemiddelde antwoordlengte. Voor exacte cijfers moeten tokens worden bijgehouden in het logboek."
    tavily_tip = "Tavily is de webzoekdienst die Ainstein gebruikt voor actuele informatie. Het gratis plan geeft 1.000 zoekopdrachten per maand — daarna stopt de dienst tot de volgende maand."

    return f"""
  <div class="card" style="border-top-color:#F5C842">
    <div class="card-label">{_tip('Kosten — ' + m['cost_month_label'], card_tip)}</div>
    <div class="big">{_tip(cost_str, cost_tip)}</div>
    <div class="meta">Anthropic API — {m['total_entries']} aanroepen totaal</div>
    <div class="divider"></div>
    <div class="row-items">
      <div class="row-item">
        <div class="row-label">{_tip('Tavily deze maand', tavily_tip)}</div>
        <div class="row-val" style="color:{tavily_col}">{_dot(tavily_col, 8)}{m['svc']['tavily_month']} / 1.000</div>
      </div>
    </div>
    <div class="hint">Anthropic: schatting op iteraties + antwoordlengte.<br>Exacte tracking: usage tokens toevoegen aan decisions.jsonl.</div>
  </div>"""


def render_card_kennislaag(m):
    if m["last_kl"] is None:
        kl_col, kl_label, kl_note = "#C0392B", "Nooit gedraaid", "Start run_kennisextractie.py"
        kl_tip = "De kennislaag is nog nooit bijgewerkt. Ainstein werkt zonder actuele kennis van Minkowski en kan daardoor minder scherp antwoorden."
    elif m["kl_age_days"] and m["kl_age_days"] > 30:
        kl_col = "#E67E22"
        kl_label = f"Laatste run: {m['last_kl']}"
        kl_note = f"{m['kl_age_days']} dagen geleden — vernieuwen aanbevolen"
        kl_tip = f"De kennislaag is {m['kl_age_days']} dagen oud. Nieuwe content op Minkowski-kanalen is nog niet verwerkt. Vernieuwen duurt ongeveer 10 minuten."
    else:
        kl_col = "#2A7A5A"
        kl_label = f"Laatste run: {m['last_kl']}"
        kl_note = "actueel"
        kl_tip = "De kennislaag is recent bijgewerkt. Ainstein beschikt over actuele kennis van Minkowski's methodologie, positionering en taal."

    out_col = "#2A7A5A" if m["outcomes_filled"] else "#C0392B"
    out_label = "Gevuld" if m["outcomes_filled"] else "Leeg — actie vereist"
    out_note = "win/loss records beschikbaar" if m["outcomes_filled"] else "NN IC + Cathalijne invullen (5 min)"
    out_tip = (
        "Er zijn win/loss-records beschikbaar van eerdere voorstellen. Ainstein kan hierop leunen om scherpere en betere voorstellen te schrijven."
        if m["outcomes_filled"] else
        "Geen records van gewonnen of verloren voorstellen. Ainstein mist daardoor een belangrijk referentiepunt bij het bouwen van nieuwe voorstellen."
    )

    card_tip = "Ainsteins geheugen van Minkowski — methodologie, positionering, en wat werkt in voorstellen. Hoe recenter bijgewerkt, hoe relevanter de antwoorden."

    return f"""
  <div class="card" style="border-top-color:{kl_col}">
    <div class="card-label">{_tip('Kennislaag', card_tip)}</div>
    <div class="big" style="color:{kl_col};font-size:18px;line-height:1.4">{_tip(kl_label, kl_tip)}</div>
    <div class="meta">{kl_note}</div>
    <div class="divider"></div>
    <div class="row-label" style="margin-bottom:6px">{_tip('08_Outcomes', 'Win/loss-records van eerdere voorstellen. Ainstein gebruikt dit om te leren wat werkt en wat niet.')}</div>
    <div>{_dot(out_col)}<strong style="color:{out_col};font-size:14px">{_tip(out_label, out_tip)}</strong></div>
    <div class="meta" style="margin-top:4px">{out_note}</div>
  </div>"""


def render_card_diensten(m):
    now = m["now"]
    svc = m["svc"]

    def svc_row(label, ts, extra=""):
        age_hours = (now - ts).total_seconds() / 3600 if ts else None
        col, _ = traffic_light(age_hours)
        age = age_label(ts, now)
        tip = SVC_TIPS.get(label, "Een externe dienst waar Ainstein gebruik van maakt.")
        return f"""
      <div class="svc-row">
        <div class="svc-name">{_dot(col, 9)}{_tip(label, tip)}</div>
        <div class="svc-age">{age}{' — ' + extra if extra else ''}</div>
      </div>"""

    tavily_extra = f"{svc['tavily_month']}/1.000 calls"

    rows = (
        svc_row("Anthropic API", svc["anthropic"])
        + svc_row("Slack", svc["slack"])
        + svc_row("Google Drive", svc["drive"])
        + svc_row("Jamie webhook", svc["jamie"])
        + svc_row("Tavily", svc["tavily"], tavily_extra)
    )

    ssl_days = m["vm"].get("ssl_days")
    ssl_tip = SVC_TIPS["SSL / DuckDNS"]
    if ssl_days is not None:
        if ssl_days > 30:
            ssl_col = "#2A7A5A"
        elif ssl_days > 10:
            ssl_col = "#E67E22"
        else:
            ssl_col = "#C0392B"
        ssl_extra = f"cert verloopt in {ssl_days}d"
        rows += f"""
      <div class="svc-row">
        <div class="svc-name">{_dot(ssl_col, 9)}{_tip('SSL / DuckDNS', ssl_tip)}</div>
        <div class="svc-age">{ssl_extra}</div>
      </div>"""
    else:
        rows += f"""
      <div class="svc-row">
        <div class="svc-name">{_dot('#8492A6', 9)}{_tip('SSL / DuckDNS', ssl_tip)}</div>
        <div class="svc-age">n.v.t. (lokaal)</div>
      </div>"""

    card_tip = "De externe diensten waar Ainstein van afhankelijk is. Als een dienst rood staat, kan dat een oorzaak zijn als Ainstein niet goed reageert."

    return f"""
  <div class="card" style="border-top-color:#1B2E5E">
    <div class="card-label">{_tip('Diensten', card_tip)}</div>
    <div class="svc-list">{rows}
    </div>
    <div class="hint" style="margin-top:12px">
      Groen = gezien &lt;24u &nbsp;·&nbsp; Oranje = 1–7d &nbsp;·&nbsp; Rood = &gt;7d of nooit
    </div>
  </div>"""


def render_card_fouten(m):
    errors = m["errors"]

    card_tip = "De laatste technische foutmeldingen uit het logboek van Ainstein. Een enkele fout is zelden urgent — een reeks fouten wel."
    error_tip = "Een fout die is opgetreden, maar het systeem draait nog. Kan een tijdelijk probleem zijn — controleer of het zich herhaalt."
    critical_tip = "Een ernstige fout. Het systeem werkt mogelijk niet meer correct en verdient directe aandacht."

    if not errors:
        content = '<div class="no-errors">Geen fouten gevonden in ainstein.log</div>'
    else:
        rows = ""
        for ts, level, msg in reversed(errors):
            ts_str = ts.strftime("%d %b %H:%M") if ts else "?"
            level_col = "#C0392B" if level == "CRITICAL" else "#E67E22"
            tip = critical_tip if level == "CRITICAL" else error_tip
            rows += f"""
        <div class="error-row">
          <div class="error-meta">
            <span class="error-ts">{ts_str}</span>
            <span class="error-level" style="color:{level_col}">{_tip(level, tip)}</span>
          </div>
          <div class="error-msg">{msg}</div>
        </div>"""
        content = rows

    if not AINSTEIN_LOG.exists():
        content = '<div class="no-errors muted">ainstein.log niet gevonden (lokaal?)</div>'

    return f"""
  <div class="card" style="border-top-color:#C0392B">
    <div class="card-label">{_tip('Recente fouten', card_tip)}</div>
    <div class="error-list">{content}
    </div>
    <div class="hint" style="margin-top:10px">
      Zie ook: <code>logs/ainstein.log</code> op de VM voor volledig logboek
    </div>
  </div>"""


# ── Full page ─────────────────────────────────────────────────────────────────

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  background: #F5F3EE;
  color: #1B2E5E;
  min-height: 100vh;
}
header {
  background: #1B2E5E;
  color: #F5F3EE;
  padding: 22px 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.brand { font-size: 18px; font-weight: 700; letter-spacing: -0.01em; }
.brand em { color: #F5C842; font-style: normal; }
.subtitle { font-size: 11px; opacity: 0.5; margin-top: 4px; letter-spacing: 0.06em; text-transform: uppercase; }
.generated { font-size: 11px; opacity: 0.4; text-align: right; line-height: 1.6; }
main {
  max-width: 980px;
  margin: 36px auto;
  padding: 0 24px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
}
.card {
  background: #fff;
  border-radius: 8px;
  padding: 24px 26px;
  box-shadow: 0 1px 3px rgba(27,46,94,0.07), 0 4px 16px rgba(27,46,94,0.04);
  border-top: 3px solid transparent;
  overflow: visible;
}
.card-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #9AA5BE;
  margin-bottom: 14px;
}
.big { font-size: 30px; font-weight: 700; letter-spacing: -0.02em; line-height: 1; }
.meta { font-size: 13px; color: #7A89A8; margin-top: 6px; }
.divider { border-top: 1px solid #F0EDE6; margin: 16px 0; }
.hint { font-size: 11px; color: #B0BAD4; line-height: 1.5; margin-top: 8px; }
.alert {
  margin-top: 12px;
  background: #FEF2E8;
  border-left: 3px solid #E67E22;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 12px;
  color: #7A4500;
}
/* VM health rows */
.row-items { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 16px; }
.row-item {}
.row-label { font-size: 10px; color: #9AA5BE; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 3px; }
.row-val { font-size: 13px; font-weight: 600; color: #1B2E5E; }
/* KPI */
.kpi-row { display: flex; gap: 28px; margin-top: 12px; }
.kpi-num { font-size: 30px; font-weight: 700; letter-spacing: -0.02em; color: #1B2E5E; }
.kpi-label { font-size: 10px; color: #9AA5BE; margin-top: 3px; text-transform: uppercase; letter-spacing: 0.05em; }
/* Skills */
.skills-list { margin-top: 16px; border-top: 1px solid #F0EDE6; padding-top: 12px; }
.skill-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 0;
  font-size: 13px;
  border-bottom: 1px solid #F7F5F0;
}
.skill-row:last-child { border-bottom: none; }
.skill-name { color: #1B2E5E; }
.skill-count { font-weight: 600; }
.skill-row.muted { color: #9AA5BE; font-style: italic; justify-content: center; }
/* Services */
.svc-list { display: flex; flex-direction: column; gap: 0; }
.svc-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 7px 0;
  border-bottom: 1px solid #F7F5F0;
  font-size: 13px;
}
.svc-row:last-child { border-bottom: none; }
.svc-name { font-weight: 500; color: #1B2E5E; }
.svc-age { color: #7A89A8; font-size: 12px; }
/* Errors */
.error-list { display: flex; flex-direction: column; gap: 8px; margin-top: 4px; }
.error-row {
  background: #FFF8F7;
  border-left: 3px solid #E8B4B0;
  border-radius: 4px;
  padding: 8px 10px;
}
.error-meta { display: flex; gap: 10px; align-items: center; margin-bottom: 3px; }
.error-ts { font-size: 11px; color: #9AA5BE; }
.error-level { font-size: 10px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }
.error-msg { font-size: 12px; color: #3A2020; font-family: monospace; word-break: break-word; }
.no-errors { font-size: 13px; color: #2A7A5A; padding: 12px 0; }
.no-errors.muted { color: #9AA5BE; }
footer {
  text-align: center;
  padding: 24px;
  font-size: 11px;
  color: #9AA5BE;
}
footer a { color: #1B2E5E; text-decoration: none; opacity: 0.6; }
footer a:hover { opacity: 1; }
@media (max-width: 640px) {
  main { grid-template-columns: 1fr; margin: 20px auto; }
  header { padding: 16px 20px; flex-wrap: wrap; }
  .row-items { grid-template-columns: 1fr; }
}

/* ── Tooltips ── */
.tip {
  position: relative;
  cursor: help;
  text-decoration: underline;
  text-decoration-style: dotted;
  text-decoration-color: rgba(27,46,94,0.22);
  text-underline-offset: 3px;
}
.tip::after {
  content: attr(data-tip);
  position: absolute;
  bottom: calc(100% + 10px);
  left: 50%;
  transform: translateX(-50%);
  background: #1B2E5E;
  color: #F5F3EE;
  font-size: 12px;
  font-weight: 400;
  font-style: normal;
  letter-spacing: 0;
  text-transform: none;
  text-decoration: none;
  white-space: normal;
  width: 230px;
  padding: 9px 13px;
  border-radius: 6px;
  line-height: 1.55;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.14s ease;
  z-index: 300;
  box-shadow: 0 4px 18px rgba(27,46,94,0.20);
}
.tip::before {
  content: '';
  position: absolute;
  bottom: calc(100% + 4px);
  left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-top-color: #1B2E5E;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.14s ease;
  z-index: 300;
}
.tip:hover::after,
.tip:hover::before { opacity: 1; }
"""


def render(m):
    c1 = render_card_status(m)
    c2 = render_card_gebruik(m)
    c3 = render_card_kosten(m)
    c4 = render_card_kennislaag(m)
    c5 = render_card_diensten(m)
    c6 = render_card_fouten(m)

    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ainstein Dashboard</title>
<style>{CSS}</style>
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
{c1}
{c2}
{c3}
{c4}
{c5}
{c6}
</main>

<footer>
  <strong>ainstein-vm</strong> · GCP · 35.253.206.86 &nbsp;·&nbsp;
  <a href="https://ainstein.duckdns.org" target="_blank">ainstein.duckdns.org</a>
  &nbsp;·&nbsp;
  <a href="slack://channel?team=T0B0ABL6T&id=C0B6B69Q812">#ainstein-status</a>
</footer>

</body>
</html>"""


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print("Ainstein dashboard generator...")
    now = datetime.now(timezone.utc)
    entries = load_decisions()
    print(f"  {len(entries)} entries uit decisions.jsonl")
    errors = load_log_errors()
    print(f"  {len(errors)} ERROR-regels gevonden in ainstein.log")
    vm = check_vm_health()
    print(f"  VM-checks: service={vm.get('service_status')}, disk={vm.get('disk_pct')}%, ssl={vm.get('ssl_days')}d")
    svc = extract_service_activity(entries, now)
    m = compute_metrics(entries, vm, svc, errors, now)
    html = render(m)
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"  Gegenereerd: {OUTPUT}")


if __name__ == "__main__":
    main()
