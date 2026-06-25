# Ainstein Backlog

*Bijgewerkt: 25 juni 2026 — twee architectuuropties toegevoegd: Optie 2 (Claude Projects tutorial, NU starten) en Optie 3 (MCP Server expose, later)*
*Beheerd door: Claude Code + Thomas — elke sessie bijwerken*

Dit is de centrale backlog voor Ainstein. Alle openstaande items — acties, bugs, ideeën, todo's — staan hier met context en prioriteit. Niet in CLAUDE.md (dat is sessiememorie), niet in losse documenten.

**Gebruik:**
- Begin elke sessie: dit bestand lezen (Session Start Protocol stap 3)
- Sluit elke sessie af: dit bestand bijwerken
- Afgerond item: verplaatsen naar ✅ Gedaan, niet verwijderen

---

## 🔴 Actief probleem

**Geen actief blokkerend probleem op dit moment.**

---

## 🟡 Volgende stap (prioriteit 1)

### 08_Outcomes vullen — actie Thomas/Jörgen
**Wat:** Concrete win/loss-records toevoegen aan `08_Outcomes` in Drive.
**Waarom:** Ainstein heeft instructie om `08_Outcomes` te raadplegen bij elk voorstel, maar de map is leeg. Commerciële lessen gaan verloren.
**Concrete cases die nu ontbreken:**
- NN IC — gewonnen (mei 2026): wat werkte, welke argumentatie, welk tarief
- Cathalijne — verloren op tarief bij Pierre: wat was het gat, wat had anders gekund
**Actie Thomas/Jörgen:** template invullen. Vijf minuten werk, directe waarde voor elk volgend voorstel.

---

## 📋 Backlog — Technisch (bouwwerk)

### 44 `claude/*` branches opruimen
**Wat:** 44 lokale `claude/*` branches accumuleren door worktree-gebruik. Groeien elke sessie.
**Actie:** `git branch --list 'claude/*' | xargs git branch -d` (verwijdert alleen volledig gemerged). Check eerst: `git branch --list 'claude/*' --no-merged main`.
**Prioriteit:** laag — rommelt, blokkeert niets.

### dev-branch cleanup
**Wat:** `dev` staat 10 commits voor op `main` met deels verouderd werk. De skills-verbeteringen en de meeste Drive-fixes zijn al apart op main gecommit. Dev bevat mogelijk unieke commits (save_note refactor, folder hint depth, deploy.yml health check).
**Actie:** `git diff main...dev -- *.py` draaien, unieke waardevolle commits identificeren, cherry-pick of delete. Daarna `dev` verwijderen of opnieuw baseren op main.
**Prioriteit:** laag — niets blokkeert productie, maar de branch rommelt.

### Klant-Agent — adversariale voorstelreview
**Wat:** Tweede API-aanroep na `build_proposal`. Speelt kritische klant (CHRO, inkoper, directeur) — genereert 3–5 scherpe bezwaren op het concept. Ainstein verwerkt ze en levert versterkt eindvoorstel. Thomas ziet alleen het eindresultaat + optioneel een "Verwerkte kritiek"-sectie.
**Architectuur:** tweede `client.messages.create()` aanroep in `agent.py`, geen tools, geen loop. Max 1500 tokens, 60s timeout. Bezwaartaxonomie uit `map_objections.md` als kader.
**Status:** volledig plan uitgeschreven. Vier beslissingen nodig van Thomas vóór bouw:
1. Bezwaren zichtbaar in Slack? (altijd als thread-reply / alleen eindvoorstel)
2. Altijd aan bij `build_proposal`, of opt-in?
3. Timeout >3 min → concept zonder Klant-Agent. Akkoord?
4. Taal bezwaren: altijd Nederlands of volgt het voorstel?
**Aanbeveling:** altijd aan, bezwaren als thread-reply, Nederlands, timeout-fallback. Eén "nee" van Thomas is genoeg om een default aan te passen.
**Effort:** 2,5–3,5 uur.

### design_program skill — van voorstel naar programmaontwerp
**Wat:** Na acceptatie van een voorstel helpt Ainstein de uitvoeringsfase ontwerpen: dag-voor-dag structuur, modulelogica, expert-matching voor de uitvoering.
**Aanpak:** nieuwe skill `design_program.md`, bouwt voort op `build_proposal` output.
**Effort:** 3–4 uur. Eerst Klant-Agent bouwen.

### Bug: `slack_nn-schade-inkomen_2026-05.md` onleesbaar
**Wat:** dit bestand is onleesbaar in twee onafhankelijke bronnen (Slack-scraper + Jamie). Structureel technisch probleem.
**Actie:** bestand inspecteren op VM, scraper-output checken op encoding/formaat-fouten.
**Prioriteit:** medium.

