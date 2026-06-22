#!/usr/bin/env python3
"""Ainstein Management Dashboard — leest logs/, schrijft dashboard/index.html"""
import base64
import json
import os
import pathlib
import re
import subprocess
from datetime import datetime, timezone, timedelta

BASE = pathlib.Path(__file__).parent.parent

# Laad .env zodat credential-checks werken (ook als cron/deploy geen env-vars heeft)
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=BASE / ".env", override=False)
except ImportError:
    pass
DECISIONS_LOG = BASE / "logs" / "decisions.jsonl"
AINSTEIN_LOG = BASE / "logs" / "ainstein.log"
DRIVE_SNAPSHOT = BASE / "logs" / "drive_snapshot_latest.json"
LOGO_PATH = pathlib.Path(__file__).parent / "minkowski_logo.png"
FONT_PATH = BASE / "assets" / "fonts" / "Sen-ExtraBold.ttf"
OUTPUT = pathlib.Path(__file__).parent / "index.html"

COST_PER_M_INPUT = 3.0
COST_PER_M_OUTPUT = 15.0
AVG_INPUT_TOKENS_PER_ITER = 2000
OUTPUT_TOKENS_PER_CHAR = 0.25
EUR_RATE = 0.92

# Approximate monthly cost (EUR) per GCP machine type, europe-west4, on-demand
GCP_COST_TABLE = {
    "e2-micro": 7.11,
    "e2-small": 14.21,
    "e2-medium": 28.42,
    "e2-standard-2": 56.85,
    "e2-standard-4": 113.70,
    "n1-standard-1": 23.43,
    "n1-standard-2": 46.86,
    "f1-micro": 4.28,
    "g1-small": 14.46,
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_ts(ts_str):
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def age_label(ts, now):
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


def run_cmd(args, timeout=5):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def load_asset_b64(path, mime):
    if path.exists():
        return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"
    return None


def _dot(color, size=9):
    return (f'<span style="display:block;width:{size}px;height:{size}px;'
            f'border-radius:50%;background:{color};margin-right:7px;'
            f'flex-shrink:0;margin-top:2px"></span>')


def _tip(content, tooltip):
    safe = tooltip.replace('"', '&quot;')
    return f'<span class="tip" data-tip="{safe}">{content}</span>'


def _badge(ok, label_ok="werkt", label_fail="fout"):
    if ok is True:
        return f'<span class="badge badge-ok">{label_ok}</span>'
    if ok is False:
        return f'<span class="badge badge-fail">{label_fail}</span>'
    return '<span class="badge badge-unknown">onbekend</span>'


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

    # CPU load (1-min average from /proc/loadavg)
    load_raw = run_cmd(["cat", "/proc/loadavg"])
    if load_raw:
        try:
            result["load_1m"] = float(load_raw.split()[0])
        except (ValueError, IndexError):
            result["load_1m"] = None
    else:
        result["load_1m"] = None

    # Memory (from free -m)
    mem_raw = run_cmd(["free", "-m"])
    result["mem_pct"] = None
    result["mem_total_mb"] = None
    if mem_raw:
        for line in mem_raw.splitlines():
            if line.startswith("Mem:"):
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        total = int(parts[1])
                        used = int(parts[2])
                        result["mem_total_mb"] = total
                        result["mem_pct"] = round(used / total * 100) if total else None
                    except ValueError:
                        pass

    # SSL cert expiry
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


def check_service_connectivity():
    """Live connectivity checks per dienst. Werkt alleen correct op de VM."""
    c = {}

    # Flask /health — retry 3× (service kan net hergestart zijn bij deploy)
    import time as _time
    health_raw = None
    for _attempt in range(3):
        health_raw = run_cmd(
            ["bash", "-c", "curl -sf --max-time 3 http://127.0.0.1:8080/health"],
            timeout=5
        )
        if health_raw is not None:
            break
        if _attempt < 2:
            _time.sleep(3)
    c["flask"] = health_raw is not None

    # Anthropic API key aanwezig
    c["anthropic"] = bool(os.environ.get("ANTHROPIC_API_KEY"))

    # Slack — live auth.test call (verifieert token én bereikbaarheid Slack API)
    import urllib.request as _urllib
    slack_token = os.environ.get("SLACK_BOT_TOKEN", "")
    if slack_token:
        try:
            req = _urllib.Request(
                "https://slack.com/api/auth.test",
                data=b"",
                headers={"Authorization": f"Bearer {slack_token}"},
                method="POST",
            )
            with _urllib.urlopen(req, timeout=5) as resp:
                c["slack"] = json.loads(resp.read()).get("ok", False)
        except Exception:
            c["slack"] = False
    else:
        c["slack"] = False

    # Google Drive service account bestand aanwezig en leesbaar
    sa_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "")
    c["drive"] = bool(sa_path and pathlib.Path(sa_path).exists())

    # Jamie webhook secret aanwezig
    c["jamie"] = bool(os.environ.get("JAMIE_WEBHOOK_SECRET"))

    # Tavily API key aanwezig
    c["tavily"] = bool(os.environ.get("TAVILY_API_KEY"))

    # SocketMode heartbeat — slack_app.py schrijft elke 30 min via auth.test
    hb_file = BASE / "logs" / "socketmode_heartbeat.txt"
    c["socketmode_age_h"] = None
    c["socketmode_ok"] = None
    if hb_file.exists():
        try:
            from datetime import datetime as _dt, timezone as _tz
            hb_raw = hb_file.read_text().strip()
            hb_ts = _dt.fromisoformat(hb_raw.replace("Z", "+00:00"))
            hb_age_h = (_dt.now(_tz.utc) - hb_ts).total_seconds() / 3600
            # Heartbeat elke 30 min → stale als >1.5u (mist 3 cycli)
            c["socketmode_age_h"] = round(hb_age_h, 1)
            c["socketmode_ok"] = hb_age_h < 1.5
        except Exception:
            pass

    return c


def get_gcp_info():
    """Haal GCP instance type op via metadata server. Werkt alleen op GCP."""
    out = run_cmd(
        ["bash", "-c",
         "curl -sf --max-time 2 "
         "'http://metadata.google.internal/computeMetadata/v1/instance/machine-type' "
         "-H 'Metadata-Flavor: Google'"],
        timeout=4
    )
    instance_type = None
    if out:
        # Format: projects/PROJECT_ID/zones/ZONE/machineTypes/e2-micro
        instance_type = out.split("/")[-1] if "/" in out else out

    cost = GCP_COST_TABLE.get(instance_type) if instance_type else None
    return {"instance_type": instance_type, "monthly_eur": cost}


# ── Service timestamps from decisions.jsonl ───────────────────────────────────

def extract_service_activity(entries, now):
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

