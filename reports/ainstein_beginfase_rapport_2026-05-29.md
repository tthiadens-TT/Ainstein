# Ainstein — Reconstructie beginfase
**Rapport gegenereerd:** 29 mei 2026  
**Periode gedekt:** 18 maart 2026 – 28 mei 2026  
**Doel:** Historische reconstructie voor maandrapport op basis van git-geschiedenis, Claude Code sessies, bestandsdatums en memory-bestanden.

---

## 1. Samenvatting

Ainstein is in 40 actieve bouwdagen gegroeid van een lokaal concept naar een volledig zakelijk platform: een cloud-VM met CI/CD-pipeline, organisatie-owned Google Workspace Shared Drive, service account, 14 commerciële skills, Slack Block Kit output, rate limiting, win/loss-geheugen en een wekelijkse backup. Wat begon als één Python-scriptje op een persoonlijke laptop draait vandaag volledig onafhankelijk van de hardware of het Gmail-account van Thomas.

| Kengetal | Waarde |
|---|---|
| Vroegste materiaal (Minkowski BizzModel pptx) | 18 maart 2026 |
| Eerste Claude Code sessie | 17 april 2026 |
| Eerste git commit | 18 april 2026 |
| Laatste commit in periode | 28 mei 2026 |
| Looptijd (eerste commit → nu) | 40 dagen |
| Totaal commits | 120 |
| Unieke commitdagen | 14 |
| Pull requests gemerged | 21 |
| Claude Code sessies (main + worktrees) | 63+ |
| Skills bij eerste commit | 3 |
| Skills nu | 14 |
| Maanden actief | 2 (april + mei 2026) |

---

## 2. Tijdlijn

### Fase 0 — Verkenning & materiaalverzameling (18 maart – 16 april 2026)

Vóór er ook maar één regel code was geschreven, werd de inhoudelijke basis gelegd.

**18 maart 2026**
- Eerste Minkowski-documenten aangemaakt: `Minkowski Future BizzModel NotebookLM.pptx`, `Copy of Minkowski as a Label - reviewed.pptx`
- `Minkowski_platform_transformatie_rapport.docx` — eerste poging tot een strategisch kader (19 maart)

**14 april 2026**
- Expert profielen gebundeld: `minkowski_team_profiles_bundle.zip` (20+ .docx bestanden), `00_Minkowski_Team_Profiles_Overview.docx`
- Precieze datum waarop de expertlaag als input voor een agent werd voorbereid

**16 april 2026**
- Source layer ingericht als gestructureerde mappenstructuur (folders `01_Proposals` t/m `06_Marketing`)
- `README_INDEX.md` geschreven — vroegste versie van de knowledge-architectuur
- Projectmap: `Downloads/minkowski_latest_md_files/`

**17 april 2026**
- Eerste Claude Code sessie gestart (project: `Minkowski-Agent`, vanuit Google Drive map `Thomas/AInstein`)
- Memory aangemaakt: "Minkowski Agent project" — architectuurbeslissingen vastgelegd (CLI, 3 skills, Anthropic SDK)

---

### Fase 1 — Kick-off en initiële bouw (18–29 april 2026)

**18 april 2026 — dag 1 in git**

Twee commits op dag één:
1. `Initial snapshot: Ainstein Slack bot + Minkowski source layer` — de eerste volledige codebase in git: `agent.py`, `tools.py`, `prompts.py`, `slack_app.py`
2. `Apply 10 review follow-ups from reviews/2026-04-18.md` — dezelfde dag al een code review uitgevoerd en 10 verbeterpunten doorgevoerd

Wat er in de initiële snapshot zat:
- `agent.py` — CLI met Anthropic SDK, interactieve chatloop, max 15 iteraties
- `tools.py` — bestandssysteemtools: `list_folder`, `read_file`, `search_files`
- `prompts.py` — systeemprompt met Minkowski-identiteit + 3 kernvaardigheden
- `slack_app.py` — Slack Bolt + Socket Mode (geen open poort nodig)
- Source layer als lokale mappenstructuur (nog niet op Drive)

Drie kernvaardigheden (v1):
1. `analyse_opportunity` — brief analyseren, fit beoordelen, verdict + next steps
2. `build_proposal` — eerdere voorstellen ophalen, bouwen of verbeteren
3. `match_experts` — expert profielen zoeken, teamsamenstellingen aanbevelen

Model: `claude-sonnet-4-6` met prompt caching op het systeemprompt.

