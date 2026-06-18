# Ainstein Ontwikkelroadmap

Laatste update: 2026-06-16
Status: Plan A afgerond ✅, Plan B afgerond ✅.

---

## Plan A: Proactive Prompt Coaching ✓ GEDAAN

**Branch:** `claude/ainstein-slack-questions-AmZir`
**Commit:** `1be0b66`
**Status:** Gepusht, wacht op merge naar main + deploy op VM.

### Waarom
Vragen in Slack zijn vaak te vaag: geen klantnaam, geen budget, geen gewenst outputformaat. Operating Rule 5 ("Do not reward vagueness") was passief. Dit maakt het actief zichtbaar in elk antwoord.

### Wat gedaan
Nieuwe sectie `## Prompt Coaching` toegevoegd aan `brain.md` na regel 263 (na Operating Rule 11, vóór `## Tone`).

Ainstein voegt na elk niet-triviaal antwoord een coachingblok toe:
```
---
**Scherpere vraag**
[één coachende zin: wat ontbrak]
> "[ideale herformulering van de vraag]"
```

### Ontwerpkeuzes
- **Skill-aware**: per skill (analyse_opportunity, build_proposal, match_experts, qualify_lead) andere coaching-elementen
- **Kwaliteitsgate**: vage coaching wordt weggelaten — liever niets dan generiek
- **Scherpheidsdrempel**: vraag is "al scherp" bij ≥3 van 6 elementen (klantnaam, budget, programmatype, outputformaat, referentiemateriaal, beslissing)
- **Scheiding van feedback-loop**: triggert nooit `record_correction` — apart systeem

### Nog te doen voor live
1. `git checkout main && git merge claude/ainstein-slack-questions-AmZir && git push`
2. Op VM: `git pull && systemctl restart ainstein`
3. Test in Slack: vage vraag → coachingblok; scherpe vraag (≥3 elementen) → bevestiging

---

## Plan B: Jamie → Ainstein → Slack ○ NOG TE DOEN

**Branch:** nog aan te maken
**Status:** Volledig uitgewerkt, gereed voor implementatie. Vereist productie-VM met Drive-credentials.

### Waarom
Charlotte en Jörgen nemen klantgesprekken op via Jamie (AI-meetingrecorder). Inzichten verdwijnen in losse transcripten. Doel: zodra een gesprek klaar is, haalt Ainstein het transcript automatisch op, analyseert het via `client_discovery_debrief`, slaat het op in de juiste Drive-projectmap, en stuurt proactief een Slack-bericht met actiepunten per persoon.

### Architectuur

```
jamie.ai ──POST──▶ Flask webhook server (:8080, daemon thread)
                         │
                   webhook_server.py
                   jamie.py (parser + HMAC-SHA256)
                   project_matcher.py
                         │
                   run_agent(messages, anthropic_client,
                             skill="client_discovery_debrief")   ← agent.py:147
                         │
                   _save_note_via_drive_api(folder_hint=...)     ← tools.py:389
                         │
                   slack_client.chat_postMessage()
                    ┌────┴────────────┐
                    ▼                 ▼
            #transcript-kanaal    DM naar expert
```

Slack WebSocket (SocketModeHandler) blijft ongewijzigd in de hoofdthread.

---

### Nieuwe bestanden

#### `jamie.py`
Parser + verificatie voor Jamie-webhooks.

```python
@dataclass
class JamieMeeting:
    meeting_id: str
    title: str
    started_at: str          # ISO 8601
    participants: list[dict] # [{"name": str, "email": str}]
    transcript: str
    summary: str
    recording_url: str | None
    language: str

def parse_jamie_payload(body: dict) -> JamieMeeting
def verify_jamie_signature(raw_body: bytes, header: str, secret: str) -> bool
def extract_minkowski_participant(participants, known_emails) -> tuple[str|None, str|None]
def infer_client_name(meeting: JamieMeeting) -> str
```

**Kritiek:** Jamie's payload-veldnamen zijn onbekend. Bij `KeyError`/`ValueError`:
1. Sla raw payload op via `_save_note_via_drive_api()` naar `00_Werkdocumenten`
2. Post naar `AINSTEIN_TRANSCRIPT_CHANNEL`: "Nieuwe Jamie-webhook ontvangen maar kon niet worden geparsed. Raw payload opgeslagen."
3. Return `200 OK` (niet 400 — anders stopt Jamie met retries)

#### `project_matcher.py`

```python
def match_project_folder(client_name, meeting_title, participants) -> tuple[str|None, str]:
    # 1. tools.search_files(client_name, folders=["01_Proposals"])
    # 2. Fallback: eerste 3-4 woorden van meeting-titel
    # 3. Geen match: return (None, "00_Werkdocumenten")
```

#### `transcript_processor.py`

```python
def set_clients(slack_client, anthropic_client) -> None
    # Wordt aangeroepen vanuit slack_app.py __main__
    # GEEN imports van slack_app — circulaire import vermijden

def process_transcript(meeting: JamieMeeting) -> None
    # Volledige pipeline, daemon-thread, vangt ALLE fouten op
    # Bij exception: post transcript + foutmelding naar AINSTEIN_TRANSCRIPT_CHANNEL

def _build_agent_prompt(meeting, folder_hint) -> str
    # Inclusief: "Note: this meeting was conducted in Dutch/English."

def _post_slack_notification(meeting, debrief_text, doc_url,
                              expert_name, expert_slack_id, matched_folder) -> None

def _extract_action_items(debrief_text: str, person: str) -> list[str]
    # Sectie 9 (Open Questions) + sectie 11 (Recommended Next Step)
```

#### `webhook_server.py`