### `audit_claude_md.py` toevoegen aan GitHub Actions CI
**Wat:** `scripts/audit_claude_md.py` draait nu alleen handmatig. De deploy-workflow doet alleen een syntax-check. Als je een nieuwe skill of module toevoegt zonder CLAUDE.md bij te werken, pikt CI dit niet op.
**Actie:** `python3 scripts/audit_claude_md.py` toevoegen als stap in `.github/workflows/deploy.yml` na de syntax-check.
**Effort:** <30 min.
**Prioriteit:** medium — voorkomt stille CLAUDE.md-drift.

### Smart meeting routing verificeren in productie
**Wat:** `transcript_processor.py` detecteert meeting types (discovery/check_in/follow_up/internal) en routeert naar de juiste skill. Code bestaat, maar is nog niet geverifieerd met een echte Jörgen-Jamie meeting waarbij het type-detectie expliciet getest is.
**Actie:** na de eerste Jörgen-meeting via Jamie: check logs op `meeting_type` — klopt het gedetecteerde type?
**Prioriteit:** laag — wachten op volgende echte meeting.

### Bug: `feedback.py` auto-review trigger onbetrouwbaar
**Wat:** `_open_count` is een in-memory teller die reset bij elke botherstart. De auto-review trigger (drempel 10) bereikt de drempelwaarde mogelijk nooit als de bot regelmatig herstart via GitHub Actions deployments.
**Actie:** teller persistent maken (bijv. eenvoudig tekstbestand op VM) of drempel drastisch verlagen.
**Prioriteit:** laag — feedback loop werkt, trigger is alleen onbetrouwbaar.

### `pptx_builder.py` hardcoded relationship ID
**Wat:** `rid = "rIdSenEB"` (regel 123) is hardcoded. Bij een tweede font collideren relationship-IDs in `presentation.xml.rels`.
**Actie:** dynamisch genereren bij uitbreiding. Nu geen actie nodig.
**Prioriteit:** laag — pas relevant als tweede font wordt toegevoegd.

### `tools.py` Tavily `search_depth` hardcoded
**Wat:** `search_depth="advanced"` hardcoded op regel 1650. Advanced kost meer API-credits dan `"basic"`. Op de gratis tier (1.000/maand) kan dit het quotum sneller uitputten.
**Actie:** `TAVILY_SEARCH_DEPTH` env var toevoegen (default `"basic"`).
**Prioriteit:** laag.

### Legacy Google Doc Slack-bestanden verwijderen uit Drive
**Wat:** Drie bestanden `slack_C09CEQ29AU8_2026-04/05/06` staan in Drive als `application/vnd.google-apps.document`. Vervangen door plain-text `.md`-bakjes na fix in commit `15bec6c`. Kunnen worden verwijderd.
**Actie:** handmatig verwijderen in Drive via de Ainstein Shared Drive.
**Prioriteit:** laag — rommelt, blokkeert niets.

### Klantbronnen als kennisbron — websites, jaarverslagen, nieuws
**Wat:** publiek beschikbare informatie over (potentiële) klanten toevoegen als bron aan de kennis-laag. Per klant: website, jaarverslag, persberichten, LinkedIn. Geeft Ainstein context over de wereld van de klant — vóórdat een voorstel of meeting begint.
**Eerste kandidaat:** NN Group (ankerklant, 300+ deelnemers, multi-year). Thomas denkt dat er al een sessie/item over bestaat — nog te traceren.
**Aanpak:** `scrape_client.py` per klant, output naar `06_Marketing/_bronmateriaal/klanten/<klantnaam>/`. Zelfde plain-text .md bakje als andere bronnen. Origine: `klant-extern`.
**Waarde:** Ainstein kan in proposals en meetings zeggen "jullie jaarverslag noemt X — dat raakt precies aan Y." Echte onafhankelijke stem, niet alleen Minkowski-perspectief.
**Status:** in de maak — nog geen code.
**Prioriteit:** medium.

### Kennis-laag automatiseren
**Wat:** `run_kennisextractie.py` automatisch via GitHub Actions scheduling.
**Trigger (nog niet bereikt):** ≥1 promotie van kennis naar bronnenlaag, óf een say-vs-sell-gat dat aantoonbaar tot een commerciële actie leidde.
**Prioriteit:** laag — evidence bar nog niet gehaald.

### Kennis terugkoppeling naar bronnenlaag
**Wat:** mechanisme om geëxtraheerde kennis te bevorderen naar de vaste bronnenlaag (01–08) na handmatige bevestiging.
**Aanpak:** afhangt van K1-pad beslissing (zie Beslissingen).
**Prioriteit:** laag — geblokkeerd door beslissing.

