# Ainstein Ontwikkelroadmap

Laatste update: 2026-06-21
Status: Kennis-laag bewijs-fase actief. Evidence-bar nog niet gehaald.

---

## Kritische terugblik op dit plan

Voordat je dit als leidraad gebruikt: vier aannames die het waard zijn om te bevragen.

1. **"Evidence-bar" is een vage gate.** Het criterium "Thomas/Jörgen promoveert ≥1 item naar bronnenlaag" is afhankelijk van menselijk handelen dat geen deadline heeft. Zonder expliciete datum blijft dit eeuwig open. Beslissing nodig: *wanneer* is de bar gehaald, en wie bewaakt dat?

2. **De kennis-laag is gebouwd maar niet teruggekoppeld.** `kennis_laag.md` bestaat in Drive, maar Ainstein leest hem niet mee bij antwoorden. Dat maakt hem nu een dood document. De cyclus is pas gesloten als de laag invloed heeft op output.

3. **De roadmap is lang maar zonder prioriteit.** Items B t/m I + U2–U9 staan allemaal als "volgende stap" zonder onderscheid. Als alles prioriteit heeft, heeft niets prioriteit. Hieronder staat een expliciete volgorde.

4. **Smart meeting routing (J) is nooit besloten.** Er is een vraag gesteld ("eerst afstemmen met Jörgen of direct implementeren?"), maar nooit beantwoord. Elke nieuwe Jamie-meeting runt nu dezelfde debrief — ook check-ins.

---

## Wat live is (productie, 21 juni 2026)

| Component | Status | Commit/PR |
|---|---|---|
| Ainstein Slack bot (SocketMode) | ✅ Live | — |
| Jamie webhook pipeline | ✅ Live | PR #27 |
| Ainstein karakter-update (uitdager/denkpartner) | ✅ Live | PR #28 |
| Feedback loop (gaps.md inject + hallucinatie-verificatie) | ✅ Live | commit `4205d75` |
| Map-reduce kennis-extractie | ✅ Live | commit `c9bbf42` |
| Tijd-dimensie + resumability in kennis-extractie | ✅ Live | commit `1a3820a` |
| SSL certifi-fix in `_slack_notify` | ✅ Live | commit `b4118c9` |
| Scrapers: LinkedIn, Medium, Substack, minkowski.org, futuresready.com | ✅ Live | commit `b716a23` + `cdbd99b` |
| Jamie-transcripten als plain-text bakje | ✅ Live | commit `d6a3553` |
| Tavily web search (vervangt DDGS) | ✅ Live | commit `7154a08` |
| Rate limiting (10 calls/uur per user) | ✅ Live | — |
| Backup: GCP snapshots + Drive backup via Actions | ✅ Live | — |
| CI/CD: auto-deploy op main, syntax check | ✅ Live | — |

---

## Open items — geordend naar urgentie

### Fase 0 — Direct oppakken (mensenwerk, geen code nodig)

| # | Item | Wie | Actie | Effort |
|---|---|---|---|---|
| H1 | **08_Outcomes vullen** | Thomas | NN Group voorstel/outcome toevoegen als win/loss-record in Drive `08_Outcomes` | 1 uur |
| H2 | **Evidence-bar — beslissing** | Thomas+Jörgen | Promoveer ≥1 item van kennis_laag.md naar vaste bronnenlaag, óf benoem een gap dat tot actie leidt. Daarna: automatisering ontgrendeld. | <1 uur |
| H3 | **Notion pagina's delen** | Thomas | In Notion-UI: deel pagina's met de Notion-integratie. Nu staat de connector klaar maar heeft 0 inhoud. | <1 uur |
| H4 | **AInstein_OUD opruimen** | Thomas | `tthiadens@gmail.com` → Google Drive → oude map verwijderen | <1 uur |
| H5 | **Calendar token beslissing** | Thomas | `normal` (tthiadens@gmail.com) token verlopen. Fix: `npx @cocal/google-calendar-mcp auth`. Of: is deze agenda nog nodig? | <1 uur |

---

### Fase 1 — Laag aansluiten (na H1+H2, ~1-2 weken)