**19 april 2026**
- `Add feedback learning loop: thumbs-down → 'what could be better?' → 07_Feedback/gaps.md`
- Ainstein leert van negatieve feedback: 👎-reactie triggert een vervolgvraag, het antwoord belandt automatisch in `07_Feedback/gaps.md`

**28 april 2026 — drie strategische commits**

1. `Add Google Drive API auth: setup script + deps for .gdoc/.gsheet/.gslides` — eerste stap richting Drive API (OAuth-gebaseerd)
2. `Migrate sales+marketing skills from multi-agent fork to single-agent` — expliciete architectuurkeuze: één agent met brede skills, geen multi-agent orchestrator. De multi-agent fork (ontwikkeld 21–28 april, nooit in git gezet) wordt geparkeerd
3. `Move source layer out of repo: SOURCE_ROOT env var, Drive single source` — data en code ontkoppeld; `AINSTEIN_SOURCE_ROOT` env var geïntroduceerd

**29 april 2026 — 10 commits, eerste 2 PR's**

Intensieve dag: source-discipline aangescherpt, alle 11 skills uitgebreid, CLI-bugs opgelost:
- `Enforce source discipline: primary = source layer, web = validate, always label`
- `Expand SKILL_INTROS to all 11 skills` — van 3 naar 11 vaardigheden in één sprint
- `Fix _detect_skill: prevent false positive routing to sharpen_positioning`
- `Fix agent.py CLI --skill: derive choices from SKILL_PROMPTS`
- `Fix agent.py CLI: load .env automatically`
- `Migrate duckduckgo-search → ddgs` — afhankelijkheidsbeheer
- `Rebuild venv + regenerate requirements.lock after project rename`
- **PR #1 en PR #2 gemerged** — eerste twee pull requests via tthiadens-TT/dev → main

---

### Fase 2 — Verdieping en stabilisatie (5–12 mei 2026)

