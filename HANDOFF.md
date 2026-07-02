# Ainstein Handoff — Sessie 2026-05-31

Dit document is de volledige overdracht van een cloud-sessie naar een lokale sessie.
Plak de inhoud van dit bestand als eerste bericht in een nieuwe lokale Claude Code sessie.

---

## Wie je bent en wat je weet

Je werkt aan het Ainstein-project voor Minkowski. Ainstein is een Claude-aangedreven commerciële intelligentielaag die draait als Slack-bot en CLI. De codebase staat op `/Users/thomasthiadens/Ainstein` (lokaal) of `/home/user/Ainstein` (cloud). De Google Drive source layer is bereikbaar via service account (`ainstein-bot@minkowski-ainstein.iam.gserviceaccount.com`), drive root ID `0AFvBEDYKrnHbUk9PVA`.

Sleutelbestanden:
- `brain.md` — system prompt van de agent
- `agent.py` — CLI orchestrator, `run_agent()` op regel 147
- `slack_app.py` — Slack bot, `_run_and_reply()` op regel 259, `__main__` op regel 950+
- `tools.py` — tool dispatch + Drive API, `_save_note_via_drive_api()` op regel 389
- `gdoc_tools.py` — Google Docs integratie
- `skills/*.md` — 14 skill-definities (plain markdown, geen code)
- `requirements.txt` — Flask staat er NIET in (relevant voor Plan B)

---

## Wat gedaan is in de vorige sessie

### Plan A: Prompt Coaching — KLAAR ✓

**Branch:** `claude/ainstein-slack-questions-AmZir` (gepusht, klaar voor merge)
**Commit:** `1be0b66 feat(brain): voeg Prompt Coaching sectie toe aan brain.md`

**Wat is gedaan:**
Nieuwe sectie `## Prompt Coaching` toegevoegd aan `brain.md` na regel 263 (na Operating Rule 11, vóór `## Tone`).

De sectie instrueert Ainstein om na elk niet-triviaal antwoord een coachingblok toe te voegen dat laat zien wat de ideale vraag had geweest. Dit is een directe extensie van Operating Rule 5 ("Do not reward vagueness").

**Kenmerken van de implementatie:**
- Skill-aware: per skill (analyse_opportunity, build_proposal, match_experts, qualify_lead) andere coaching-elementen
- Kwaliteitsgate: vage coaching ("more context would help") wordt weggelaten — liever geen coaching dan generieke coaching
- Scherpheidsdrempel: vraag is "al scherp" als ≥3 van 6 elementen aanwezig zijn (klantnaam, budget, programmatype, outputformaat, referentiemateriaal, beslissing)
- Scheiding van feedback-loop: triggert nooit `record_correction` — compleet apart systeem
- Format: `---` divider + **Scherpere vraag** header + één coachingszin + blockquote met ideale herformulering

**Wat nog moet:**
- Branch mergen naar main: `git checkout main && git merge claude/ainstein-slack-questions-AmZir`
- Deployen op de productie-VM: `git pull` + `systemctl restart ainstein`
- Testen in Slack: stel een vage vraag → verwacht coachingblok; stel een scherpe vraag (≥3 elementen) → verwacht bevestiging

---

## Wat nog gedaan moet worden

### Plan B: Jamie → Ainstein → Slack — NOG TE DOEN

**Prioriteit:** Hoog. Hoge dagelijkse waarde voor Charlotte en Jörgen.
**Branch:** Nog aan te maken (bijv. `claude/jamie-webhook-integration`)
**Vereist:** Productie-VM met Drive-credentials + Jamie account met webhook-configuratie

**Waarom:**
Charlotte en Jörgen nemen klantgesprekken op via Jamie (AI-meetingrecorder). Inzichten verdwijnen nu in losse transcripten. Doel: zodra een gesprek klaar is, haalt Ainstein het transcript op, analyseert het via de `client_discovery_debrief`-skill, slaat het op in de juiste Drive-projectmap, en stuurt proactief een gestructureerd Slack-bericht met actiepunten per persoon.

---

### Plan B — Volledige implementatiespecificatie

#### Architectuur

```
jamie.ai ──POST──▶ Flask webhook server (:8080, daemon thread)
                         │
                   webhook_server.py
                   jamie.py (parser + HMAC-SHA256)
                   project_matcher.py (Drive-zoekactie)
                         │
                   run_agent(messages, anthropic_client,
                             skill="client_discovery_debrief")
                         │
                   _save_note_via_drive_api(folder_hint=matched_folder)
                         │
                   slack_client.chat_postMessage()
                    ┌────┴────────────┐
                    ▼                 ▼
            #transcript-kanaal    DM naar expert
```