def compute_metrics(entries, vm, svc, svc_health, gcp, errors, now):
    window_7d = now - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    parsed = [(parse_ts(e.get("timestamp")), e) for e in entries]
    parsed = [(ts, e) for ts, e in parsed if ts]
    parsed.sort(key=lambda x: x[0])

    last_ts = parsed[-1][0] if parsed else None
    last_age_hours = (now - last_ts).total_seconds() / 3600 if last_ts else None

    recent_7d = [(ts, e) for ts, e in parsed if ts >= window_7d]
    messages_7d = sum(1 for _, e in recent_7d if e.get("channel") or e.get("user_id"))
    meetings_7d = sum(1 for _, e in recent_7d if e.get("skill") == "meeting_reviewer")

    prev_start = now - timedelta(days=14)
    prev_7d = [(ts, e) for ts, e in parsed if prev_start <= ts < window_7d]
    prev_messages = sum(1 for _, e in prev_7d if e.get("channel") or e.get("user_id"))
    prev_meetings = sum(1 for _, e in prev_7d if e.get("skill") == "meeting_reviewer")

    jamie_entries = [(ts, e) for ts, e in parsed if e.get("skill") == "meeting_reviewer"]
    last_jamie_ts = jamie_entries[-1][0] if jamie_entries else None
    last_jamie_title = jamie_entries[-1][1].get("meeting_title", "") if jamie_entries else None
    meetings_month = sum(1 for ts, e in parsed if ts >= month_start and e.get("skill") == "meeting_reviewer")

    skill_counts = {}
    for _, e in recent_7d:
        s = e.get("skill") or "(geen skill)"
        skill_counts[s] = skill_counts.get(s, 0) + 1
    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    cost_usd = 0.0
    cost_is_exact = False
    for ts, e in parsed:
        if ts >= month_start:
            in_tok = e.get("input_tokens")
            out_tok = e.get("output_tokens")
            if in_tok and out_tok:
                cost_usd += (in_tok * COST_PER_M_INPUT + out_tok * COST_PER_M_OUTPUT) / 1_000_000
                cost_is_exact = True
            else:
                iters = e.get("iterations", 1)
                answer_chars = e.get("answer_chars", 0)
                input_tokens = iters * AVG_INPUT_TOKENS_PER_ITER
                output_tokens = answer_chars * OUTPUT_TOKENS_PER_CHAR
                cost_usd += (input_tokens * COST_PER_M_INPUT + output_tokens * COST_PER_M_OUTPUT) / 1_000_000

    extract_skills = {"extract_knowledge", "extract_knowledge_distilleer", "extract_knowledge_merge"}
    kl_entries = [(ts, e) for ts, e in parsed if e.get("skill") in extract_skills]
    last_kl_ts = kl_entries[-1][0] if kl_entries else None
    kl_age_days = (now - last_kl_ts).days if last_kl_ts else None

    # Futures Ready metrics
    window_30d = now - timedelta(days=30)
    skills_30d = set()
    for ts, e in parsed:
        if ts >= window_30d and e.get("skill"):
            skills_30d.add(e.get("skill"))
    files_read_all = set()
    for _, e in parsed:
        for f in (e.get("files_read") or []):
            files_read_all.add(f)
    n_bronnen = 0
    bronnen_file = BASE / "scripts" / "bronnen.json"
    if bronnen_file.exists():
        try:
            n_bronnen = len(json.loads(bronnen_file.read_text()))
        except Exception:
            pass

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
        "prev_messages": prev_messages,
        "prev_meetings": prev_meetings,
        "last_jamie_ts": last_jamie_ts,
        "last_jamie_title": last_jamie_title,
        "meetings_month": meetings_month,
        "top_skills": top_skills,
        "cost_anthropic_eur": cost_usd * EUR_RATE,
        "cost_is_exact": cost_is_exact,
        "cost_month_label": now.strftime("%B %Y"),
        "last_kl": last_kl_ts.strftime("%d %b %Y") if last_kl_ts else None,
        "kl_age_days": kl_age_days,
        "outcomes_filled": outcomes_filled,
        "total_entries": len(entries),
        "_entries": entries,
        "skills_30d": skills_30d,
        "n_files_read": len(files_read_all),
        "n_bronnen": n_bronnen,
        "vm": vm,
        "svc": svc,
        "svc_health": svc_health,
        "gcp": gcp,
        "errors": errors,
        "now": now,
    }


# ── Alert en trend helpers ────────────────────────────────────────────────────

def _trend_arrow(current, previous):
    """Geeft (pijl, kleur, context-tekst) terug voor gebruik naast een KPI."""
    if previous == 0 and current == 0:
        return "", "#8492A6", ""
    if previous == 0:
        return "↑", "#2A7A5A", "was 0"
    pct = (current - previous) / previous
    if pct > 0.15:
        return "↑", "#2A7A5A", f"was {previous}"
    if pct < -0.15:
        return "↓", "#C0392B", f"was {previous}"
    return "=", "#8492A6", f"was {previous}"


def build_alert_signals(m):
    """Bepaal de ernst en geef een lijst van problemen terug."""
    issues = []
    severity = "ok"

    vm = m["vm"]
    h = m["svc_health"]

    def _add(level, msg):
        nonlocal severity
        issues.append(msg)
        if level == "critical" or (level == "warning" and severity == "ok"):
            severity = level

    svc_st = vm.get("service_status")
    if svc_st and svc_st not in ("active",):
        _add("critical", f"ainstein.service {svc_st}")

    if h.get("flask") is False:
        _add("critical", "Flask reageert niet (/health)")

    ssl_days = vm.get("ssl_days")
    if ssl_days is not None and ssl_days < 10:
        _add("critical", f"SSL verloopt in {ssl_days} dagen")
    elif ssl_days is not None and ssl_days < 30:
        _add("warning", f"SSL verloopt in {ssl_days} dagen")

    disk = vm.get("disk_pct")
    if disk and disk > 85:
        _add("critical", f"Schijf {disk}% vol")
    elif disk and disk > 75:
        _add("warning", f"Schijf {disk}% — bijna vol")

    for svc_key, label in [("anthropic", "Anthropic"), ("slack", "Slack"),
                             ("drive", "Google Drive"), ("jamie", "Jamie")]:
        if h.get(svc_key) is False:
            _add("warning", f"{label} niet geconfigureerd")

    tavily_n = m["svc"].get("tavily_month", 0)
    if tavily_n > 900:
        _add("critical", f"Tavily {tavily_n}/1.000")
    elif tavily_n > 750:
        _add("warning", f"Tavily {tavily_n}/1.000")

    age_h = m.get("last_age_hours")
    if age_h and age_h > 72:
        _add("warning", f"Geen activiteit in {int(age_h / 24)} dagen")

    return severity, issues