#### K1. Terugkoppeling kennis-laag
**Probleem:** `kennis_laag.md` in Drive bestaat maar Ainstein leest hem niet. De extractie-cyclus produceert output zonder invloed.
**Oplossing:** Één van twee paden — (a) Ainstein injecteert `kennis_laag.md` automatisch bij voorstellen/matching (lichte aanpassing in `agent.py`), of (b) Thomas promoveert handmatig naar de reguliere bronnenlaag. Pad A is schaalbaar. Pad B is veiliger voor kwaliteitscontrole. Beslissing open.
**Effort:** 2-3 uur (pad A), <1 uur (pad B).

#### K2. Kennis-laag contextprobleem — structurele fix
**Probleem:** Bij grote dataset (alle bronnen samen) loopt input op tot 267k+ chars → API-timeout bij iteratie 4-5. Tijdelijke workaround (timeout-fix + resumability) is live maar lost het niet structureel op.
**Echte fix:** Extractie per oorsprong draaien in losse runs (al gedeeltelijk aanwezig via map-reduce). Verfijnen zodat geen enkele run > 50k chars input verwerkt.
**Effort:** 3-4 uur.

#### J. Smart meeting routing
**Probleem:** Jamie-webhook past nu `client_discovery_debrief` toe op élke meeting. Check-ins, interne vergaderingen en statusupdates krijgen een volledige klantdebrief — dat is fout.
**Beslissing nodig:** Direct implementeren, of eerst afstemmen met Jörgen over exacte scope?
**Technisch:** Kleine uitbreiding in `transcript_processor.py` — detect check-in vs client op basis van title/deelnemers, stuur dan naar lichtere skill of skip.
**Effort:** 2-3 uur.

---

### Fase 2 — Kennis verbreden (na K1, ~2-4 weken)

#### K3. Gmail als onafhankelijke klantstem
**Wat:** Klant-mails analyseren op vraagstukken, pijnpunten, transformatie-signalen — de echte klantperspectief die ontbreekt in de huidige laag.
**Waarom:** Nu is de laag sterk Minkowski-centrisch (Jörgen, Thomas, minkowski.org). Gmail-MCP is al verbonden.
**Beslissing open:** `tthiadens@gmail.com` of `thomas@minkowski.org`? Welke mails zijn relevant?
**Effort:** 3-4 uur.

#### K4. GitHub Actions scheduling voor kennis-extractie
**Conditie:** Pas na evidence-bar (H2) gehaald.
**Wat:** Wekelijkse cron-job draait `run_kennisextractie.py` automatisch — niet meer handmatig op VM.
**Effort:** 2 uur.

#### K5. Spotify-podcast Minkowski Spacetime
**Wat:** 6+ afleveringen met klantgasten = rijkste onafhankelijke klantstem die beschikbaar is. Audio → transcript nodig.
**Blokkade:** Tooling voor audio-transcriptie ontbreekt. Whisper op VM, of externe service?
**Effort:** 3-4 uur (excl. transcriptie-tooling keuze).

---

### Fase 3 — Commerciële intelligentie (na Fase 2, ~1-2 maanden)

#### B. Website-analyse via Slack
**Wat:** Trigger `/dvv-website [URL]` → Ainstein analyseert op DVV + AUB + SEO → Slack-rapport.
**Stand:** DVV + AUB frameworks al gebouwd (`dvv_check` skill). Website-scan al gedaan voor minkowski.org (mei 2026). Nu productief maken via Slack.
**Blokkade:** Playwright installeren op VM voor JS-rendered content.
**Effort:** 4-6 uur (Versie A zonder Playwright: 4u; met Playwright: 6u).

#### D. Leerarchitectuur — Stap 1: Versterkte feedbackloop
**Wat:** Ainstein analyseert wekelijks `gaps.md`, detecteert 3+ vergelijkbare patronen, stuurt Thomas een Slack-voorstel: "voeg X toe / pas skill Y aan" — ter goedkeuring, niet autonoom.
**Waarom:** Nu is Thomas de bottleneck voor bronnenlaag-updates. Dit maakt patronen zichtbaar zonder extra werk.
**Effort:** 2-3 uur.