### Webhook URL upgraden naar `webhook.minkowski.nl`
**Wat:** DuckDNS-URL vervangen door professioneel Minkowski-domein.
**Aanpak:** A-record `webhook.minkowski.nl → 35.253.206.86` + certbot opnieuw uitvoeren.
**Blokkade:** Thomas heeft nog geen toegang tot het Minkowski domein. Niets aan te doen tot dan.

### Prompt Coaching format fixen
**Wat:** "max 4 regels" limiet in brain.md conflicteert met het vereiste formaat.
**Actie:** limiet versoepelen of coaching-blok compacter maken.
**Prioriteit:** laag.

### Kennis-laag schaalplafond
**Wat:** REDUCE herschrijft bij elke run de volledige `kennis_laag.md`. Schaalt niet voorbij ~70 entiteiten.
**Aanpak (later):** incrementeel mergen.
**Prioriteit:** laag — pas relevant bij ~70 entiteiten.

### Semantische zoeklaag (RAG/Embeddings)
**Wat:** Vervang keyword grep in `search_files()` door vector embeddings.
**Tooling:** `text-embedding-3-small` of `sentence-transformers`; vectorstore FAISS of Chroma op VM.
**Prioriteit:** laag — bronnenlaag heeft ~50 docs, keyword grep volstaat.

### Interactieve voorstel-refinement loop
**Wat:** Slack thread-reactie triggert `refine_proposal` skill met vorige output als context.
**Prioriteit:** medium.

### Website-analyse via Slack (DVV+AUB+SEO)
**Wat:** URL via Slack → Ainstein analyseert op DVV, AUB, SEO.
**Blokkade:** Playwright installeren op VM.
**Prioriteit:** medium.

---

## 📋 Backlog — Beslissingen (Thomas/Jörgen)

### Beslissing evidence-bar kennis-laag: wanneer automatiseren?
**Wat:** de trigger voor automatisering (`run_kennisextractie.py` via GitHub Actions) is gekoppeld aan een evidence-bar. Die heeft nog geen concrete deadline.
**Criteria uit roadmap:** ≥1 promotie van kennis naar bronnenlaag, óf een say-vs-sell-gat dat aantoonbaar tot een commerciële actie leidde.
**Actie Thomas/Jörgen:** geef de evidence-bar een concrete datum of concrete actie als trigger. Anders blijft dit eeuwig open.

### Kwaliteitscheck eerste productie-output meeting_reviewer
**Wat:** twee Drive-docs van 18 juni zijn nog niet handmatig beoordeeld: `260618_Gespreksnotitie _ Voorbereiding Hei-dag Waardestromen` en `260618_Debrief_SNI_NonLife_Leiderschapsprogramma`. Dit is de validatiestap vóór Ainstein breder ingezet wordt bij klantgesprekken.
**Actie Thomas:** open beide docs in Drive en beoordeel of de analyse correct en commercieel bruikbaar is.

### PPTX font-embedding visueel testen
**Wat:** Sen ExtraBold is via OOXML ingebakken in PPTX-output (`pptx_builder.py:_embed_sen_extrabold`). Nog niet visueel geverifieerd op een machine zonder Sen-installatie.
**Actie Thomas:** open een Ainstein-gegenereerd deck op Windows of Mac zonder Sen geïnstalleerd. Controleer of het font correct wordt weergegeven.
**Prioriteit:** doen vóór eerstvolgende klantverstrekking.


### TAVILY_API_KEY instellen op VM
**Wat:** Tavily is geconfigureerd als primaire websearch, maar `TAVILY_API_KEY` staat niet in `.env` op de VM (staat als commentaar in `.env.example`). Bot valt terug op DDGS.
**Actie Thomas:** sleutel aanmaken op tavily.com (gratis tier, geen CC nodig), instellen op VM: `echo "TAVILY_API_KEY=tvly-..." >> ~/Ainstein/.env` + bot herstarten via deploy.
**Prioriteit:** medium — Tavily geeft betere zoekresultaten dan DDGS.

### Say-vs-sell gaten adresseren
**Gevonden in kennis-laag run 21 juni 2026:**
- NN Group als ankerklant — 300+ deelnemers, multi-year, nauwelijks zichtbaar
- Wheel of Reasoning — ingezet in programma's, afwezig in publieke communicatie
- Agentic AI als leiderschapsthema — intern aanwezig (LEAD3), geen publieke positie
- "Making history by changing the future" — actief 2021–2023, afwezig 2026. Bewust of drift?
**Actie Thomas/Jörgen:** beslissen welke gaten worden geadresseerd en in welk medium.