def render_alert_bar(m):
    severity, issues = build_alert_signals(m)

    if severity == "ok":
        return (
            '<div class="alert-bar alert-ok">'
            '<span class="alert-icon">✓</span>'
            'Alles OK — Ainstein actief, alle koppelingen werken'
            '</div>'
        )

    bg = "#B91C1C" if severity == "critical" else "#B45309"
    label = "Actie vereist" if severity == "critical" else "Let op"
    icon = "✕" if severity == "critical" else "!"
    items_html = " &nbsp;·&nbsp; ".join(f"<strong>{i}</strong>" for i in issues)

    ping_script = """
<script>
function ainsteinPing() {
  var btn = document.getElementById('ping-btn');
  if (!btn) return;
  btn.disabled = true;
  btn.textContent = 'Bezig...';
  var issues = [];
  document.querySelectorAll('.alert-bar strong').forEach(function(el) { issues.push(el.textContent); });
  fetch('/webhooks/ping', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({issues: issues.join(', ') || 'dashboard-alert'})
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    btn.textContent = data.ok ? '✓ Ping verstuurd naar #ainstein-status' : ('✕ ' + (data.error || 'fout'));
    btn.style.background = data.ok ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.3)';
  })
  .catch(function() { btn.textContent = '✕ Netwerk fout'; btn.style.background = 'rgba(0,0,0,0.3)'; });
}
</script>"""

    ping_btn = (
        '<button id="ping-btn" onclick="ainsteinPing()" '
        'style="margin-left:16px;padding:4px 14px;border:none;border-radius:4px;'
        'background:rgba(255,255,255,0.2);color:#fff;cursor:pointer;font-size:13px;'
        'white-space:nowrap;vertical-align:middle">'
        'Ping #ainstein-status</button>'
    )

    return (
        ping_script
        + f'<div class="alert-bar" style="background:{bg};display:flex;align-items:center;flex-wrap:wrap;gap:6px">'
        + f'<span class="alert-icon">{icon}</span>'
        + f'<span>{label}: {items_html}</span>'
        + ping_btn
        + '</div>'
    )


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
        st_tip = "Nog geen activiteit geregistreerd. Ainstein heeft nog geen verzoek verwerkt."
    elif m["last_age_hours"] < 24:
        st_tip = "Ainstein heeft onlangs een verzoek verwerkt. Alles werkt normaal."
    elif m["last_age_hours"] < 72:
        st_tip = "Ainstein heeft meer dan een dag niets gedaan. Dit kan normaal zijn bij weinig gebruik."
    else:
        st_tip = "Ainstein is al meer dan 3 dagen inactief. Controleer of de service draait."

    svc_raw = vm.get("service_status")
    if svc_raw == "active":
        svc_col, svc_txt = "#2A7A5A", "actief"
    elif svc_raw == "inactive":
        svc_col, svc_txt = "#E67E22", "inactief"
    elif svc_raw == "failed":
        svc_col, svc_txt = "#C0392B", "gefaald"
    else:
        svc_col, svc_txt = "#8492A6", "n.v.t."

    disk_pct = vm.get("disk_pct")
    if disk_pct is None:
        disk_col, disk_txt = "#8492A6", "n.v.t."
    elif disk_pct < 70:
        disk_col, disk_txt = "#2A7A5A", f"{disk_pct}%"
    elif disk_pct < 85:
        disk_col, disk_txt = "#E67E22", f"{disk_pct}% — let op"
    else:
        disk_col, disk_txt = "#C0392B", f"{disk_pct}% — vol!"

    # CPU load
    load = vm.get("load_1m")
    if load is None:
        cpu_col, cpu_txt = "#8492A6", "n.v.t."
    elif load < 0.8:
        cpu_col, cpu_txt = "#2A7A5A", f"{load:.2f} (laag)"
    elif load < 1.5:
        cpu_col, cpu_txt = "#E67E22", f"{load:.2f} (gemiddeld)"
    else:
        cpu_col, cpu_txt = "#C0392B", f"{load:.2f} (hoog)"

    # Memory
    mem_pct = vm.get("mem_pct")
    mem_total = vm.get("mem_total_mb")
    if mem_pct is None:
        mem_col, mem_txt = "#8492A6", "n.v.t."
    elif mem_pct < 70:
        mem_col, mem_txt = "#2A7A5A", f"{mem_pct}%"
    elif mem_pct < 85:
        mem_col, mem_txt = "#E67E22", f"{mem_pct}% — let op"
    else:
        mem_col, mem_txt = "#C0392B", f"{mem_pct}% — vol!"
    if mem_total:
        mem_txt += f" / {round(mem_total/1024, 1)} GB"

    ssl_days = vm.get("ssl_days")
    if ssl_days is None:
        ssl_col, ssl_txt = "#8492A6", "n.v.t."
    elif ssl_days > 30:
        ssl_col, ssl_txt = "#2A7A5A", f"geldig ({ssl_days}d)"
    elif ssl_days > 10:
        ssl_col, ssl_txt = "#E67E22", f"verloopt in {ssl_days}d"
    else:
        ssl_col, ssl_txt = "#C0392B", f"verloopt in {ssl_days}d!"

    deploy_txt = (vm.get("last_deploy") or "onbekend")[:16]

    inactive_alert = ""
    if m["last_age_hours"] is None or m["last_age_hours"] >= 72:
        inactive_alert = '<div class="alert">Controleer of ainstein.service actief is op de VM.</div>'

    svc_tip = "De achtergrondservice op de server. Stopt deze, dan reageert Ainstein nergens meer op."
    disk_tip = "Opslagruimte op de server. Bij meer dan 85% gebruik kan de server vastlopen."
    cpu_tip = "CPU-belasting (load average, 1 minuut). Boven 1.5 is de server zwaar belast."
    mem_tip = "RAM-gebruik op de server. Bij meer dan 85% kan Ainstein trager worden of crashen."
    ssl_tip = "Het HTTPS-certificaat. Verloopt dit, dan werkt de Jamie-koppeling niet meer."
    deploy_tip = "Datum van de laatste automatische code-update vanuit GitHub."

    return f"""
  <div class="card" style="border-top-color:{st_col}">
    <div class="card-label">{_tip('Systeemstatus', 'Of Ainstein actief is en de server gezond — gebaseerd op wanneer het systeem voor het laatst een verzoek verwerkte.')}</div>
    <div class="big" style="color:{st_col}">{_dot(st_col)}{_tip(st_label, st_tip)}</div>
    <div class="meta">Laatste gebruik: {m['last_activity'] or 'onbekend'}</div>
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
        <div class="row-label">{_tip('CPU load', cpu_tip)}</div>
        <div class="row-val" style="color:{cpu_col}">{_dot(cpu_col, 8)}{cpu_txt}</div>
      </div>
      <div class="row-item">
        <div class="row-label">{_tip('Geheugen', mem_tip)}</div>
        <div class="row-val" style="color:{mem_col}">{_dot(mem_col, 8)}{mem_txt}</div>
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

    msg_arr, msg_col, msg_ctx = _trend_arrow(m["messages_7d"], m["prev_messages"])
    meet_arr, meet_col, meet_ctx = _trend_arrow(m["meetings_7d"], m["prev_meetings"])

    msg_tip = "Het aantal keer dat iemand Ainstein via Slack een vraag of opdracht heeft gestuurd."
    meet_tip = "Het aantal Jamie-vergaderingen dat Ainstein heeft ontvangen en geanalyseerd."

    # Jamie-blok
    now = m["now"]
    last_jts = m.get("last_jamie_ts")
    last_jtitle = m.get("last_jamie_title") or "—"
    if len(last_jtitle) > 44:
        last_jtitle = last_jtitle[:42] + "…"
    jamie_age = age_label(last_jts, now) if last_jts else "nooit"
    meetings_month = m.get("meetings_month", 0)
    jamie_tip = "De meest recente vergadering die Jamie naar Ainstein heeft doorgestuurd en die Ainstein heeft geanalyseerd."

    return f"""
  <div class="card" style="border-top-color:#98D2CF">
    <div class="card-label">{_tip('Gebruik — afgelopen 7 dagen', 'Hoeveel Ainstein is gebruikt: berichten via Slack en vergaderingen via Jamie.')}</div>
    <div class="kpi-row">
      <div>
        <div class="kpi-num">
          {m['messages_7d']}
          {f'<span class="trend" style="color:{msg_col}">{msg_arr}</span>' if msg_arr else ''}
        </div>
        <div class="kpi-label">{_tip('berichten', msg_tip)}</div>
        {f'<div class="trend-ctx">{msg_ctx}</div>' if msg_ctx else ''}
      </div>
      <div>
        <div class="kpi-num">
          {m['meetings_7d']}
          {f'<span class="trend" style="color:{meet_col}">{meet_arr}</span>' if meet_arr else ''}
        </div>
        <div class="kpi-label">{_tip('meetings', meet_tip)}</div>
        {f'<div class="trend-ctx">{meet_ctx}</div>' if meet_ctx else ''}
      </div>
    </div>
    <div class="divider"></div>
    <div class="jamie-block">
      <div class="row-label" style="margin-bottom:6px">{_tip('Laatste Jamie-meeting', jamie_tip)}</div>
      <div class="jamie-title">{last_jtitle}</div>
      <div class="jamie-meta">{jamie_age} &nbsp;·&nbsp; {meetings_month} deze maand</div>
    </div>
    <div class="skills-list">{skills_html}
    </div>
  </div>"""


def render_card_kosten(m):
    cost_a = m["cost_anthropic_eur"]
    cost_a_str = f"≈ €{cost_a:.2f}" if cost_a >= 0.01 else "< €0.01"

    gcp = m["gcp"]
    instance = gcp.get("instance_type")
    gcp_cost = gcp.get("monthly_eur")
    if gcp_cost is not None:
        gcp_str = f"≈ €{gcp_cost:.2f}/mnd"
        gcp_type = f"({instance})"
    elif instance:
        gcp_str = "onbekend"
        gcp_type = f"({instance})"
    else:
        gcp_str = "n.v.t."
        gcp_type = "(lokaal)"

    tavily_pct = int(m["svc"]["tavily_month"] / 10)
    tavily_col = "#2A7A5A" if tavily_pct < 70 else "#E67E22" if tavily_pct < 90 else "#C0392B"

    anthropic_tip = (
        "Exacte kosten op basis van geregistreerde tokens." if m.get("cost_is_exact")
        else "Schatting op basis van het aantal aanroepen en de gemiddelde antwoordlengte."
    )
    gcp_tip = "De maandelijkse serverkosten op Google Cloud Platform. Loopt 24/7, ongeacht gebruik."
    tavily_tip = "Webzoekdienst voor actuele informatie. Het gratis plan geeft 1.000 zoekopdrachten per maand."

    total_eur = cost_a + (gcp.get("monthly_eur") or 0.0)
    total_str = f"€{total_eur:.2f}/mnd" if gcp.get("monthly_eur") else ""

    hint_txt = (
        "Anthropic: exacte kosten op basis van tokens."
        if m.get("cost_is_exact")
        else "Anthropic: schatting. Exacte tracking: tokens worden nu gelogd, zichtbaar na volgende aanroep."
    )

    return f"""
  <div class="card" style="border-top-color:#A4B187">
    <div class="card-label">{_tip('Kosten — ' + m['cost_month_label'], 'Wat Ainstein deze maand kost aan externe diensten.')}</div>
    <div class="row-items" style="margin-top:4px">
      <div class="row-item">
        <div class="row-label">{_tip('Anthropic API', anthropic_tip)}</div>
        <div class="row-val">{_tip(cost_a_str, anthropic_tip)}</div>
        <div style="font-size:11px;color:#B0BAD4;margin-top:2px">{m['total_entries']} aanroepen</div>
      </div>
      <div class="row-item">
        <div class="row-label">{_tip('Google Cloud VM', gcp_tip)}</div>
        <div class="row-val">{_tip(gcp_str, gcp_tip)}</div>
        <div style="font-size:11px;color:#B0BAD4;margin-top:2px">{gcp_type}</div>
      </div>
      {('<div class="row-item"><div class="row-label" style="color:#001C40;font-weight:700">Totaal/mnd</div><div class="row-val" style="font-weight:700">' + total_str + '</div></div>') if total_str else ''}
    </div>
    <div class="divider"></div>
    <div class="row-items">
      <div class="row-item">
        <div class="row-label">{_tip('Tavily deze maand', tavily_tip)}</div>
        <div class="row-val" style="color:{tavily_col}">{_dot(tavily_col, 8)}{m['svc']['tavily_month']} / 1.000</div>
      </div>
    </div>
    <div class="hint">{hint_txt}</div>
  </div>"""


def render_card_kennislaag(m):
    if m["last_kl"] is None:
        kl_col, kl_label, kl_note = "#C0392B", "Nooit gedraaid", "Start run_kennisextractie.py"
        kl_tip = "De kennislaag is nog nooit bijgewerkt. Ainstein mist actuele kennis van Minkowski."
    elif m["kl_age_days"] and m["kl_age_days"] > 30:
        kl_col = "#E67E22"
        kl_label = f"Laatste run: {m['last_kl']}"
        kl_note = f"{m['kl_age_days']} dagen geleden — vernieuwen aanbevolen"
        kl_tip = f"De kennislaag is {m['kl_age_days']} dagen oud. Nieuwe content is nog niet verwerkt. Vernieuwen duurt ~10 min."
    else:
        kl_col = "#2A7A5A"
        kl_label = f"Laatste run: {m['last_kl']}"
        kl_note = "actueel"
        kl_tip = "De kennislaag is recent bijgewerkt. Ainstein heeft actuele kennis van Minkowski."

    out_col = "#2A7A5A" if m["outcomes_filled"] else "#C0392B"
    out_label = "Gevuld" if m["outcomes_filled"] else "Leeg — actie vereist"
    out_note = "win/loss records beschikbaar" if m["outcomes_filled"] else "NN IC + Cathalijne invullen (5 min)"
    out_tip = (
        "Win/loss-records beschikbaar. Ainstein kan hierop leunen bij het bouwen van voorstellen."
        if m["outcomes_filled"] else
        "Geen win/loss-records. Ainstein mist een belangrijk referentiepunt voor nieuwe voorstellen."
    )

    card_tip = "Ainsteins geheugen van Minkowski — methodologie, positionering, en wat werkt in voorstellen."

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
    vm = m["vm"]
    h = m["svc_health"]

    def _svc_dot(ok):
        if ok is True:
            return _dot("#2A7A5A", 9)
        if ok is False:
            return _dot("#C0392B", 9)
        return _dot("#8492A6", 9)

    def row(label, ok, status_txt, age_txt, tip):
        dot = _svc_dot(ok)
        badge_cls = "badge-ok" if ok is True else "badge-fail" if ok is False else "badge-unknown"
        badge_label = status_txt
        return f"""
      <div class="svc-row">
        <div class="svc-name">{dot}{_tip(label, tip)}</div>
        <div class="svc-right">
          <span class="badge {badge_cls}">{badge_label}</span>
          <span class="svc-age">{age_txt}</span>
        </div>
      </div>"""

    # Google Cloud VM
    vm_disk = vm.get("disk_pct")
    vm_online = vm_disk is not None
    vm_age = f"schijf {vm_disk}%" if vm_disk is not None else "lokaal"
    gcp_instance = m["gcp"].get("instance_type") or "onbekend"

    # Flask /health
    flask_ok = h.get("flask")
    flask_age = "/health: ok" if flask_ok else "/health: geen antwoord"

    # Anthropic — credential + last used
    anth_ok = h.get("anthropic")
    anth_age = age_label(svc["anthropic"], now) if svc["anthropic"] else "nooit"

    # Slack
    slack_ok = h.get("slack")
    slack_age = age_label(svc["slack"], now) if svc["slack"] else "nooit"

    # Google Drive
    drive_ok = h.get("drive")
    drive_age = age_label(svc["drive"], now) if svc["drive"] else "nooit"

    # Jamie
    jamie_ok = h.get("jamie")
    jamie_age = age_label(svc["jamie"], now) if svc["jamie"] else "nooit"

    # Tavily
    tavily_ok = h.get("tavily")
    tavily_age = f"{svc['tavily_month']}/1.000 calls" if svc["tavily"] else "nooit"

    # SSL
    ssl_days = vm.get("ssl_days")
    ssl_ok = ssl_days is not None and ssl_days > 10
    ssl_age = f"{ssl_days}d resterend" if ssl_days is not None else "n.v.t."

    # SocketMode heartbeat
    sm_ok = h.get("socketmode_ok")
    sm_age_h = h.get("socketmode_age_h")
    if sm_age_h is None:
        sm_age_txt = "geen heartbeat-data (nog niet opgestart)"
    elif sm_age_h < 1:
        sm_age_txt = f"{int(sm_age_h * 60)}m geleden"
    else:
        sm_age_txt = f"{sm_age_h:.1f}u geleden"

    rows = (
        row("Google Cloud VM", vm_online,
            "online" if vm_online else "n.v.t.",
            f"{vm_age} · {gcp_instance}",
            "De server waarop Ainstein draait. Als deze offline gaat, stopt alles.")
        + row("Flask app", flask_ok,
              "bereikbaar" if flask_ok else "geen antwoord",
              flask_age,
              "De applicatieserver (Flask) die Slack en Jamie verwerkt. Dit is de meest directe indicator dat Ainstein werkt.")
        + row("Anthropic API", anth_ok,
              "geconfigureerd" if anth_ok else "niet geconfigureerd",
              anth_age,
              "De AI-dienst achter Ainsteins intelligentie. Elke verzoek gaat via Anthropic.")
        + row("Slack", slack_ok,
              "geconfigureerd" if slack_ok else "niet geconfigureerd",
              slack_age,
              "De chatverbinding waarmee Ainstein berichten ontvangt en verstuurt.")
        + row("Google Drive", drive_ok,
              "geconfigureerd" if drive_ok else "niet geconfigureerd",
              drive_age,
              "De documentenopslag met voorstellen, expertprofielen en methodologie.")
        + row("Jamie webhook", jamie_ok,
              "geconfigureerd" if jamie_ok else "niet geconfigureerd",
              jamie_age,
              "De koppeling met Jamie. Na elke vergadering stuurt Jamie het transcript naar Ainstein.")
        + row("Tavily", tavily_ok,
              "geconfigureerd" if tavily_ok else "niet geconfigureerd",
              tavily_age,
              "Webzoekdienst voor actuele informatie. Gratis plan: 1.000 zoekopdrachten per maand.")
        + row("SSL / DuckDNS", ssl_ok,
              "geldig" if ssl_ok else ("verloopt binnenkort" if ssl_days is not None else "n.v.t."),
              ssl_age,
              "Het HTTPS-certificaat en domein. Verloopt dit, dan werkt de Jamie-koppeling niet meer.")
        + row("SocketMode verbinding", sm_ok,
              "actief" if sm_ok is True else ("stale" if sm_ok is False else "geen data"),
              sm_age_txt,
              "Heartbeat van de Slack SocketMode-verbinding. Wordt elke 30 min bijgewerkt. Stale = Ainstein reageert mogelijk niet op Slack-berichten.")
    )

    card_tip = "Of elke externe dienst geconfigureerd is en bereikbaar. Rood = actie vereist."

    return f"""
  <div class="card" style="border-top-color:#287093">
    <div class="card-label">{_tip('Diensten', card_tip)}</div>
    <div class="svc-list">{rows}
    </div>
    <div class="hint" style="margin-top:10px">
      Groen = geconfigureerd &amp; bereikbaar &nbsp;·&nbsp; Rood = niet geconfigureerd of fout
    </div>
  </div>"""


def render_card_futures_ready(m):
    kl_age = m.get("kl_age_days")
    n_bronnen = m.get("n_bronnen", 0)
    skills_30d = m.get("skills_30d", set())
    n_files = m.get("n_files_read", 0)
    meetings_month = m.get("meetings_month", 0)
    last_jamie = m.get("last_jamie_title") or "—"

    # ── Mindset: kennislaag actualiteit ────────────────────────────────────────
    if kl_age is None:
        ms_ok = False
        ms_label = "Kennislaag nog niet opgebouwd"
        ms_note = "Draai run_kennisextractie.py om te starten"
    elif kl_age > 30:
        ms_ok = None
        ms_label = f"{n_bronnen} bronnen · {kl_age}d oud"
        ms_note = "Vernieuwen aanbevolen — nieuwe content niet verwerkt"
    else:
        ms_ok = True
        ms_label = f"{n_bronnen} bronnen · {kl_age}d actueel"
        ms_note = "LinkedIn, Medium, Substack, website, Slack, proposals, meetings"

    # ── Skillset: breedte van inzet ────────────────────────────────────────────
    # Exclude kennisextractie-skills (pipeline, niet direct ingezet)
    user_skills = skills_30d - {"extract_knowledge_distilleer", "extract_knowledge_merge"}
    n_skills = len(user_skills)
    if n_skills >= 4:
        ss_ok = True
        ss_label = f"{n_skills} skills actief (30d)"
    elif n_skills >= 2:
        ss_ok = None
        ss_label = f"{n_skills} skills actief (30d)"
    else:
        ss_ok = False
        ss_label = f"{n_skills} skill{'s' if n_skills != 1 else ''} actief (30d)"
    skills_txt = ", ".join(sorted(user_skills)) if user_skills else "geen"
    ss_note = (skills_txt[:72] + "…") if len(skills_txt) > 72 else skills_txt

    # ── Toolset: kennisbreedte ─────────────────────────────────────────────────
    if n_files >= 20 or meetings_month >= 4:
        ts_ok = True
    elif n_files >= 6 or meetings_month >= 2:
        ts_ok = None
    else:
        ts_ok = False
    ts_label = f"{n_files} docs gelezen · {meetings_month} meetings deze maand"
    ts_note = f"Laatste meeting: {last_jamie[:60]}{'…' if len(last_jamie) > 60 else ''}"

    # ── Overall ────────────────────────────────────────────────────────────────
    dims = [ms_ok, ss_ok, ts_ok]
    n_green = dims.count(True)
    n_red = dims.count(False)
    if n_red == 0 and n_green == 3:
        ov_label, ov_col = "Gereed", "#2A7A5A"
    elif n_red >= 2:
        ov_label, ov_col = "Basis", "#C0392B"
    else:
        ov_label, ov_col = "Groeiend", "#E67E22"

    def dim_row(label, ok, status_label, note, tip):
        col = "#2A7A5A" if ok is True else "#C0392B" if ok is False else "#E67E22"
        return (
            f'<div style="display:flex;align-items:flex-start;gap:12px;'
            f'padding:10px 0;border-bottom:1px solid #EDE9E0">'
            f'{_dot(col, 8)}'
            f'<div style="flex:1;min-width:0">'
            f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;'
            f'color:#8492A6;font-weight:700;margin-bottom:2px">{_tip(label, tip)}</div>'
            f'<div style="font-size:13px;font-weight:600;color:#1B2E5E">{status_label}</div>'
            f'<div style="font-size:12px;color:#8492A6;margin-top:2px;'
            f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{note}</div>'
            f'</div></div>'
        )

    rows = (
        dim_row("Mindset", ms_ok, ms_label, ms_note,
                "Wat Ainstein weet: de kennislaag met Minkowski-positionering, methodologie en klantkennis.")
        + dim_row("Skillset", ss_ok, ss_label, ss_note,
                  "Wat Ainstein kan: de skills die actief zijn ingezet in de afgelopen 30 dagen.")
        + dim_row("Toolset", ts_ok, ts_label, ts_note,
                  "Waarmee Ainstein werkt: documenten gelezen, meetings verwerkt, bronnen aangeraakt.")
    )

    return f"""
  <div class="card" style="border-top-color:{ov_col}">
    <div class="card-label">{_tip('Futures Ready', 'In hoeverre Ainstein klaar is om Minkowski te ondersteunen — op drie assen.')}</div>
    <div style="display:flex;align-items:baseline;gap:8px;margin-bottom:12px">
      {_dot(ov_col, 10)}
      <span style="font-size:20px;font-weight:800;color:{ov_col};font-family:\'Sen\',Helvetica,sans-serif">{ov_label}</span>
      <span style="font-size:12px;color:#8492A6">— Ainstein gereedheid</span>
    </div>
    {rows}
  </div>"""


def render_card_fouten(m):
    errors = m["errors"]
    error_tip = "Een fout die is opgetreden maar het systeem draait nog. Controleer of het zich herhaalt."
    critical_tip = "Een ernstige fout. Het systeem werkt mogelijk niet meer correct — directe aandacht vereist."

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
    <div class="card-label">{_tip('Recente fouten', 'De laatste technische foutmeldingen. Een enkele fout is zelden urgent — een reeks fouten wel.')}</div>
    <div class="error-list">{content}
    </div>
    <div class="hint" style="margin-top:10px">
      Zie ook: <code>logs/ainstein.log</code> op de VM voor volledig logboek
    </div>
  </div>"""