#### G. Pipeline tracker
**Wat:** Google Sheet of Doc als acquisitie-pipeline. `/pipeline` → status actieve leads.
**Beslissing open:** Sheet (makkelijker te bekijken) of Doc (simpeler te schrijven via API)?
**Effort:** 2-3 uur.

---

### Fase 4 — Strategische uitbreiding (Q3 2026)

#### C. Interactieve voorstel-refinement loop
**Wat:** Google Doc comments per sectie → `/refine-comments` → Ainstein herschrijft → `/export-deck` → PPTX.
**Plan:** Volledig uitgewerkt in `ainstein-is-de-assistent-merry-swing.md`.
**Effort:** ~7 uur (Fase 1: 4u, Fase 2: 3u).

#### D. Leerarchitectuur — Stap 2: Episodisch geheugen
**Wat:** Na afgeronde sessie: gestructureerde les naar `08_Episodes` in Drive (klanttype, vraagstuk, format, budget, wat resoneerde).
**Conditie:** Stap 1 (versterkte feedbackloop) werkt.
**Effort:** 3-4 uur.

#### H. Geautomatiseerde lead-radar
**Wat:** Cron-job maandag 08:00 — web searches op Minkowski-relevante signalen → shortlist 3-5 prospects naar Jörgen.
**Conditie:** GTM-laag bewezen in praktijk.
**Effort:** 3-4 uur.

#### I. Competitive intelligence skill
**Wat:** Nieuwe skill `competitive_brief` — 3-5 gerichte web searches op wie er bij prospect al werkt, formuleert Minkowski-onderscheid.
**Effort:** 2-3 uur.

---

### Fase 5 — Architectuursprong (Q4 2026 of later)

| Item | Wat | Effort |
|---|---|---|
| **A1. RAG / vector search** | FAISS of PGVector — semantisch zoeken i.p.v. keyword grep. Fundament voor alle schaalbare retrieval. | 10-15 uur |
| **D Stap 3. Semantische zoeklaag** | Bouwt op A1. | 4-5 uur |
| **S4. Klant-Agent (U5)** | Tweede agent die elk voorstel aanvalt met bezwaren vóór oplevering. | 6-8 uur |
| **S8. Live pricing engine (U9)** | Rekentool i.p.v. tekstuele prijslijsten. | 6-8 uur |
| **I3. Cloud Logging** | GCP Cloud Logging i.p.v. lokale VM-logs. | 3-4 uur |
| **I4. conversations.db versleuteling** | SQLCipher of encrypted disk volume. | 4-6 uur |

---

## Openstaande beslissingen (vereisen Thomas/Jörgen input)

| # | Beslissing | Context | Urgentie |
|---|---|---|---|
| D1 | **Terugkoppeling kennis-laag** — Ainstein injecteert automatisch, of Thomas promoveert handmatig? | K1 hangt hiervan af | Hoog |
| D2 | **Smart meeting routing** — Direct implementeren, of eerst scope afstemmen met Jörgen? | Elke meeting runt nu volledige debrief | Hoog |
| D3 | **Gmail-account** — `tthiadens@gmail.com` of `thomas@minkowski.org` als klantstem? | K3 hangt hiervan af | Middel |
| D4 | **Pipeline tracker** — Google Sheet of Google Doc? | G hangt hiervan af | Laag |
| D5 | **Calendar normal-token** — Nog nodig, of verwijderen? | H5 | Laag |
| D6 | **Webhook-domein** — Zodra Thomas toegang tot minkowski.nl: A-record instellen + certbot | Upgrade van DuckDNS | Laag |

---

## Hoe dit bestand gebruiken

Dit bestand staat in de repo onder `plans/ainstein-roadmap.md`.
Gebruik het als context aan het begin van elke nieuwe Claude Code sessie:

> "Lees `plans/ainstein-roadmap.md` en ga verder waar we gebleven waren."

De roadmap beschrijft intenties en beslissingen — geen implementatiedetails. Implementatiedetails horen thuis in de commit messages en CLAUDE.md.