### Prompt Coaching praktijktest
**Wat:** valideren of de Prompt Coaching sectie (brain.md) in de praktijk werkt.
**Actie Thomas/Jörgen:** testen met vage vragen in Slack, beoordelen of de coaching scherp en nuttig is.

### MCP-koppelingen — twee open beslissingen
**Calendar MCP:** ✅ token vernieuwd (19 mei 2026), "minkowski"-account correct op `thomas@minkowski.org` gezet. Minkowski-agenda zelf nog leeg — vul zakelijke afspraken in als je agenda-context in briefings wilt.
**Gmail MCP:** werkt, maar leest `tthiadens@gmail.com`. Beslissing: moet Ainstein de Minkowski-inbox (`thomas@minkowski.org`) kunnen lezen, en voor welk gebruik?
**Notion MCP:** verbonden, maar 0 pagina's gedeeld. Eenmalige handeling in Notion UI (Settings → Connections). Beslissing: welke pagina's wil je beschikbaar maken?

---

## 📋 Backlog — Architectuuropties (Major Decisions)

### OPTIE 2: Claude Projects Goed Inrichten — Tutorial & Checklist
**Status:** Ready to launch  
**Priority:** HOOG  
**Horizon:** NU (deze week starten)  
**Owner:** Thomas + Jörgen (samen valideren)  
**Relates to:** Track 2 (AI Toolbox), samen-werken in projecten  

**Context:** Claude Projects als alternatief voor Slack Bot workflow. Jij + Jörgen in dezelfde plek aan voorstel werken, Claude geeft feedback. Niet Ainstein-bot, maar Claude met goede instructies + Project Memory + Drive-access.

**Wat:**
8-stap tutorial:
1. Project aanmaken (`[JJMMDD] [Klant] — [Soort werk]`)
2. Google Drive connector instellen
3. Project Memory vullen (klant + Minkowski context)
4. Custom Instructions (jouw feedback-rol)
5. Start werk (voorstel concept + feedback-loop)
6. File-linking (@positioning.md, etc)
7. Terugkoppeling naar Root 2 (01_Proposals, 07_Feedback, 08_Outcomes)
8. Herhalen voor volgende voorstel (duplicate project)

**Waarom NU:**
- 80% van Optie 3 (MCP) met 20% van de work
- Geen extra infrastructuur nodig
- Validatie dat Jörgen + TT samen kunnen werken
- Template voor elke toekomstige voorstel

**Deliverables:**
- Tutorial document (7 stappen + troubleshooting)
- Checklist (ben je klaar?)
- Custom Instructions template (kopieer-plakken)
- Project Memory template (klant + Minkowski context)

**Success metrics:**
- Jörgen + TT kunnen zonder context-switching samen itereren
- Voorstel-kwaliteit verbetert (sneller feedback)
- Geen copypaste-werk meer (Drive-connected)
- Team adopteert dit als standaard voor voorstel-schrijven

---

## Tutorial: Claude Projects Goed Inrichten

*Gebasseerd op learnings uit sessie "Collaborative interface for program design" (22 juni 2026) en live proof-of-concept in Jörgens project "Minkowski& AInstein".*

### Kernbevindingen (waarom dit werkt)

1. **Drive connector werkt in shared projects** — niet read-only, Claude kan schrijven naar Drive (mits code execution + file creation aanstaat, standaard op Team-plan)
2. **Instructions zijn het knelpunt** — niet de connectors. Goed geformuleerde instructions bepalen of Claude als sparring partner werkt of als note-taker
3. **Files-sectie is kritiek** — leeg = geen kennis. De kennisbank (4 bestanden) bepaalt de kwaliteit van het advies
4. **Context blijft in Projects** — Slack trunceert lange teksten en programmaoutlines; Projects houdt alles bij

### 8 Stappen: Project Inrichten

#### Stap 1: Project aanmaken
```
Naam: [JJMMDD] [Klant] — [Soort werk]
  Voorbeeld: 260625 NN Group — LEAD 3 Program Design
  
Zichtbaarheid: Shared (minimum: jij + voornaamste sparringpartner)
Connectors: Google Drive (verplicht), Slack (optioneel), Web search (handig)
```

**Waarom deze naam?** Datum bovenaan = makkelijk sorteren. Klant + werk = context onmiddellijk duidelijk.

---

#### Stap 2: Google Drive connector instellen

1. Klik **"Add connector"** → **Google Drive**
2. Selecteer je **Minkowski Shared Drive** (`0AFvBEDYKrnHbUk9PVA`)
3. Test: vraag Claude "list the folders in the root"
4. Verifieer dat hij `01_Proposals`, `02_Tools`, etc. ziet

