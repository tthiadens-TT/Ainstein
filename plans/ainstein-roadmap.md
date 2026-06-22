# Ainstein Ontwikkelroadmap

Laatste update: 2026-06-21 (volledige audit — alle sessies, memory-files, worktrees)
Status: Kennis-laag bewijs-fase actief. Evidence-bar nog niet gehaald.

---

## Kritische terugblik op dit plan

Vier aannames die het waard zijn te bevragen:

1. **"Evidence-bar" heeft geen deadline.** Criterium "Thomas/Jörgen promoveert ≥1 item" is afhankelijk van menselijk handelen zonder datum. Beslissing nodig: *wanneer* precies?

2. **Kennis-laag is gebouwd maar niet teruggekoppeld.** `kennis_laag.md` bestaat in Drive, maar Ainstein leest hem niet mee bij antwoorden. Dood document totdat K1 geïmplementeerd is.

3. **Drive-connector is geblokkeerd.** Google Workspace AI-policy-label blokkeert `mcp__4e943b1e` voor de Shared Drive. Dit is geen tijdelijk probleem — vereist admin-actie van Thomas/Jörgen.

4. **NN Group kennisbank: volledig plan, nooit geïmplementeerd.** Sessie 19 juni heeft een compleet uitgewerkt plan opgeleverd (`plans/laten-we-met-1-precious-pearl.md`). Nooit uitgebouwd. Formele go/no-go ontbreekt.

---

## Wat live is (productie, 21 juni 2026)

| Component | Commit/PR |
|---|---|
| Ainstein Slack bot (SocketMode) | — |
| Jamie webhook pipeline | PR #27 |
| Ainstein karakter-update (uitdager/denkpartner) | PR #28 |
| Smart meeting routing (discovery / check-in / follow-up / internal) | commit `18 jun sessie` |
| Feedback loop (gaps.md inject + hallucinatie-verificatie + auto-review) | commit `4205d75` |
| Map-reduce kennis-extractie per bron | commit `c9bbf42` |
| Tijd-dimensie + resumability in kennis-extractie | commit `1a3820a` |
| SSL certifi-fix in `_slack_notify` | commit `b4118c9` |
| Scrapers: LinkedIn, Medium (403-geblokkeerd), Substack, minkowski.org, futuresready.com | commit `b716a23` |
| Jamie-transcripten als plain-text bakje | commit `d6a3553` |
| Tavily web search (vervangt DDGS, DDGS blijft fallback) | commit `7154a08` |
| Slack-scraper (exports als .md in Drive) | commit `15bec6c` |
| Rate limiting (10 calls/uur per user) | — |
| Backup: GCP snapshots (dagelijks) + Drive backup (wekelijks, GitHub Actions) | — |
| CI/CD: auto-deploy op main, syntax check | — |

---

## URGENT — direct oppakken

### ~~AINSTEIN-BACKUP-DEST: env var ontbreekt op VM~~ ✅ OPGELOST
`AINSTEIN_BACKUP_DEST_ID=0AAnoQGN-2hbvUk9PVA` staat in `.env` op VM (geverifieerd 2026-06-22 via SSH). Was een foutieve claim in de roadmap.

### ~~DRIVE-CONNECTOR-BLOKKADE~~ ✅ GEEN ACTIE NODIG — al opgelost (2026-06-19)
De `mcp__4e943b1e` connector kan `text/plain` bestanden inderdaad niet lezen ("ineligible to be used in generative AI contexts"). Maar dit is **geen belemmering**: de service account leest plain-text wél normaal, en de service account is altijd de bedoelde leesweg geweest voor `kennis_laag.md` en `_bronmateriaal`. De MCP connector is alleen relevant voor Claude Code review-sessies, niet voor de productie-bot of K1. Gedocumenteerd in `deploy_checklist_and_lessons.md` (2026-06-19). Geen admin-actie nodig.

---

## Fase 0 — Mensenwerk, geen code nodig