# ── Client card (pilot) ──────────────────────────────────────────────────────

_CLIENT_FOLDERS = ("01_Proposals", "08_Outcomes", "04_Experts")
_SKIP_NAMES = {"", "TEMPLATE", "templates", "_Archive", "README"}


def _extract_client(entry):
    """Derive a client/context label from a trace entry."""
    for path in entry.get("files_read", []):
        parts = path.replace("\\", "/").split("/")
        for folder in _CLIENT_FOLDERS:
            if folder in parts:
                idx = parts.index(folder)
                if idx + 1 < len(parts):
                    cand = parts[idx + 1]
                    if (cand not in _SKIP_NAMES
                            and "." not in cand
                            and not cand.startswith("_")
                            and not (cand[0].isdigit() if cand else True)):
                        return cand
    if entry.get("skill") == "meeting_reviewer":
        return entry.get("meeting_title") or None
    return None


def _skill_nl(skill):
    return {
        "build_proposal": "voorstel",
        "analyse_opportunity": "analyse",
        "match_experts": "experts",
        "qualify_lead": "kwalificatie",
        "prepare_discovery": "discovery-prep",
        "client_discovery_debrief": "debrief",
        "map_objections": "bezwaren",
        "meeting_reviewer": "meeting",
        "dvv_check": "kwaliteitscheck",
        "create_content": "content",
        "sharpen_positioning": "positionering",
        "extract_knowledge": "kennisanalyse",
    }.get(skill or "", skill or "?")