**Troubleshooting:** 
- Fout "ineligible to be used in generative AI"? → Dit is de **persoonlijke Drive-connector**, niet de Shared Drive. Verwijder en zet juiste Drive erin.
- Connector niet verschijnen? → Refresh de pagina.

---

#### Stap 3: Project Memory vullen (klant + Minkowski context)

Dit is waar je één keer context inzet zodat elke vraag daarna contextueel is.

**Plak dit als starting point, pas aan per klant:**

```
## Klant
- **Naam:** [klant]
- **Context:** [wie zijn ze, waar worstelen ze mee]
- **Vorige Minkowski-werk:** [wat hebben we eerder gedaan]
- **Stakeholders:** [wie participeren, wie beslist]
- **Budget/timing:** [wanneer, welke schaal]

## Minkowski Context
Minkowski is een agency for applied futures. We helpen organisaties future-ready worden via:
- Futures thinking (challenge assumptions, see what's coming)
- Leadership development (individual, team, org-wide)
- Experiential learning (programs, not workshops)

Our value = strong thinking + well-designed programs + credible experts + sharp proposals + commercial translation.

## Deze sessie
Doel: [voorstel bouwen / program ontwerpen / opportunity analyseren]
Outputformat: [beknopt voorstel / gedetailleerde outline / 3 opties met trade-offs]
Volgende stap: [review + feedback / presentatie aan klant / expert matching]
```

**Waarom dit werkt:** Claude begrijpt direct wat de klant nodig heeft en hoe Minkowski waarde levert.

---

#### Stap 4: Custom Instructions (de sparring partner)

Plak dit als **Project Instructions**. Dit is het hart — dit bepaalt of Claude challenger is of yes-man:

```
You are Ainstein — Minkowski's commercial intelligence and thinking partner.

Not a generic AI assistant. A challenger, strategist, and colleague embedded in Minkowski's work.

**What Minkowski does**
Minkowski is an agency for applied futures. It helps organisations become future-ready through futures thinking, leadership development, and experiential learning. Minkowski's value sits in the combination: strong thinking + well-designed programs + credible experts + sharp proposals + commercial translation.

**Your role**
- Challenge assumptions — including ones no one asked you to challenge
- Add what wasn't thought of but should have been
- Propose directions the team hasn't considered
- Reuse Minkowski's existing knowledge before generating from scratch
- Be commercially sharp, not academically interesting

You are the best thinking colleague — not the one who takes notes, but the one who asks "what if we did this differently?" and means it.

**When someone brings you a task**
- Commercial opportunity or lead → analyse: fit, gaps, risks, next steps
- Proposal to build or improve → retrieve past work, apply DVV-check
- Expert selection → match to real need, not familiar names
- Program design → ground in Minkowski methodology, challenge the logic
- Text or positioning → check against Minkowski language, not generic agency language

**Operating rules**
1. Never invent numbers. Prices, day rates, budgets — if not in the source material, say so explicitly.
2. Distinguish what is found from what is inferred. Label assumptions as assumptions.
3. Challenge vague asks. Don't reward fuzzy framing with polished-sounding output.
4. Protect quality over speed. If the source is thin or silent, say so and ask.
5. Reuse before creating. Adapt proven material where possible.
6. Label ownership. Never imply [Client] or [Minkowski] owns a program element without a source.
7. Proactive, not reactive. End every substantive answer with a concrete proposed next step.

**The DVV-check** (apply before any proposal or client-facing text)
- **D — Duidelijk (Clear):** Short sentences, no jargon, understandable outside Minkowski?
- **V — Volledig (Complete):** Does it answer what, who, how long, what it costs, what it delivers?
- **V — Verleidelijk (Compelling):** More "you" than "we"? Concrete outcomes, not abstract promises?

**Tone**
Sharp. Grounded. Commercially aware. Direct but not cold. Never generic, never inflated.
Write like someone who understands both how to win work and how to protect the Minkowski offer.

**What good looks like**
Uses Minkowski source material. Challenges what wasn't questioned. Adds what wasn't thought of. Makes the next step clearer. Sounds recognisably Minkowski.

**What bad looks like**
Sounds generic. Ignores sources. Invents certainty. Repeats clichés. Just confirms what was already said.
```

---

#### Stap 5: Files uploaden (kennisbank vullen)

Dit zijn de vier bestanden die het meest waarde toevoegen. Export ze uit de Shared Drive en upload als `.txt` of `.md` in de Files-sectie:

| Bestand | Locatie in Drive | Wat het bevat |
|---|---|---|
| `kennis_laag.md` | `06_Marketing/_kennis/` | Getrianguleerde Minkowski-kennis (verkondigd + verkoopbaar) |
| `verbal_identity.md` | `06_Marketing/` | Verboden woorden, vocabulary pairs, Minkowski voice-and-tone |
| `02_Tools_Agent_README.md` | `02_Tools/` | SCOPE, Futures Cone, 7 Practices, Jörgens eigen uitleg van methodologie |
| `gaps.md` | `07_Feedback/` | Bekende gaten in Ainsteins kennis — feedback loop |

**Optioneel maar waardevol:**
- 2-3 gewonnen voorstellen als referentie (uit `01_Proposals/`)
- `minkowski_decision_layer.json` (expert-index, uit `04_Experts/`)

**Upload als `.txt`** — Projects handelt markdown soms raar. Plain text is betrouwbaarder.

---

#### Stap 6: File-linking in gesprekken

Met Drive connector actief kan je in een vraag rechtstreeks linken:

```
Kijk naar deze voorstel: [Drive link naar document]
Hoe zouden we dit voor klant X kunnen aanpassen?

Of: pas deze positioning aan op basis van verbal_identity.md
```

Claude leest het document live. Dit werkt als directe bronverwijzing.

---

#### Stap 7: Terugkoppeling naar Root 2

Na elk substantieel piece of work:
- **Voorstel klaar?** → Upload naar `01_Proposals/[klant]/` in Drive
- **Feedback van klant?** → Log in `07_Feedback/gaps.md` (wat miste Ainstein / wat zei Claude wat niet werkte)
- **Gewonnen/verloren?** → Noteer in `08_Outcomes/` (leerbare patronen voor toekomst)

Dit voedt de kennislaag — elke project maakt Ainstein scherper.

---

#### Stap 8: Volgende voorstel = duplicate project

Klaar met deze klant of move naar volgende fase? Duplicate het project:
- Rechts-klik project → **Duplicate**
- Update Project Memory (nieuwe klant of fase)
- Keep instructions (deze blij hetzelfde)
- Keep Files (kennisbank is stable)
- Update Custom Instructions als nodig (bijvoorbeeld: nu program design in plaats van proposal)

---

### Verificatie-Checklist

Voor je zegt "klaar", test dit:

- [ ] **Vage vraag:** Stel Ainstein "Wat zouden we kunnen doen voor een retailer?" → moet terugvragen of context eisen, niet direct antwoord geven
- [ ] **Getal buiten bronnen:** Vraag naar day rate voor een expert die niet in 04_Experts staat → moet expliciet zeggen "niet in de kennisbank"
- [ ] **Zwak concept:** Geef een vaag voorstel → moet DVV-check toepassen, zwaktes benoemen
- [ ] **Drive link:** Plak een Drive-link met een document → Claude leest het correct
- [ ] **Ownership labeling:** Vraag wie eigenaar is van een program-onderdeel → labelt `[Klant]`, `[Minkowski]`, of `[Nog bepalen]`

---

### Troubleshooting

**Drive connector ziet files niet**
→ Refresh pagina. Check dat je Shared Drive geselecteerd hebt (niet persoonlijke Drive).

**Claude geeft getallen die niet in bronnen staan**
→ Instructions niet goed ingesteld. Controleer dat "Never invent numbers" er in staat.

**File-linking werkt niet**
→ Zorg dat je Drive connector nog steeds actief is. Soms werkt het beter met folder-links dan bestand-links.

**Instructions voelen niet als "Ainstein"**
→ Pas aan: vul Custom Instructions volledig in. Generiek template werkt niet — je moet je eigen tone/rol definiëren.

**Project Memory is te lang**
→ Oké — Claude handelt langere memory goed. Maar zorg dat het gestructureerd is (kopjes, bullets, duidelijke scheidingen).

---

### Referentie: Waar vind je de bestanden?

Alle bestanden staan in je Shared Drive `Minkowski AInstein`:
- Drive ID: `0AFvBEDYKrnHbUk9PVA`
- Standaard pad in Drive connector: deze wordt automatisch herkend

Eerste keer? Gooi ze in je Google Drive (persoonlijk) als backup, maar werk altijd via de Shared Drive connector (teamwork!).

**First test:** Volgende Nike/[klant]-voorstel

---

### OPTIE 3: Ainstein als MCP Server — Root 2 Knowledge Expose
**Status:** Planning  
**Priority:** MID  
**Horizon:** Later (na Optie 2 validation)  
**Owner:** Thomas (co-design met Claude Code)  
**Relates to:** Track 2 (AI Toolbox), Claude Projects integration  

**Context:** Root 2 (01–08 folders) exposeren als MCP Server zodat Claude Projects Ainstein-kennis direct kunnen benutten — eleganter dan huidiga Drive-API aanroepen.