```python
def create_webhook_app(slack_client, anthropic_client) -> Flask
    # POST /webhooks/jamie:
    #   1. raw body lezen (voor HMAC vóór JSON-parse)
    #   2. verify_jamie_signature() → 403 bij fail
    #   3. _is_duplicate(meeting_id) → 200 zonder verwerking
    #   4. parse_jamie_payload() → bij fout: raw naar Drive + Slack, return 200
    #   5. Direct 200 OK retourneren
    #   6. threading.Thread(target=process_transcript, daemon=True).start()
    # GET /health → {"status": "ok", "jamie_configured": true}

def start_webhook_server(port: int, slack_client, anthropic_client) -> None

# Deduplicatie (thread-safe) — Jamie herprobeert bij timeout:
_processed_meetings: set[str] = set()
_meetings_lock = threading.Lock()
```

---

### Gewijzigde bestanden

#### `slack_app.py` — twee toevoegingen

**1. `/transcript` slash command** (vóór `if __name__`, zelfde patroon als regel 546):
```python
@app.command("/transcript")
def cmd_transcript(body, ack, say):
    _slash_handler("client_discovery_debrief", body, ack, say)
```

**2. Webhook-thread in `__main__`** (invoegen vóór `handler.start()` op regel 977):
```python
if os.environ.get("JAMIE_WEBHOOK_SECRET"):
    from webhook_server import start_webhook_server
    from transcript_processor import set_clients
    _wh_slack_client = app.client
    _wh_anthropic_client = ANTHROPIC_CLIENT
    set_clients(_wh_slack_client, _wh_anthropic_client)
    _wh_port = int(os.environ.get("JAMIE_WEBHOOK_PORT", "8080"))
    threading.Thread(
        target=start_webhook_server,
        args=(_wh_port, _wh_slack_client, _wh_anthropic_client),
        daemon=True,
    ).start()
    logger.info("Jamie webhook server gestart op poort %s", _wh_port)
```

#### `requirements.txt`
Toevoegen: `flask>=3.0.0`

#### `.env.example`
```
JAMIE_WEBHOOK_SECRET=          # python3 -c "import secrets; print(secrets.token_hex(32))"
JAMIE_WEBHOOK_PORT=8080
AINSTEIN_TRANSCRIPT_CHANNEL=   # Slack channel ID
EXPERT_CHARLOTTE_EMAIL=charlotte@minkowski.nl
EXPERT_JORGEN_EMAIL=jorgen@minkowski.nl
EXPERT_CHARLOTTE_SLACK_ID=     # Slack profiel → More → Copy member ID
EXPERT_JORGEN_SLACK_ID=
```

---

### Implementatievolgorde

**Fase 1 — Fundament:**
- [ ] `jamie.py` met parse-fout fallback
- [ ] `webhook_server.py` met deduplicatie en security-first
- [ ] `flask>=3.0.0` aan `requirements.txt`
- [ ] `slack_app.py __main__` webhook-thread (8 regels)
- [ ] Test: `curl localhost:8080/health`
- [ ] Test: POST zonder signature → 403

**Fase 2 — Verwerking:**
- [ ] `project_matcher.py`
- [ ] `transcript_processor.py` met failure-pad
- [ ] Test: synthetische payload + geldig HMAC → run_agent aanroep in logs

**Fase 3 — Notificaties:**
- [ ] `_post_slack_notification()` — kanaalpost + DM
- [ ] `/transcript` slash command
- [ ] Registreren in Slack App config (api.slack.com → Slash Commands)

**Fase 4 — Deployment:**
- [ ] Env vars op VM
- [ ] nginx: `location /webhooks/ { proxy_pass http://127.0.0.1:8080; proxy_read_timeout 30s; }`
- [ ] Jamie: `https://ainstein.minkowski.nl/webhooks/jamie` + secret
- [ ] Eerste echte meeting → raw payload in Drive → `jamie.py` aanpassen op schema

---

### Kritieke beslissingen (genomen)

| Beslissing | Keuze |
|---|---|
| Circulaire import | `set_clients()` — geen imports van `slack_app` buiten `__main__` |
| Secret niet geconfigureerd | Server start niet — geen silent security-lek |
| Jamie payload onbekend | Parse-fout → raw naar Drive + Slack, info nooit kwijt |
| Dubbele webhooks (retry) | `_is_duplicate()` op `meeting_id`, thread-safe |
| `ANTHROPIC_CLIENT` in processor | Via `set_clients()`, niet importeren uit `slack_app` |
| Taal debrief | `meeting.language` → `language_note` in agent-prompt |

### Hergebruikte bestaande functies

| Functie | Locatie | Gebruik |
|---|---|---|
| `search_files(query, folders)` | `tools.py:1195` | Projectmatch in Drive |
| `_save_note_via_drive_api(title, content, folder_hint)` | `tools.py:389` | Debrief opslaan |
| `_find_subfolder_by_hint()` | `tools.py:353` | BFS 5 niveaus, gecapped |
| `run_agent(messages, client, skill=...)` | `agent.py:147` | Transcript-analyse |
| `app.client.chat_postMessage()` | `slack_app.py:650` | Slack-notificaties |
| `threading.Thread(daemon=True)` | `slack_app.py:511,537,695` | Achtergrondverwerking |
| `_slash_handler(skill, body, ack, say)` | `slack_app.py:546 patroon` | `/transcript` command |

---

## Hoe dit bestand gebruiken

Dit bestand staat in de repo onder `plans/ainstein-roadmap.md`.
Gebruik het als context aan het begin van elke nieuwe Claude Code sessie:

> "Lees `plans/ainstein-roadmap.md` en ga verder waar we gebleven zijn."