| # | Item | Wie | Actie |
|---|---|---|---|
| H1 | **08_Outcomes vullen** | Thomas | NN Group voorstel/outcome toevoegen als win/loss-record in Drive `08_Outcomes` |
| H2 | **Evidence-bar — beslissing met datum** | Thomas+Jörgen | Promoveer ≥1 item van `kennis_laag.md` naar vaste bronnenlaag, óf benoem een gap dat tot actie leidt. Stel een concrete deadline. |
| H3 | **Notion pagina's delen** | Thomas | Notion-UI → Settings → Connections → deel pagina's met de Claude MCP-integratie |
| H4 | **AInstein_OUD opruimen** | Thomas | `tthiadens@gmail.com` → Google Drive → oude map verwijderen |
| H5 | **Calendar token beslissing** | Thomas | `normal` (tthiadens@gmail.com) token verlopen. Fix: `npx @cocal/google-calendar-mcp auth`. Of: is deze agenda nog nodig? |
| H6 | **Jörgen-DM validatie** | Jörgen | Eerste echte Minkowski-meeting waarbij Jörgen aanwezig is via Jamie → DM + proactieve voorstellen valideren in productie |
| H7 | **Drive docs kwaliteit beoordelen** | Thomas+Jörgen | Hei-dag Waardestromen + SNI Non-Life debrief — zijn de automatisch aangemaakte docs commercieel bruikbaar? |

---

## Fase 1 — Kennis aansluiten (na H1+H2, ~1-2 weken)

### K1. Terugkoppeling kennis-laag
**Probleem:** `kennis_laag.md` bestaat in Drive maar Ainstein leest hem niet mee bij antwoorden. De extractie-cyclus produceert output zonder invloed op gedrag.
**Twee paden:**
- (A) Ainstein injecteert `kennis_laag.md` automatisch bij voorstellen/matching — aanpassing in `agent.py`. Schaalbaar.
- (B) Thomas promoveert handmatig naar de reguliere bronnenlaag. Veiliger voor kwaliteitscontrole.
**Beslissing open:** welk pad?
**Blokkade:** Drive-connector AI-policy (zie URGENT). Als die niet opgelost is, werkt pad A niet via MCP.
**Effort:** 2-3 uur (pad A), <1 uur (pad B).

### K2. Kennis-laag contextprobleem — structurele fix
**Probleem:** Bij alle bronnen samen loopt input op tot 267k+ chars → API-timeout bij iteratie 4-5. Map-reduce structuur is gebouwd (commit `c9bbf42`) maar lost het niet volledig op.
**Fix:** Zorg dat geen enkele run > 50k chars input verwerkt. Extractie per oorsprong in losse runs, ook in de reduce-stap.
**Effort:** 3-4 uur.

### K-MEDIUM. Medium-scraper werkend maken
**Probleem:** `scrape_medium.py` bestaat maar Medium geeft HTTP 403 bij urllib én bij `?format=json`. LinkedIn en Minkowski-sites zijn gedaan; Medium ontbreekt in de kennis-laag.
**Oplossing:** Side-panel-methode (Thomas plakt content door vanuit ingelogde browser), of alternatieve API.
**Wie:** Thomas (side-panel) of Claude Code (andere aanpak).
**Effort:** 1-2 uur.

### K-BRON-OVERZICHT. Afvinkcriterium per kennisbron
**Probleem:** `bronnen.json` heeft 10 bronnen, maar er is geen overzicht van welke volledig gescraped zijn en welke niet. Maakt volledigheid onbeoordeelbaar.
**Actie:** Voeg `status`-veld toe aan `bronnen.json` per bron: `done` / `partial` / `blocked` + reden.
**Effort:** <1 uur.

### K4. GitHub Actions scheduling kennis-extractie
**Conditie:** Na evidence-bar (H2).
**Wat:** Wekelijkse cron-job draait `run_kennisextractie.py` automatisch.
**Effort:** 2 uur.

### J. Smart meeting routing — verificatie
**Status:** Basisrouting gebouwd in sessie 18 juni (detection: discovery/check_in/follow_up/internal). Nog **niet geverifieerd** in productie met echte meetings. Staat als afgerond maar is niet beproefd.
**Actie:** Eerste echte Jörgen-meeting afwachten → loggen welk type gedetecteerd werd → verfijnen indien nodig.

---

## Fase 2 — Kennis verbreden (na K1, ~2-4 weken)

### K3. Gmail als onafhankelijke klantstem
**Wat:** Client-mails analyseren op vraagstukken en transformatie-signalen.
**Beslissing open:** `tthiadens@gmail.com` of `thomas@minkowski.org`?
**Effort:** 3-4 uur.