**Wat:** 
- Python/Node MCP server met tools: `read_file`, `search_files`, `list_folder`, `search_content`, `get_file_metadata`
- Service account + Drive API authentication
- Caching + reliability (moet altijd werken)
- Claude Project connecteert erop → voelt aan als "Ainstein in project"

**Waarom later:**
- Optie 2 (Claude Project goed inrichten) is 80% impact met 20% work
- Optie 3 is eleganter maar niet critical de komende 2 maanden
- Eerst valideren dat Optie 2 werkt (Jörgen + TT samen in Projects)

**Decision gate:** End Juli 2026 (na zomer + Optie 2 validation)

**Voorbereiding:**
- [ ] Optie 2 gelanceerd + gevalideerd
- [ ] Root 2 structuur stabiel (governance af)
- [ ] Service account + Drive API live (al in Slack Bot)

**Deliverables (als we het build):**
- MCP server code (Python or Node)
- Auth setup (service account, token refresh)
- Testing + reliability
- Deployment config
- Documentation
- Monitoring

**Success metrics:**
- <500ms response time read_file
- <1s for search_content
- Zero unhandled exceptions production
- Team adopts as standard way to access Root 2 from Projects

---

## 📋 Backlog — Toekomst (nog niet te bouwen)

### Episodisch geheugen
**Wat:** na elke proposalsessie gestructureerde lessen opslaan in `08_Episodes` in Drive.
**Prioriteit:** medium — pas nuttig als ≥10 sessies gedocumenteerd zijn.

### prioritise_pipeline skill
**Wat:** leads prioriteren op basis van ICP-fit, timing, openstaande kansen.
**Prioriteit:** na Klant-Agent en design_program.

### Ainstein voert acties zelf uit na Slack-bevestiging
**Wat:** "doe het maar" in Slack triggert vervolgactie direct.
**Prioriteit:** complex — aparte sessie, pas als Klant-Agent stabiel draait.

### Lead-radar (proactief)
**Wat:** Ainstein scant wekelijks signalen (LinkedIn, nieuws) en meldt prospects.
**Prioriteit:** laag — pas bouwen als ICP en GTM-laag bewezen werken in de praktijk.

### Pipeline tracker
**Wat:** lichtgewicht commerciële pipeline — welke leads, welke fase, volgende actie.
**Prioriteit:** laag.

### Competitive intelligence skill
**Wat:** vergelijking Minkowski vs. concurrent op verzoek.
**Prioriteit:** laag.

---

## ✅ Gedaan (archief)