**5 mei 2026 — zelflerend systeem (4 commits, PR #3 en #4)**

- `Build self-learning feedback loop: capture, classify, consult, act` — de feedbacklus wordt uitgebreid tot een volledig leer-systeem: opvangen, classificeren, raadplegen, actie
- `Capture feedback replies in channels, not only DMs` — Ainstein luistert nu ook naar feedback in kanalen, niet alleen in DMs

**8 mei 2026 — refactor naar markdown-bestanden (4 commits, PR #5)**

- `Refactor: verplaats brain + skills naar losse markdown-bestanden` — systeemprompt opgesplitst in `brain.md` + afzonderlijke skill-bestanden in `skills/`; beter onderhoudbaar en makkelijker te reviewen
- `Update requirements.lock na toevoeging Google Drive API en PyMuPDF deps`
- `Voeg client_secret*.json toe aan .gitignore` — OAuth-sleutel buiten git

**11 mei 2026 — Drive API + logging (7 commits, PR #6)**

- `Add Google Drive API backend for server deployment` — Drive API volledig werkend voor de serveromgeving (niet meer alleen lokaal via mount)
- `Voeg persistent logging toe: errors, decision traces, Drive snapshot, export` — foutopsporingsinfrastructuur voor productie
- `Voeg read_doc_comments toe als agent tool + CLI wrapper` — Ainstein kan Google Doc-comments lezen
- `Borg projectinstellingen in git: settings.json + gitignore fix`
- `Fix drie open dev-punten (CF 17, CF 18, CF 22)` — drie bekende bugs gesloten

**12 mei 2026 — voorstel-refinementloop + beveiliging (6 commits, PR #7)**

- `Voeg interactieve voorstel-refinement loop toe + PPTX export` — Ainstein kan een voorstel stap-voor-stap verfijnen via Slack en het exporteren als PowerPoint
- `Voorkom path traversal in _fs_read_file` — beveiligingspatch: directory traversal buiten bronnenlaag wordt geblokkeerd
- `Fix OAuth scope: drive.readonly → drive voor comment write-toegang`

---

### Fase 3 — VM-deployment en zakelijke inrichting (18–21 mei 2026)

**18 mei 2026 — van laptop naar cloud (12 commits, PR #8)**

Dit is de grootste enkele dag qua impact: Ainstein verlaat de laptop.

- `Add CI/CD: auto-deploy to VM on push to dev/main` — GitHub Actions pipeline: push naar dev/main → SSH naar VM → git pull → systemctl restart ainstein
- `Add DEPLOYMENT.md: VM-beheer, schrijfpaden en beveiligingschecklist`
- `Pre-deployment: alle lokale wijzigingen voor VM-migratie`
- `Fix Drive API init: support GOOGLE_SERVICE_ACCOUNT_FILE + broaden scope to drive` — service account als primaire auth (geen OAuth meer nodig op VM)
- `Verhoog snelheid en verlaag tokengebruik via twee-laags caching`
- `Fix: gebruik correcte naam Ainstein (niet AInstein) in system prompt` — merknaamcorrectie

Infrastructuur na 18 mei:
```
GitHub (main branch)
    │  push → GitHub Actions (.github/workflows/deploy.yml)
    │  SSH → VM (35.253.206.86)
    ▼
/home/thomas/Ainstein/  [systemd service: ainstein]
    └── python slack_app.py (Socket Mode)
```

**20 mei 2026 — Drive-schrijfproblemen opgelost (2 commits)**
- `Fix save_note: gebruik werkende Drive API service, bypass gdoc_tools OAuth`
- `Fix: save_note tool, skill-detectie archief-taken, Drive auth VM`

**21 mei 2026 — Shared Drive migratie (27 commits, PR #9–15)**

De zwaarste dag in de geschiedenis van het project: 27 commits, 7 PR's. De migratie van Thomas' persoonlijke Drive naar de organisatie-owned Shared Drive.

Kernwijzigingen:
- `Update Drive root + CLAUDE.md naar nieuwe Shared Drive architectuur` — driveId `0AFvBEDYKrnHbUk9PVA` (Minkowski AInstein Shared Drive, eigendom Jörgen/Minkowski)
- `Refactor save_note: losse Google Docs in juiste submap` — context-gedreven opslag: folder_hint matcht submap tot 5 niveaus diep
- `Fix list_folder Drive mode: recursief via 'in parents' (BFS)` — Drive API listing volledig herschreven
- `Fix save_note: voeg supportsAllDrives toe aan alle Drive API calls` — Shared Drives vereisen deze flag overal
- `Fix Drive shortcuts resolven bij read_file` — .gdoc-stubs worden automatisch resolved
- `Verbeter 7 skills + fix detect-skill false positive`
- `Gebruik Amsterdam-tijd in system prompt (was UTC)`
- `Injecteer huidige datum in system prompt`
- `Voeg list_recent_files tool toe via Drive API`

Nieuwe Shared Drive structuur na 21 mei:
| Map | Inhoud |
|---|---|
| `00_Roadmap` | Projectplanning |
| `00_Werkdocumenten` | Werkaantekeningen (default write-doel) |
| `01_Proposals` | Voorstellen — hergebruik, taal, modulecombinaties |
| `02_Tools` | Frameworks, workshopformats, facilitatie |
| `03_Pricing` | Tarieven, kortingslogica, aannames |
| `04_Experts` | Expertprofielen (.docx), JSON-index, beslissingslaag |
| `05_Venues` | Locatieprofielen, vergelijkingsmatrix |
| `06_Marketing` | Positionering, tone-of-voice, ICP, GTM |
| `07_Feedback` | `gaps.md` — autom. aangevuld via 👎-lus |

---

### Fase 4 — Volwassenheid en productie-hardening (26–28 mei 2026)

**26 mei 2026 — bugfixes en DVV-skill (14 commits, PR #16–18)**

- `Add dvv_check skill — standalone DVV quality check via Slack` — veertiende vaardigheid: Ainstein kan zelfstandig een DVV-kwaliteitscheck uitvoeren
- `Add startup config logging + deploy checklist in DEPLOYMENT.md`
- `Fix try-again context loss, memory save bug, add startup/crash notifications` — drie kritieke productiebugs gesloten
- `Fix: lege Slack-reply bij lege agent-response`
- `fix: create_gdoc gebruikt service account i.p.v. verlopen OAuth`

**27 mei 2026 — hardening (13 commits)**

- `feat: rate limiting per Slack-user (max 10 calls/uur)` — misbruikbeveiliging; configureerbaar via `RATE_LIMIT_MAX`
- `feat: wekelijkse backup bronnenlaag naar 09_Backup in Shared Drive` — cron: elke zondag 03:00, 4 snapshots bewaard
- `ci: syntax check vóór deploy — blokkeert bij Python-fouten`
- `ci: deploy trigger beperkt tot main only`
- `ci: approval gate toevoegen voor productie-deploys`
- `fix: thread-safe in-memory cache via _READ_CACHE_LOCK`
- `fix: invalid_thread_ts bij slash commands — antwoorden kwamen niet aan`
- `fix: Drive shortcuts resolven bij read_file`
- `fix: zes tech-debt items uit code review (CF 29/32/34/35/36/37)`

**28 mei 2026 — nieuwe features + laatste cleanup (15 commits, PR #19–21)**

- `feat: 08_Outcomes — win/loss geheugen voor Ainstein` — nieuwe map in Shared Drive: Ainstein raadpleegt gewonnen voorstellen als eerste, flaggt expliciet als logica uit verloren voorstellen wordt hergebruikt
- `feat: Slack Block Kit formatting voor gestructureerde Ainstein-antwoorden` — headers, tabellen en dikgedrukte tekst worden omgezet naar visuele Slack Block Kit-blokken
- `feat(gtm): voeg ICP-check en acquisitieprotocol toe aan sales skills` — ICP als Stap 0 bij qualify_lead en analyse_opportunity; `acquisitie_protocol.md` en `gtm_strategy.md` toegevoegd aan `06_Marketing`
- `brain.md: kennisarchitectuur herschikt — verrijken i.p.v. stapelen`
- `backup: schrijf naar externe Shared Drive i.p.v. bronnenlaag zelf`
- `remove startup write test — leaves stale files in Drive` — `_check_drive_write_access()` verwijderd: de test vervuilde Drive met `_ainstein_write_test` bestanden bij crashes

---

## 3. Skill-evolutie

| Datum | Aantal skills | Toegevoegd |
|---|---|---|
| 18 april 2026 | 3 | `analyse_opportunity`, `build_proposal`, `match_experts` |
| 29 april 2026 | 11 | `qualify_lead`, `prepare_discovery`, `map_objections`, `client_discovery_debrief`, `sharpen_positioning`, `create_content`, `adapt_messaging`, `debrief_to_messaging` |
| mei 2026 | 13 | `refine_proposal`, `review_feedback` |
| 26 mei 2026 | **14** | `dvv_check` |

---

## 4. Architectuurkeuzes en beslismomenten

### Multi-agent → single-agent (28 april 2026)
Tussen 21 en 28 april werd een multi-agent variant ontwikkeld (nooit in git gezet): aparte sales-agent, marketing-agent en orchestrator. Op 28 april bewust teruggedraaid naar één agent. Redenering: de gebruikersgroep is klein (Jörgen + experts in Slack), routing-overhead weegt niet op, cross-domain requests zijn natuurlijker in single-agent met thread-memory. De waardevolle inhoud uit de multi-agent fork (playbooks, output-contracts) werd gemigeerd naar `SKILL_PROMPTS`.

### Source layer uit repo (28 april 2026)
Data en code ontkoppeld via `AINSTEIN_SOURCE_ROOT` env var. Repo bevat alleen code, nooit brondata.

### Drive API via service account (18–21 mei 2026)
Overgang van OAuth (persoonlijk, verloopt) naar service account (`ainstein-bot@minkowski-ainstein.iam.gserviceaccount.com`). Service account heeft Contributor-rechten op de Minkowski Shared Drive; geen persoonlijke Drive-quota verbruikt.

### Persoonlijke → organisatie-owned Drive (21 mei 2026)
Thomas' gmail-gebaseerde Drive map (`AInstein_OUD`) vervangen door organisatie-owned Shared Drive (`Minkowski AInstein`, driveId `0AFvBEDYKrnHbUk9PVA`). Eigendom: Jörgen van der Sloot / Minkowski organisatie. Toegang: Jörgen, Thomas (thomas@minkowski.org), Charlotte van Veelen, ainstein-bot.

### Brain.md + losse skill-bestanden (8 mei 2026)
Systeemprompt opgesplitst: `brain.md` voor identiteit/operationele regels, aparte `.md` bestanden per skill in `skills/`. Beter onderhoudbaar; skills kunnen onafhankelijk worden gereviewed en aangepast.

---

## 5. Pull request overzicht

| PR | Datum | Inhoud |
|---|---|---|
| #1 | 29 april | Source discipline, skills uitgebreid, CLI-fixes |
| #2 | 29 april | Tweede batch fixes (dev → main) |
| #3 | 5 mei | Feedbacklus uitgebreid (capture, classify, consult, act) |
| #4 | 5 mei | Channel-feedback (niet alleen DMs) |
| #5 | 8 mei | Refactor: brain.md + losse skill-bestanden |
| #6 | 11 mei | Drive API backend, persistent logging, read_doc_comments |
| #7 | 12 mei | Voorstel-refinementloop, PPTX export, path traversal fix |
| #8 | 18 mei | VM-deployment, CI/CD, service account, caching |
| #9 | 21 mei | Shared Drive migratie (batch 1) |
| #10–15 | 21 mei | Shared Drive migratie (batch 2–7): save_note, list_folder, skills, shortcuts |
| #16 | 26 mei | DVV-skill, startup-logging |
| #17 | 26 mei | Productiebugs: try-again, memory save, startup-notificaties |
| #18 | 26 mei | Config logging + deploy-checklist |
| #19 | 28 mei | Slack Block Kit formatting |
| #20 | 28 mei | Rate limiting + backup naar externe Shared Drive |
| #21 | 28 mei | Slack bijlagen bij @mention in channels |

---

## 6. Infrastructuur — voor en na

| Onderdeel | Begin (18 april) | Nu (28 mei) |
|---|---|---|
| Runtime | Lokale terminal | Cloud VM (35.253.206.86), systemd service |
| Deploy | Handmatig | GitHub Actions (push → SSH → git pull → restart) |
| Bronnenlaag | Lokale map / Thomas' Gmail Drive | Minkowski Workspace Shared Drive (org-owned) |
| Auth Drive | OAuth (persoonlijk, verloopt) | Service account (vaste credentials) |
| CI | Geen | Syntax check (py_compile) vóór elke deploy |
| Branch-beleid | Vrij | Deploy alleen van `main`; approval gate voor productie |
| Beveiliging | Geen | Rate limiting (10 calls/uur/user), path traversal blokkering |
| Backup | Geen | Wekelijks, 4 snapshots, aparte Shared Drive |
| Geheugen | Geen | `08_Outcomes` (win/loss per voorstel) + `07_Feedback` (gaps-lus) |
| Output-formatting | Platte tekst | Slack Block Kit (headers, tabellen, bold) |

---

## 7. Wat is er nog niet gebouwd

Per 28 mei 2026 staan de volgende items op de roadmap maar zijn nog niet gerealiseerd:

- **Website-analyse** — DVV+AUB+SEO-analyse via Slack (DVV-check ✅, AUB-audit en website-scanner nog open)
- **Interactieve voorstel-refinementloop** — technisch gebouwd (12 mei), maar nog niet volledig in productie
- **Leerarchitectuur** — feedbacklus → episodisch geheugen → RAG (architecturele schuld A1–A4 op roadmap)
- **AUB-audit op bronnenlaag** — automatische kwaliteitscheck van bestaande brondocumenten
- **`AInstein_OUD` verwijderen** — oude gmail-gebaseerde Drive map, bewust uitgesteld
- **Calendar MCP** — token verlopen 19 mei 2026; `npx @cocal/google-calendar-mcp auth` nodig
- **Gmail MCP (Minkowski-inbox)** — technisch verbonden op gmail; beslissing Minkowski-inbox nog open
- **Slack MCP (Minkowski-workspace)** — wacht op org-goedkeuring

---

## 8. Kengetallen per fase

| Fase | Periode | Commits | PR's | Kernmijlpaal |
|---|---|---|---|---|
| 0 — Materiaal & verkenning | 18 maart – 16 april | — | — | Expert profielen, source layer, CLAUDE.md |
| 1 — Kick-off | 18–29 april | 16 | 2 | Eerste werkende bot, 11 skills, Drive API, single-agent |
| 2 — Verdieping | 5–12 mei | 21 | 5 | Brain.md refactor, voorstel-loop, Drive API backend |
| 3 — VM-deploy | 18–21 mei | 41 | 8 | Cloud VM, CI/CD, Shared Drive migratie, service account |
| 4 — Productie | 26–28 mei | 42 | 6 | Rate limiting, backup, Block Kit, Outcomes, DVV-skill |
| **Totaal** | **18 april – 28 mei** | **120** | **21** | |

---

## 9. Betrokkenen

| Persoon | Rol |
|---|---|
| Thomas Thiadens | Bouwen, deployen, beheren |
| Jörgen van der Sloot | Product owner, Shared Drive aangemaakt (21 mei), Content Manager |
| Charlotte van Veelen | Toegang Shared Drive |
| ainstein-bot@minkowski-ainstein.iam.gserviceaccount.com | Service account (Contributor-rechten op Shared Drive) |

---

*Dit rapport is automatisch gegenereerd op basis van git-geschiedenis, Claude Code sessiebestanden, bestandsdatums en persistente memory-bestanden. Alle datums zijn verifieerbaar via `git log --all --format="%ad %s" --date=format:"%Y-%m-%d" | sort` in `/Users/thomasthiadens/Ainstein`.*