### K5. Spotify-podcast Minkowski Spacetime
**Wat:** 6+ afleveringen met klantgasten als kennisbron. Audio → transcript tooling nodig.
**Blokkade:** Spotify API levert geen transcripten. Whisper op VM of externe service?
**Effort:** 3-4 uur (excl. tooling-keuze).

---

## Fase 3 — Commerciële intelligentie (~1-2 maanden)

### B. Website-analyse via Slack
**Wat:** `/dvv-website [URL]` → DVV + AUB + SEO analyse → Slack-rapport.
**Blokkade:** Playwright installeren op VM voor JS-rendered content.
**Effort:** 4-6 uur.

### B-SEO. SEO als derde framework
**Conditie:** Na B live. Technisch, on-page, autoriteitslaag toevoegen.
**Effort:** 2-3 uur extra.

### E. AUB-audit bronnenlaag
**Wat:** Maandelijkse scan Drive op verouderde/unieke/onbetrouwbare bronnen → "5 zwakste plekken" naar Thomas.
**Effort:** 3-4 uur.

### D. Versterkte feedbackloop (Stap 1 leerarchitectuur)
**Wat:** Ainstein analyseert wekelijks `gaps.md`, detecteert 3+ vergelijkbare patronen, stuurt Thomas een Slack-voorstel ter goedkeuring.
**Effort:** 2-3 uur.

### G. Pipeline tracker
**Wat:** Google Sheet of Doc als acquisitie-pipeline. `/pipeline` → status actieve leads.
**Beslissing open:** Sheet (leesbaarder) of Doc (makkelijker schrijven via API)?
**Effort:** 2-3 uur.

### TAVILY-MONITORING. Tavily API-limiet monitoring
**Probleem:** Gratis plan = 1.000 calls/maand. Geen monitoring. Als limiet bereikt valt Ainstein stil terug op DDGS zonder waarschuwing.
**Fix:** Teller in `.env` of simpele log-analyse die Thomas wekelijks ziet.
**Effort:** 1 uur.

### CREATE-CONTENT-PROACTIEF. Beslissing: proactieve voorstellen bij interne meetings?
**Gesignaleerd 17 juni:** create_content-meetings genereren geen proactieve voorstellen. "Bewuste keuze of vergeten?" — nooit beantwoord.
**Actie Thomas:** Ja of nee. Bij ja: 1-2 uur implementatie.

---

## Fase 4 — Strategische uitbreiding (Q3 2026)

### NN-KENNISBANK. Externe kennisbank per klant (start: NN Group)
**Situatie:** Sessie 19 juni heeft een volledig uitgewerkt plan opgeleverd in `plans/laten-we-met-1-precious-pearl.md`. Scripts, skill, Drive-structuur — alles beschreven. Nooit geïmplementeerd.
**Actie:** Formele go/no-go van Thomas. Bij go: Claude Code bouwt `scrape_client_research.py`, `run_client_kennisextractie.py`, skill `client_profile.md`, `clients/nn_group.json`.
**Effort:** 5-6 uur bij go.

### C. Interactieve voorstel-refinement loop
**Wat:** Google Doc comments → `/refine-comments` → Ainstein herschrijft → `/export-deck` → PPTX.
**Plan:** Volledig uitgewerkt in `ainstein-is-de-assistent-merry-swing.md`.
**Effort:** ~7 uur.

### D Stap 2. Episodisch geheugen
**Conditie:** Stap 1 (versterkte feedbackloop) werkt.
**Effort:** 3-4 uur.

### H. Geautomatiseerde lead-radar
**Wat:** Cron-job maandag 08:00 — web searches → shortlist 3-5 prospects naar Jörgen.
**Effort:** 3-4 uur.

### I. Competitive intelligence skill
**Wat:** `competitive_brief` — gerichte web searches op wie bij prospect al werkt, Minkowski-onderscheid per concurrent.
**Effort:** 2-3 uur.

### GTM-THOMAS. Thomas persoonlijke GTM-propositie
**Situatie:** Besproken 19 juni, gepland voor "volgende sessie". Ainsteins uitdaagvraag ("wat is het specifieke probleem dat jij voor hen oplost?") nooit beantwoord. Nooit opgepakt.
**Actie:** Thomas initieert sessie zodra relevant.