| Item | Commit/PR | Datum |
|---|---|---|
| 7 skills verbeterd: DVV-toets in build_proposal, map_objections herschreven, create_content/adapt_messaging/sharpen_positioning/match_experts/debrief_to_messaging versterkt + detect-skill false positive "content" gefixed | `6fff459` | 22 juni 2026 |
| dev-branch cleanup (10 commits, deels verouderd) gepland | backlog | 22 juni 2026 |
| `.env` opruimen — dubbele AINSTEIN_STATUS_CHANNEL regels gefixed | handmatig op VM | 22 juni 2026 |
| Drie audit-gaps gesloten: run_backup.sh in git, RATE_LIMIT_MAX in .env.example, pip-audit (0 kwetsbaarheden) | `cfba2fb` | 22 juni 2026 |
| Architectuurbeslissing: single-agent blijft; Klant-Agent = tweede API-call, geen apart systeem | sessie 22 juni 2026 | — |
| `AINSTEIN_BACKUP_DEST_ID` ingesteld op VM | handmatig | 28 mei 2026 |
| K3 Dubbele deploy — geen deploy-cron op VM, alleen backup-crons; GitHub Actions enige deploypad | `crontab -l` check | 28 mei 2026 |
| Approval gate — bewust verwijderd (`6305c4b`), solo-project | commit `6305c4b` | 28 mei 2026 |
| Ainstein Slack bot (SocketMode) | live | — |
| 08_Outcomes setup (win/loss geheugen) | `8425f0b` | — |
| Wekelijkse Drive backup | `39cd42d` | — |
| Rate limiting (max 10 calls/uur per user) | `3c8f264` | — |
| Block Kit formatting voor Slack | `b689c18` | — |
| Feedback loop (gaps.md in prompts, auto-review #ainstein-status) | live | — |
| Plan A: Prompt Coaching | `05ed433` | mei 2026 |
| Web search via Tavily + DDGS fallback | `7154a08` | mei 2026 |
| Dynamic Slack user lookup | `cf18ff4` | mei 2026 |
| Vision/image support (JPEG/PNG) | `110b681` | mei 2026 |
| Kennis-laag bewijs-fase (scrapers + extractie) | `1a3820a` e.a. | mei/juni 2026 |
| Kennis-laag REDUCE fix (timeout 900s, max_tokens 32k, resumability) | `1a3820a` | 21 juni 2026 |
| Plan B: Jamie webhook pipeline | PR #27 | mei 2026 |
| Ainstein karakter-update (uitdager/denkpartner) | PR #28 | 16 juni 2026 |
| Jamie meeting test (Hei-dag Waardestromen) — DM + taakreview werkt | live | 21 juni 2026 |
| Backlog centraliseren | zie commit | 21 juni 2026 |
| Kennis-laag contextprobleem opgelost | `1a3820a` | 21 juni 2026 |
| Kennis-laag volledige run — alle 10 bronnen verwerkt, `kennis_laag.md` bijgewerkt | live op VM | 21 juni 2026 |
| Slack-scraper geautomatiseerd — werkdagen 01:00 via VM cron (deploy.yml), scrapet laatste 2 dagen | `5d93daf` + deploy | 22 juni 2026 |
| K1-pad: kennis_laag.md injectie via agent.py (Pad A) — `drive_read_kennis_laag()` + `load_kennis_context()` in tools.py, injectie in agent.py na gaps.md | `4af0453` | 22 juni 2026 |
| `_slack_notify` certifi-fix — SSL-context met certifi-CA toegevoegd in `run_kennisextractie.py` | `b4118c9` | 21 juni 2026 |
| DM-status ruis bij interne meetings gefixed — `if not sent_dms and not failed_dms: return` check aanwezig in `transcript_processor.py:337` | in code | 22 juni 2026 |
| `send_slack_message` tool toegevoegd | `fdda619` | 22 juni 2026 |
| DM-status verificatie in #ainstein-status thread | `e232ef9` | 22 juni 2026 |
| Dashboard: ping-knop in alert bar → POST `/webhooks/ping` → #ainstein-status | `69e99e2` | 22 juni 2026 |
| Dashboard: SocketMode heartbeat — slack_app.py schrijft elke 30 min naar `logs/socketmode_heartbeat.txt`, dashboard toont badge | `69e99e2` | 22 juni 2026 |
| Dashboard: Futures Ready kaart — mindset/skillset/toolset gereedheid op basis van kennislaag + skills_30d + docs gelezen | `dc32484` | 22 juni 2026 |
| Deploy: `workflow_dispatch` trigger in deploy.yml — handmatige herstart via GitHub Actions UI (geen SSH nodig) | `69e99e2` | 22 juni 2026 |
| Slack: `/health` command geregistreerd in Slack app (`/status` was bezet door andere app) | handmatig | 22 juni 2026 |
| Dashboard: live Slack auth.test check (niet alleen env var aanwezigheid) | `20e0e2f` | 22 juni 2026 |
| DM naar Jörgen: dashboard URL + uitleg van alle kaarten | via Slack MCP | 22 juni 2026 |
| Dashboard: live health checks per dienst (groen/rood), GCP CPU/geheugen/kosten, klanten-pilot, token-logging exacte kosten | `b2bee86`–`2d9fd6d` | 22 juni 2026 |
| Management dashboard (`dashboard/generate.py`) — 4 KPI-kaarten, Minkowski-stijl, nginx + cron via deploy.yml | `5c33ae9` | 22 juni 2026 |
| CLAUDE.md volledig bijgewerkt (Current State, skills, sessie-rituelen) | `1e3cd2e` | 22 juni 2026 |
| Kennis-laag Jörgen/Charlotte validatie verstuurd naar #about-ainstein — 7 items ter bevestiging; dagelijkse monitoring via scheduled task 09:05 | Slack MCP | 22 juni 2026 |
| Kennis-laag validatie: Charlotte bevestigt alle 7 items (100% klopt); 7 gecureerde .md documenten aangemaakt in Drive (4x 02_Tools, 3x 06_Marketing) | Ainstein scheduled task | 24 juni 2026 |
| Kennis-laag pipeline-visualisatie (bronnen → MAP/REDUCE → injectie → gebruik) — SVG diagram | Claude Code | 22 juni 2026 |
| Roadmap audit: 12 nieuwe items toegevoegd vanuit sessie-reviews, 2 achterhaalde items verwijderd | sessie | 22 juni 2026 |
| Kennis-laag map-reduce refactor | `c9bbf42` | 21 juni 2026 |
| Kennis-laag tijd-dimensie (Trend, gedateerde facetten, Historie) | `1a3820a` | 21 juni 2026 |
| Website-scraper minkowski.org + futuresready.com + team/experts | `dcbd99b` | 21 juni 2026 |
| LinkedIn/Medium/Substack scrapers + bronnen.json (10 bronnen) | `b716a23` | 21 juni 2026 |