def build_client_interactions(entries, now):
    """Return list of latest interaction per client, sorted by recency."""
    latest = {}
    for e in entries:
        client = _extract_client(e)
        if not client:
            continue
        ts = parse_ts(e.get("timestamp"))
        if ts is None:
            continue
        if client not in latest or ts > latest[client]["ts"]:
            latest[client] = {
                "client": client,
                "ts": ts,
                "skill": e.get("skill"),
                "preview": e.get("answer_preview", ""),
            }
    rows = sorted(latest.values(), key=lambda x: x["ts"], reverse=True)
    return rows[:8]


def render_card_klanten(m):
    rows = build_client_interactions(m["_entries"], m["now"])
    now = m["now"]

    if not rows:
        content = '<div class="no-errors muted">Nog geen klantinteracties herkend.<br>Wordt gevuld zodra Ainstein bestanden uit 01_Proposals leest of meetings verwerkt.</div>'
    else:
        content = ""
        for r in rows:
            age = age_label(r["ts"], now)
            skill_lbl = _skill_nl(r["skill"])
            preview = r["preview"][:140].replace("<", "&lt;").replace(">", "&gt;") if r["preview"] else ""
            if preview and len(r["preview"]) > 140:
                preview += "…"
            client_display = r["client"]
            if len(client_display) > 42:
                client_display = client_display[:40] + "…"
            content += f"""
      <div class="klant-row">
        <div class="klant-header">
          <span class="klant-name">{client_display}</span>
          <span class="klant-meta">
            <span class="badge badge-ok" style="background:#E8F4FC;color:#1A4E7C">{skill_lbl}</span>
            <span class="svc-age">{age}</span>
          </span>
        </div>
        {'<div class="klant-preview">' + preview + '</div>' if preview else ''}
      </div>"""

    return f"""
  <div class="card" style="border-top-color:#8492A6;grid-column:1/-1">
    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px">
      <div class="card-label" style="margin-bottom:0">{_tip('Klanten — pilot', 'Automatisch afgeleid uit bestanden die Ainstein heeft gelezen en meetings die zijn binnengekomen. Geen handmatige invoer.')}</div>
      <span style="font-size:10px;color:#B0BAD4;font-style:italic">experimenteel — afgeleid uit bronnen</span>
    </div>
    <div class="klant-list">{content}
    </div>
  </div>"""