Slack WebSocket (SocketModeHandler) blijft ongewijzigd in de hoofdthread.

---

#### Nieuwe bestanden

**`jamie.py`**

```python
from dataclasses import dataclass

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

def parse_jamie_payload(body: dict) -> JamieMeeting: ...
# Veld-namen zijn ONBEKEND — eerste echte webhook onthult schema.
# Bij KeyError/ValueError: sla raw payload op naar Drive + post naar Slack-kanaal.
# Retourneer NOOIT een fout naar Jamie (200 OK altijd).

def verify_jamie_signature(raw_body: bytes, header: str, secret: str) -> bool: ...
# HMAC-SHA256 via header X-Jamie-Signature: sha256=<hex>

def extract_minkowski_participant(participants, known_emails) -> tuple[str|None, str|None]: ...
# Matcht op EXPERT_CHARLOTTE_EMAIL / EXPERT_JORGEN_EMAIL env vars

def infer_client_name(meeting: JamieMeeting) -> str: ...
```

**`project_matcher.py`**

```python
def match_project_folder(client_name, meeting_title, participants) -> tuple[str|None, str]:
    # 1. tools.search_files(client_name, folders=["01_Clients"])
    # 2. Fallback: eerste 3-4 woorden van meeting-titel
    # 3. Geen match: retourneer (None, "00_Werkdocumenten")
    # folder_hint gaat direct naar _save_note_via_drive_api(folder_hint=...)
```

**`transcript_processor.py`**

```python
_slack_client = None
_anthropic_client = None

def set_clients(slack_client, anthropic_client) -> None:
    # Wordt aangeroepen vanuit slack_app.py __main__ vóór server start
    # GEEN imports van slack_app hier — circulaire import vermijden

def process_transcript(meeting: JamieMeeting) -> None:
    # Volledige pipeline. Daemon-thread. Vangt ALLE fouten op.
    # Bij exception: post transcript + foutmelding naar AINSTEIN_TRANSCRIPT_CHANNEL

def _build_agent_prompt(meeting, folder_hint) -> str:
    # Inclusief language_note:
    # "Note: this meeting was conducted in Dutch/English. Write the debrief in the same language."

def _post_slack_notification(meeting, debrief_text, doc_url,
                              expert_name, expert_slack_id, matched_folder) -> None:
    # Kanaalpost naar AINSTEIN_TRANSCRIPT_CHANNEL + DM naar expert

def _extract_action_items(debrief_text: str, person: str) -> list[str]:
    # Extraheer uit sectie 9 (Open Questions) en sectie 11 (Recommended Next Step)
```

**`webhook_server.py`**

```python
def create_webhook_app(slack_client, anthropic_client) -> Flask:
    # POST /webhooks/jamie:
    #   1. Lees raw body (nodig voor HMAC vóór JSON-parse)
    #   2. verify_jamie_signature() → 403 bij fail
    #   3. _is_duplicate(meeting_id) → 200 zonder verwerking bij duplicaat
    #   4. parse_jamie_payload() → bij parse-fout: raw payload naar Drive + Slack, return 200
    #   5. Direct 200 OK retourneren
    #   6. threading.Thread(target=process_transcript, daemon=True).start()
    # GET /health → {"status": "ok", "jamie_configured": true}

def start_webhook_server(port: int, slack_client, anthropic_client) -> None: ...

# Deduplicatie (thread-safe):
_processed_meetings: set[str] = set()
_meetings_lock = threading.Lock()

def _is_duplicate(meeting_id: str) -> bool:
    with _meetings_lock:
        if meeting_id in _processed_meetings:
            return True
        _processed_meetings.add(meeting_id)
        return False
```

---

#### Gewijzigde bestanden

**`slack_app.py` — twee toevoegingen:**

1. `/transcript` slash command (vóór `if __name__`, zelfde patroon als bijv. regel 546):
```python
@app.command("/transcript")
def cmd_transcript(body, ack, say):
    _slash_handler("client_discovery_debrief", body, ack, say)
```