### JORGEN-MAGIC. Jörgens vraag: 'wat is Minkowski's magic?'
**Situatie:** Ainstein stelde voor dit als nulmeting te doen. Sessie eindigde daarna. Nooit uitgevoerd.
**Actie:** Ainstein kan dit draaien zodra Thomas groen licht geeft.

---

## Fase 5 — Architectuursprong (Q4 2026)

| Item | Wat | Effort |
|---|---|---|
| **A1. RAG / vector search** | FAISS of PGVector — semantisch zoeken. Fundament voor U7+ | 10-15 uur |
| **U2. Conversie-feedbackloop** | Systematisch hergebruik logica uit gewonnen proposals (vereist H1) | 3-4 uur |
| **U3. CRM-context per klant** | Klantdossier per organisatie — keuze: Drive-structuur of echte CRM | 2-3 uur |
| **U4. Pipeline management** | Prioritering actieve kansen op status, deadline, experts | 4-6 uur |
| **U5. Klant-Agent** | Tweede agent die elk voorstel aanvalt met bezwaren vóór oplevering | 6-8 uur |
| **U6. Stakeholder mapping** | Saboteur, champion, beslisser per kans | 3-4 uur |
| **U8. Expert availability** | Agenda's vaste experts koppelen aan matching | 4-6 uur |
| **S8. Live pricing engine** | Rekentool i.p.v. tekstuele prijslijsten | 6-8 uur |
| **I3. Cloud Logging** | GCP Cloud Logging i.p.v. lokale VM-logs | 3-4 uur |
| **I4. conversations.db versleuteling** | SQLCipher of encrypted disk | 4-6 uur |

---

## Hygiëne — klein maar niet vergeten

| # | Item | Wie | Urgentie |
|---|---|---|---|
| HY1 | **PPTX Sen ExtraBold testen** | Claude Code | `rid = 'rIdSenEB'` hardcoded — visueel testen op machine zonder Sen-installatie vóór klantverstrekking | Laag |
| HY2 | **reviews/ directory** | Thomas | In git (versiebeheer) of `.gitignore`? Al gevlagd 15 juni, nooit besloten | Laag |
| HY3 | **Weekly routines aanmaken** | Thomas | Wekelijkse skills audit, expert index check, feedback digest voorgesteld. Go of no-go? | Laag |
| HY4 | **Drive MCP token structureel oplossen** | Thomas+Claude | Token verloopt frequent (~1 week). Service account auth vs. OAuth refresh? | Middel |

---

## Openstaande beslissingen (vereisen Thomas/Jörgen input)

| # | Beslissing | Impact | Urgentie |
|---|---|---|---|
| D1 | **Terugkoppeling kennis-laag** — Ainstein injecteert automatisch of Thomas promoveert handmatig? | K1 | Hoog |
| D2 | **Drive-connector AI-policy** — admin-actie of alternatief documenteren? | K1, kennis-integratie | Hoog |
| D3 | **Evidence-bar datum** — wanneer precies is de bar gehaald? | K4, automatisering | Hoog |
| D4 | **NN Group kennisbank** — go of no-go op het 19-juni plan? | NN-KENNISBANK | Middel |
| D5 | **create_content-meetings** — proactieve voorstellen ja of nee? | CREATE-CONTENT | Middel |
| D6 | **Gmail-account voor klantstem** — `tthiadens@gmail.com` of `thomas@minkowski.org`? | K3 | Middel |
| D7 | **Pipeline tracker formaat** — Google Sheet of Google Doc? | G | Laag |
| D8 | **Calendar normal-token** — nog nodig, of verwijderen? | H5 | Laag |
| D9 | **Slack MCP org-goedkeuring** — externe blokkade, wacht op Jörgen/org-beheerder | SLACK-MCP | Extern |
| D10 | **Webhook-domein upgrade** — zodra Thomas toegang tot minkowski.nl: A-record + certbot | DNS | Extern |

---

## Hoe dit bestand gebruiken

Dit bestand staat in de repo onder `plans/ainstein-roadmap.md`.

> "Lees `plans/ainstein-roadmap.md` en ga verder waar we gebleven waren."

Implementatiedetails horen in commit messages en CLAUDE.md, niet hier.