# ── CSS ───────────────────────────────────────────────────────────────────────

CSS_TEMPLATE = """
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: Helvetica, Arial, "Lucida Grande", sans-serif;
  background: #F5F4F1;
  color: #001C40;
  min-height: 100vh;
}}
{font_face}
header {{
  background: #FFFFFF;
  border-bottom: 1px solid #E4E1D8;
  padding: 14px 40px;
}}
.header-inner {{
  max-width: 1060px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}}
.header-left {{ display: flex; align-items: center; gap: 16px; }}
.header-logo {{ height: 30px; width: auto; display: block; }}
.header-divider {{ width: 1px; height: 26px; background: #D8D5CC; flex-shrink: 0; }}
.header-product-name {{
  display: block;
  font-family: 'Sen', Helvetica, Arial, sans-serif;
  font-size: 15px; font-weight: 800; color: #001C40;
  letter-spacing: -0.01em; line-height: 1.2;
}}
.header-product-sub {{
  display: block; font-size: 10px; color: #8494A8;
  letter-spacing: 0.08em; text-transform: uppercase; margin-top: 3px;
}}
.generated {{ font-size: 11px; color: #9AA5BE; text-align: right; line-height: 1.6; }}
main {{
  max-width: 1060px;
  margin: 28px auto;
  padding: 0 24px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}}
.card {{
  background: #FFFFFF;
  border-radius: 8px;
  padding: 20px 22px;
  box-shadow: 0 1px 2px rgba(0,28,64,0.06), 0 3px 12px rgba(0,28,64,0.04);
  border-top: 3px solid transparent;
  overflow: visible;
}}
.card-label {{
  font-size: 10px; font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; color: #9AA5BE; margin-bottom: 12px;
}}
.big {{ font-size: 26px; font-weight: 700; letter-spacing: -0.02em; line-height: 1; color: #001C40; }}
.meta {{ font-size: 12px; color: #7A89A8; margin-top: 5px; }}
.divider {{ border-top: 1px solid #EEEAE2; margin: 12px 0; }}
.hint {{ font-size: 11px; color: #B0BAD4; line-height: 1.5; margin-top: 8px; }}
.alert {{
  margin-top: 10px; background: #FEF2E8;
  border-left: 3px solid #E67E22; border-radius: 4px;
  padding: 7px 11px; font-size: 12px; color: #7A4500;
}}
.row-items {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px 14px; }}
.row-label {{ font-size: 10px; color: #9AA5BE; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 3px; }}
.row-val {{ font-size: 12px; font-weight: 600; color: #001C40; }}
.kpi-row {{ display: flex; gap: 24px; margin-top: 10px; }}
.kpi-num {{ font-size: 28px; font-weight: 700; letter-spacing: -0.02em; color: #001C40; }}
.kpi-label {{ font-size: 10px; color: #9AA5BE; margin-top: 3px; text-transform: uppercase; letter-spacing: 0.05em; }}
.skills-list {{ margin-top: 12px; border-top: 1px solid #EEEAE2; padding-top: 10px; }}
.skill-row {{
  display: flex; justify-content: space-between; align-items: center;
  padding: 4px 0; font-size: 12px; border-bottom: 1px solid #F5F3EE;
}}
.skill-row:last-child {{ border-bottom: none; }}
.skill-name {{ color: #001C40; }}
.skill-count {{ font-weight: 600; color: #287093; }}
.skill-row.muted {{ color: #9AA5BE; font-style: italic; justify-content: center; }}
/* Services */
.svc-list {{ display: flex; flex-direction: column; }}
.svc-row {{
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 0; border-bottom: 1px solid #F5F3EE; font-size: 12px;
}}
.svc-row:last-child {{ border-bottom: none; }}
.svc-name {{ font-weight: 500; color: #001C40; display: flex; align-items: flex-start; }}
.svc-right {{ display: flex; align-items: center; gap: 8px; flex-shrink: 0; }}
.svc-age {{ color: #9AA5BE; font-size: 11px; }}
/* Badges */
.badge {{
  font-size: 10px; font-weight: 700; letter-spacing: 0.04em;
  padding: 2px 7px; border-radius: 10px; text-transform: uppercase;
  white-space: nowrap;
}}
.badge-ok    {{ background: #E6F4EE; color: #1A6645; }}
.badge-fail  {{ background: #FDEEEC; color: #8B2016; }}
.badge-unknown {{ background: #F0EDE6; color: #7A89A8; }}
/* Errors */
.error-list {{ display: flex; flex-direction: column; gap: 7px; margin-top: 4px; }}
.error-row {{
  background: #FFF8F7; border-left: 3px solid #E8B4B0;
  border-radius: 4px; padding: 7px 10px;
}}
.error-meta {{ display: flex; gap: 10px; align-items: center; margin-bottom: 3px; }}
.error-ts {{ font-size: 11px; color: #9AA5BE; }}
.error-level {{ font-size: 10px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }}
.error-msg {{ font-size: 11px; color: #3A2020; font-family: monospace; word-break: break-word; }}
.no-errors {{ font-size: 12px; color: #2A7A5A; padding: 10px 0; }}
.no-errors.muted {{ color: #9AA5BE; }}
/* Klanten */
.klant-list {{ display: flex; flex-direction: column; gap: 6px; }}
.klant-row {{
  background: #FAFAF8; border-radius: 5px; padding: 8px 10px;
  border-left: 3px solid #D8D5CC;
}}
.klant-header {{
  display: flex; justify-content: space-between; align-items: center;
  gap: 8px; flex-wrap: wrap;
}}
.klant-name {{ font-size: 13px; font-weight: 600; color: #001C40; }}
.klant-meta {{ display: flex; align-items: center; gap: 8px; flex-shrink: 0; }}
.klant-preview {{
  font-size: 11px; color: #7A89A8; margin-top: 4px;
  line-height: 1.5; font-style: italic;
}}
footer {{
  text-align: center; padding: 20px; font-size: 11px; color: #9AA5BE;
}}
footer a {{ color: #287093; text-decoration: none; opacity: 0.7; }}
footer a:hover {{ opacity: 1; }}
@media (max-width: 900px) {{
  main {{ grid-template-columns: repeat(2, 1fr); }}
}}
@media (max-width: 600px) {{
  main {{ grid-template-columns: 1fr; margin: 16px auto; }}
  header {{ padding: 12px 16px; }}
}}
/* Tooltips */
.tip {{
  position: relative; cursor: help;
  text-decoration: underline;
  text-decoration-style: dotted;
  text-decoration-color: rgba(0,28,64,0.20);
  text-underline-offset: 3px;
}}
.tip::after {{
  content: attr(data-tip);
  position: absolute; bottom: calc(100% + 10px); left: 50%;
  transform: translateX(-50%);
  background: #001C40; color: #FFFFFF;
  font-size: 12px; font-weight: 400; font-style: normal;
  letter-spacing: 0; text-transform: none; text-decoration: none;
  white-space: normal; width: 230px; padding: 9px 13px;
  border-radius: 6px; line-height: 1.55;
  opacity: 0; pointer-events: none;
  transition: opacity 0.14s ease; z-index: 300;
  box-shadow: 0 4px 18px rgba(0,28,64,0.18);
}}
.tip::before {{
  content: ''; position: absolute; bottom: calc(100% + 4px); left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent; border-top-color: #001C40;
  opacity: 0; pointer-events: none;
  transition: opacity 0.14s ease; z-index: 300;
}}
.tip:hover::after, .tip:hover::before {{ opacity: 1; }}
/* Alert bar */
.alert-bar {{
  padding: 11px 40px; font-size: 13px; font-weight: 600;
  text-align: center; color: #FFFFFF; line-height: 1.5;
  display: flex; align-items: center; justify-content: center; gap: 10px;
  flex-wrap: wrap;
}}
.alert-bar.alert-ok {{ background: #1A6645; }}
.alert-icon {{
  font-size: 15px; font-weight: 900;
  width: 22px; height: 22px; border-radius: 50%;
  background: rgba(255,255,255,0.25);
  display: inline-flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}}
/* Trend */
.trend {{ font-size: 18px; font-weight: 700; margin-left: 4px; vertical-align: middle; }}
.trend-ctx {{ font-size: 11px; color: #9AA5BE; margin-top: 2px; }}
/* Jamie */
.jamie-block {{ margin-bottom: 6px; }}
.jamie-title {{ font-size: 13px; font-weight: 600; color: #001C40; line-height: 1.4; }}
.jamie-meta {{ font-size: 11px; color: #7A89A8; margin-top: 3px; }}
"""