2. Webhook-thread in `__main__` (invoegen vóór `handler.start()` op huidige regel 977):
```python
if os.environ.get("JAMIE_WEBHOOK_SECRET"):
    from webhook_server import start_webhook_server
    from transcript_processor import set_clients
    _wh_slack_client = app.client          # Bolt WebClient
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

**`requirements.txt`:**
Toevoegen: `flask>=3.0.0`

**`.env.example`:**
```
JAMIE_WEBHOOK_SECRET=          # python3 -c "import secrets; print(secrets.token_hex(32))"
JAMIE_WEBHOOK_PORT=8080
AINSTEIN_TRANSCRIPT_CHANNEL=   # Slack channel ID voor transcript-notificaties
EXPERT_CHARLOTTE_EMAIL=charlotte@minkowski.nl
EXPERT_JORGEN_EMAIL=jorgen@minkowski.nl
EXPERT_CHARLOTTE_SLACK_ID=     # Slack profiel → More → Copy member ID
EXPERT_JORGEN_SLACK_ID=
```

---

#### Implementatievolgorde

**Fase 1 — Fundament + veiligheid (geen Slack-notificaties nog):**
1. `jamie.py` — parser met parse-fout fallback (raw payload → Drive + Slack)
2. `webhook_server.py` — Flask, deduplicatie, security (geen server zonder secret)
3. `flask>=3.0.0` aan `requirements.txt`
4. `slack_app.py __main__` — webhook-thread (8 regels)
5. Test: `curl localhost:8080/health` → `{"status": "ok", "jamie_configured": true}`
6. Test: `curl -X POST localhost:8080/webhooks/jamie` zonder signature → 403

**Fase 2 — Verwerking:**
7. `project_matcher.py` — roept bestaande `search_files()` aan
8. `transcript_processor.py` — `set_clients()` + `process_transcript()` met failure-pad
9. Test met synthetische payload + geldig HMAC → log toont parsing + run_agent aanroep

**Fase 3 — Notificaties:**
10. `_post_slack_notification()` — kanaalpost + DM
11. `/transcript` slash command + registreren in Slack App config (api.slack.com → Slash Commands)

**Fase 4 — Deployment:**
12. Env vars instellen op VM (zie `.env.example` uitbreiding)
13. nginx toevoegen: `location /webhooks/ { proxy_pass http://127.0.0.1:8080; proxy_read_timeout 30s; }`
14. Jamie configureren: webhook URL `https://ainstein.minkowski.nl/webhooks/jamie` + shared secret
15. Eerste echte meeting → raw payload in Drive → `jamie.py` aanpassen op werkelijk schema

---

#### Kritieke ontwerpbeslissingen (al genomen)

| Beslissing | Keuze | Reden |
|---|---|---|
| Circulaire import oplossen | `set_clients()` in transcript_processor | Geen imports van slack_app buiten __main__ |
| Secret niet geconfigureerd | Server start simpelweg niet | Geen silent security-lek mogelijk |
| Jamie payload onbekend | Parse-fout → raw naar Drive + Slack | Eerste meeting onthult schema, info nooit kwijt |
| Jamie retry → dubbele verwerking | `_is_duplicate()` op meeting_id | Thread-safe set, in-memory |
| ANTHROPIC_CLIENT in transcript_processor | Via `set_clients()` parameter | Niet importeren uit slack_app |
| run_agent() aanroep | `run_agent(messages, anthropic_client, skill="client_discovery_debrief")` | Bevestigde signature (agent.py:147) |
| Taal debrief | `meeting.language` → language_note in prompt | Minkowski werkt NL én EN |

---

#### Hergebruikte bestaande functies (geen duplicatie)

- `tools.search_files(query, folders)` — projectmatch in Drive (tools.py:1195)
- `tools._save_note_via_drive_api(title, content, folder_hint)` — opslaan debrief (tools.py:389)
- `tools._find_subfolder_by_hint()` — BFS 5 niveaus diep, al gecapped (tools.py:353)
- `agent.run_agent(messages, client, skill=...)` — transcript-analyse (agent.py:147)
- `app.client.chat_postMessage(channel, text, mrkdwn=True)` — Slack-notificaties (slack_app.py:650)
- `threading.Thread(daemon=True)` — achtergrondverwerking (slack_app.py:511, 537, 695)
- `_slash_handler(skill, body, ack, say)` — /transcript command (slack_app.py:546 patroon)

---

## Hoe verder in de nieuwe sessie

1. `git pull` op de lokale repo om deze handoff op te halen
2. Open Claude Code lokaal in `/Users/thomasthiadens/Ainstein`
3. Plak dit document als context of verwijs naar `HANDOFF.md`
4. Controleer eerst: `git log --oneline -5` — branch `claude/ainstein-slack-questions-AmZir` moet zichtbaar zijn
5. Beslis: Plan A mergen eerst, of direct Plan B implementeren?

**Aanbeveling:** merge Plan A eerst (`git checkout main && git merge claude/ainstein-slack-questions-AmZir && git push`), deploy op VM, test in Slack. Dan Plan B in een verse branch.