def render(m, logo_uri, font_face):
    alert_bar = render_alert_bar(m)
    c1 = render_card_status(m)
    c2 = render_card_gebruik(m)
    c3 = render_card_kosten(m)
    c4 = render_card_kennislaag(m)
    c4b = render_card_futures_ready(m)
    c5 = render_card_diensten(m)
    c6 = render_card_fouten(m)
    c7 = render_card_klanten(m)

    css = CSS_TEMPLATE.format(font_face=font_face)

    if logo_uri:
        logo_html = f'<img class="header-logo" src="{logo_uri}" alt="Minkowski">'
    else:
        logo_html = '<span style="font-family:\'Sen\',Helvetica,sans-serif;font-weight:800;font-size:18px;color:#A4B187">Minkowski</span>'

    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ainstein Dashboard</title>
<style>{css}</style>
</head>
<body>
<header>
  <div class="header-inner">
    <div class="header-left">
      {logo_html}
      <div class="header-divider"></div>
      <div>
        <span class="header-product-name">Ainstein</span>
        <span class="header-product-sub">Management Dashboard</span>
      </div>
    </div>
    <div class="generated">Gegenereerd op<br>{m['generated_at']}</div>
  </div>
</header>
{alert_bar}
<main>
{c1}
{c2}
{c3}
{c4}
{c4b}
{c5}
{c6}
{c7}
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

    logo_uri = load_asset_b64(LOGO_PATH, "image/png")
    print(f"  Logo: {'geladen' if logo_uri else 'niet gevonden'}")

    font_b64 = load_asset_b64(FONT_PATH, "font/truetype")
    if font_b64:
        font_face = f"@font-face {{ font-family: 'Sen'; font-weight: 800; src: url('{font_b64}') format('truetype'); }}"
        print("  Sen ExtraBold: ingeladen")
    else:
        font_face = ""

    entries = load_decisions()
    print(f"  {len(entries)} entries uit decisions.jsonl")
    errors = load_log_errors()
    vm = check_vm_health()
    print(f"  VM: service={vm.get('service_status')}, disk={vm.get('disk_pct')}%, "
          f"load={vm.get('load_1m')}, mem={vm.get('mem_pct')}%, ssl={vm.get('ssl_days')}d")
    svc_health = check_service_connectivity()
    print(f"  Health checks: {svc_health}")
    gcp = get_gcp_info()
    print(f"  GCP: instance={gcp.get('instance_type')}, cost=€{gcp.get('monthly_eur')}/mnd")
    svc = extract_service_activity(entries, now)
    m = compute_metrics(entries, vm, svc, svc_health, gcp, errors, now)
    html = render(m, logo_uri, font_face)
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"  Gegenereerd: {OUTPUT}")


if __name__ == "__main__":
    main()
