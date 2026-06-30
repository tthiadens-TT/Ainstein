# Ainstein Backlog

*Bijgewerkt: 30 juni 2026 (sessie: Drive-herstructurering type→entiteit afgerond; alle code bijgewerkt; commit 015516a)*
*Beheerd door: Claude Code + Thomas — elke sessie bijwerken*

Dit is de centrale backlog voor Ainstein. Alle openstaande items — acties, bugs, ideeën, todo's — staan hier met context en prioriteit. Niet in CLAUDE.md (dat is sessiememorie), niet in losse documenten.

**Gebruik:**
- Begin elke sessie: dit bestand lezen (Session Start Protocol stap 3)
- Sluit elke sessie af: dit bestand bijwerken
- Afgerond item: verplaatsen naar ✅ Gedaan, niet verwijderen

---

## 🔴 Actief probleem

### Drive-connector blokkade: MCP connector kan Shared Drive niet lezen
**Symptoom:** `mcp__4e943b1e` connector retourneert nul bestanden bij parentId-query op Shared Drive, zelfs met geldige bestanden erin. `04_Experts` map is NIET leeg.
**Root cause:** Google Workspace AI-beleid markeert de Shared Drive "Minkowski AInstein" als "ineligible for generative AI contexts." Actief seit 21 mei 2026 (migratie van persoonlijke Drive naar Shared Drive).
**Impact voor Claude Code sessies:** Ainstein kan in sessies de bronnenlaag niet direct lezen via de MCP connector. Productie-bot op VM werkt wel (service account).

**Fix — actie Thomas (Workspace-admin, ~10 min):**
1. Ga naar `admin.google.com` (thomas@minkowski.org of Jörgen als admin)
2. Apps > Google Workspace > Drive & Docs
3. Zoek naar AI/Gemini-beleidsinstelling die Shared Drive-inhoud als "niet-bruikbaar voor AI" markeert
4. Schakel restrictie uit voor "Minkowski AInstein" Shared Drive, of voor de hele org
5. Test daarna: open Claude Code, vraag `parentId = '1ml1O6XS766fbS3bfejqlh14qNvyI-nbB'` via MCP connector — moeten nu bestanden terugkomen

**Workaround tot fix:** SSH naar VM + service account voor Shared Drive-toegang.
**Verwachte moeite:** 10 min voor Thomas. 0 code nodig.

---

## 🟡 Volgende stap (prioriteit 1)

*(leeg — zie backlog hieronder)*

---

## 📋 Backlog — Technisch (bouwwerk)

### Retrieval-first in build_proposal
**Wat:** `skills/build_proposal.md` aanpassen: stap 1 wordt deterministisch ophalen uit `Clients/<naam>/Outcomes/` voor vergelijkbare cases. Genereer alleen wat niet op te halen is.
**Geblokkeerd door:** folder-migratie + Outcomes vullen.

### Origin-gewicht in merge-skill (synaptic stratification licht)
**Wat:** zekerheid niet meer als `count(distinct origins)` maar als `sum(weights)`. Klant-stem weegt zwaarder dan intern-Slack.
**Wanneer:** na Double Helix stabiel in productie.

### kennis-bestanden verplaatsen naar 05_Ainstein Knowledge Base (latere fase)
**Wat:** `kennis_laag.md`, `entiteiten.md`, `minkowski_voice.md` verplaatsen van `04_Marketing/_kennis/` naar `05_Ainstein Knowledge Base/`. De kennis is ook marketingkennis — urgentie is laag, maar hoort architectureel bij Ainstein, niet bij Marketing.
**Actie:** Drive + code (bronnen.json, tools.py kennis-pad, agent.py injectie-pad).
**Prioriteit:** laag.

### Markdown cache opnieuw genereren na Drive-rename (Thomas, VM)
**Wat:** Na de Drive-herstructurering zijn de top-level mapnamen veranderd. De bestaande Markdown-cache heeft padverwijzingen met de oude namen. Cache opnieuw opbouwen zodat alles klopt.
**Actie Thomas:** SSH naar VM, dan: `cd ~/Ainstein && python3 scripts/convert_to_markdown.py`
**Prioriteit:** medium — cache werkt nog, maar klopt niet meer met nieuwe structuur.

### 00_Roadmap Drive-docs verhuizen (Thomas, ~5 min)
**Wat:** Twee docs in `00_Roadmap` Drive-folder ("OPTIE 2 — Claude Projects Tutorial", "OPTIE 3 — MCP Server Architecture") verplaatsen naar `05_Ainstein Knowledge Base/Roadmap/`. Daarna lege `00_Roadmap` verwijderen.
**Actie Thomas:** review eerst of de docs nog actueel zijn, daarna verplaatsen in Drive.
**Prioriteit:** laag.

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

### [idee] Markdown cache: naam-collision voorkomen
**Wat:** Twee bestanden in verschillende submappen met dezelfde naam overschrijven elkaars `.md` in de root van de source-folder. Nu geen probleem — `01_Proposals` heeft unieke namen — maar groeit met de tijd.
**Aanpak:** relatief pad meenemen in de cache-bestandsnaam: `NN_Group__Proposal.md` in plaats van `Proposal.md`. Vereist dat `_drive_list_files_in_folder` het parent-pad retourneert, of een aparte BFS die het pad bijhoudt.
**Trigger:** zodra er voor het eerst een naamconflict optreedt (script logt dan een overschrijving).

### [idee] AI-samenvatting in Markdown cache-header
**Wat:** De cache-header bevat nu alleen de sectielijst uit `##` headers. Een beknopte AI-samenvatting per document (3–5 zinnen, commercieel relevant) maakt de cache veel meer bruikbaar voor Ainstein: minder tokens nodig om te begrijpen wat er in staat.
**Aanpak:** optionele stap in `convert_folder` — na conversie één extra API-call voor samenvatting, opgeslagen in de header. Opt-in via `--summarize` vlag.
**Gegated op:** bewijs dat de cache daadwerkelijk raadpleegbaar is en dat de header gelezen wordt.

### [idee] MCP converters vs. eigen pipeline combineren
**Wat:** Thomas vroeg of de eigen Markdown-conversie beter is dan MCP-converters, en of ze te combineren zijn.
**Antwoord:** eigen pipeline is beter voor batch-caching (offline, token-efficiënt, geen per-call overhead). MCP handig voor ad-hoc conversie van losse bestanden. Combinatie: MCP als fallback voor bestandstypen die de eigen pipeline niet ondersteunt (bijv. exotische formats).
**Nu niet nodig:** eigen pipeline dekt alle relevante types (.docx, .pdf, .pptx, .gdoc, .eml).

### [idee] VM tier upgraden voor grotere PPTX-bestanden
**Wat:** e2-micro (1GB RAM) dwingt een 20MB PPTX-limiet. Bestanden zoals `Activate-NNLEAD4_vJ.pptx` (184MB) worden overgeslagen.
**Aanpak:** upgrade naar e2-small (2GB) of e2-medium (4GB) in GCP. Kost ~$10–20/maand extra.
**Trigger:** zodra er meerdere grote PPTX-bestanden zijn die commercieel relevant zijn en nu worden overgeslagen.

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

### GitHub MCP authenticatie — credentials verlopen
**Symptoom:** elke dagelijkse review meldt `Authentication Failed: Bad credentials` bij `mcp__github__list_pull_requests` en `mcp__github__list_issues`. Geldt al weken (eerst gevlagd: 2026-06-15).
**Impact:** dagelijkse reviews kunnen GitHub-status (open PRs, issues) niet verifiëren. Geen productie-impact — code deployt gewoon via GitHub Actions.
**Actie Thomas:** GitHub MCP-connector opnieuw authenticeren in Claude Code:
1. Open Claude Code desktop app
2. Ga naar MCP-instellingen (Settings > Connectors of vergelijkbaar)
3. Verwijder de GitHub-connector en voeg hem opnieuw toe met een geldig GitHub-token
4. Of: genereer een nieuw Personal Access Token op github.com (repo + read:org scopes) en update de connector-configuratie
**Prioriteit:** medium — geen productie-impact, maar verblindend voor dagelijkse code-reviews.

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

*Doel: Elk project werkt met dezelfde bronnenlaag als Ainstein, zodat project-output direct Ainstein verrijkt. Synergie in plaats van isolatie.*

*Gebasseerd op learnings uit sessie "Collaborative interface for program design" (22 juni 2026) en live proof-of-concept in Jörgens project "Minkowski& AInstein".*

---

## De Synergie-Cirkel (waarom dit anders is dan een gewoon project)

```
Project Start
    ↓
[Files: haalt kennis UIT Ainstein's bronnenlaag]
    ↓
Je werkt (voorstel / programma-ontwerp / analyse)
    ↓
Je ontdekt iets NEU, iets wat MIST, iets wat WERKT
    ↓
[Terugkoppeling: voegt toe AAN Ainstein's bronnenlaag]
    ↓
Ainstein via Slack is nu SCHERPER (volgende keer)
    ↓
Volgende project haalt al die NIEUWE kennis eruit
    ↓
→ Cirkel versterkt zich
```

**Het verschil:** 
- **Normaal Claude Project:** Je gebruikt Claude, Claude geeft antwoorden, klaar.
- **Dit:** Je en Claude werken allebei met dezelfde kennisbasis. Het project is geen geïsoleerde taak, het is een **feedback-loop met Ainstein.**

Dit is hoe je schaal bouwt zonder afhankelijk te zijn van één persoon. Elk team-lid die een project opstart, verrijkt Ainstein.

---

### Kernbevindingen (waarom dit werkt)

1. **Drive connector werkt in shared projects** — niet read-only, Claude kan schrijven naar Drive (mits code execution + file creation aanstaat, standaard op Team-plan)
2. **Instructions zijn het knelpunt** — niet de connectors. Goed geformuleerde instructions bepalen of Claude als sparring partner werkt of als note-taker
3. **Files-sectie is kritiek** — leeg = geen kennis. De kennisbank (4 bestanden) bepaalt de kwaliteit van het advies
4. **Context blijft in Projects** — Slack trunceert lange teksten en programmaoutlines; Projects houdt alles bij

### 8 Stappen: Project Inrichten voor Synergie

#### Stap 1: Project aanmaken
```
Naam: [JJMMDD] [Klant] — [Soort werk]
  Voorbeeld: 260625 NN Group — LEAD 3 Program Design
  
Zichtbaarheid: Shared (minimum: jij + voornaamste sparringpartner)
Connectors: Google Drive (VERPLICHT — je link naar Ainstein's bronnenlaag)
```

**Waarom deze naam?** Datum bovenaan = makkelijk sorteren. Klant + werk = context onmiddellijk duidelijk.

**Synergie-check:** Drive connector moet werken. Dit is je link naar dezelfde Files waar Ainstein uit leest.

---

#### Stap 2: Instructions instellen (wie ben je in dit project)

Plak dit als **Project Instructions**. Dit bepaalt je rol in het project:

```
You are Ainstein — Minkowski's commercial intelligence and thinking partner.

Not a generic AI assistant. A challenger, strategist, and colleague.

**Your role in this project**
- Challenge assumptions — including ones no one asked you to challenge
- Add what wasn't thought of but should have been
- Propose directions not yet considered
- Reuse Minkowski's existing knowledge from the Files before generating from scratch
- Be commercially sharp, not academically interesting

**When working on this project**
- Commercial opportunity → analyse: fit, gaps, risks, next steps
- Proposal to build → retrieve past work from Files, apply DVV-check
- Expert selection → match to real need, not familiar names (use 04_Experts data)
- Program design → ground in Minkowski methodology, challenge the logic
- Text or positioning → check against verbal_identity.md in Files

**Operating rules**
1. Never invent numbers. If pricing/budgets not in Files, say so explicitly.
2. Distinguish what is found from inferred. Label assumptions.
3. Challenge vague asks. Don't reward fuzzy framing.
4. Protect quality over speed. If source is thin, ask.
5. Reuse before creating. Adapt proven material from Files.
6. Label ownership: [Client], [Minkowski], or [To Be Determined] — never assume.
7. Proactive: end every answer with a concrete next step.

**The DVV-check** (apply before proposals)
- **D — Duidelijk:** Understandable outside Minkowski?
- **V — Volledig:** What, who, how long, cost, delivers what?
- **V — Verleidelijk:** Outcomes, not abstract promises?

**Tone**
Sharp. Grounded. Commercially aware. Direct but not cold.
```

**Synergie-check:** Dit zijn dezelfde Instructions die Ainstein in Slack gebruikt. Je werkt met dezelfde mindset.

---

#### Stap 3: Files vullen (je bronnenlaag-toegang)

Dit zijn de bestanden die je uit Drive pullt. Dit is hoe je dezelfde kennis gebruikt als Ainstein:

| Bestand | Waar in Drive | Wat het bevat |
|---|---|---|
| `kennis_laag.md` | `06_Marketing/_kennis/` | Getrianguleerde Minkowski-kennis (verkondigd + verkoopbaar) |
| `verbal_identity.md` | `06_Marketing/` | Toon, verboden woorden, vocabulary pairs |
| `02_Tools_Agent_README.md` | `02_Tools/` | SCOPE, Futures Cone, 7 Practices, methodologie |
| `gaps.md` | `07_Feedback/` | Bekende gaten in Ainstein's kennis — je leert wat nog ontbreekt |

**Optioneel maar waardevol:**
- 2-3 gewonnen voorstellen (uit `01_Proposals/`) als referentie
- `minkowski_decision_layer.json` (expert-index, uit `04_Experts/`)

**Upload als `.txt` of `.md`** — Projects handelt formatting soms raar.

**Synergie-check:** Dit zijn dezelfde Files die Ainstein gebruikt. Je en Claude hebben dezelfde bron. Alles wat je ontdekt dat hier MIST → voeg je later terug toe.

---

#### Stap 4: Google Drive connector testen

1. Klik **"Add connector"** → **Google Drive**
2. Selecteer je **Minkowski Shared Drive** (`0AFvBEDYKrnHbUk9PVA`)
3. Test: vraag Claude "list the folders in the root"
4. Verifieer dat hij `01_Proposals`, `02_Tools`, etc. ziet
5. Test: plak een Drive-link naar een document → Claude leest het live

**Troubleshooting:** 
- Fout "ineligible to be used in generative AI"? → Dit is de **persoonlijke Drive-connector**, niet de Shared Drive. Verwijder en zet juiste Drive erin.
- Connector niet verschijnen? → Refresh de pagina.

**Synergie-check:** Drive connector = je live-link naar bronnenlaag. Dit is hoe je in het project dezelfde bestanden raadpleegt als Ainstein in Slack.

---

#### Stap 5: Project Memory vullen (klant + purpose)

Dit is context die je EENMAAL zet zodat elke vraag contextueel is.

**Plak dit als starting point, pas aan per klant:**

```
## Klant
- **Naam:** [klant]
- **Context:** [wie zijn ze, waar worstelen ze mee]
- **Vorige Minkowski-werk:** [wat hebben we eerder gedaan]
- **Stakeholders:** [wie participeren, wie beslist]
- **Budget/timing:** [wanneer, welke schaal]
- **Wat mist in kennisbank:** [industry-specifieke kennis, expert-banden, eerdere werk — dit zul je later toevoegen]

## Minkowski Context
Minkowski is een agency for applied futures. We helpen organisaties future-ready worden via:
- Futures thinking (challenge assumptions, see what's coming)
- Leadership development (individual, team, org-wide)
- Experiential learning (programs, not workshops)

Our value = strong thinking + well-designed programs + credible experts + sharp proposals + commercial translation.

## Dit project
- **Doel:** [voorstel bouwen / program ontwerpen / opportunity analyseren]
- **Output:** [beknopt voorstel / gedetailleerde outline / 3 opties]
- **Volgende stap:** [review + feedback / klantpresentatie / expert matching]
- **Feedback-plan:** [wie geeft feedback, wanneer]
```

**Synergie-check:** Wat mist? Noteer dit — dat voeg je AAN Ainstein toe als het project klaar is.

---

#### Stap 6: Work in progress (het voorstel/ontwerp/analyse)

Je werkt nu in het project. Claude is jouw sparring partner. Twee regels:

1. **Alles wat je doet, staat in het project** — niet in Slack, niet in je notitie-app. Alles hier, zodat het traceerbaar is voor terugkoppeling.
2. **Als je iets mist in de Files**, noteer het direct in Project Memory onder "Nieuw ontdekt / nog toe te voegen" — je voegt het straks toe.

**Synergie-moment:** Terwijl jij werkt, verrijkt jij impliciet al Ainstein — door aan te geven wat mist.

---

#### Stap 7: Live file-linking

Met Drive connector actief kan je in een vraag rechtstreeks linken:

```
Kijk naar deze voorstel: [Drive link]
Hoe passen we dit aan voor klant X?

Of: controleer dit concept tegen verbal_identity.md
```

Claude leest het live. Dit is directe synchronisatie met Ainstein's bronnen.

**Synergie-check:** Je en Claude hebben dezelfde bron. Geen "jij zegt X, ik zeg Y" — jullie spreken dezelfde taal.

---

#### Stap 8: Terugkoppeling naar Ainstein (dit is de cirkel)

**Dit is NIET optioneel.** Dit is hoe Ainstein groeit. Na elk project:

**A) Voorstel/output klaar?**
→ Upload naar `01_Proposals/[klant]/` in Drive
- Dit is de "success case" — laat Ainstein zien wat werkt

**B) Wat miste je in de Files?**
→ Log ALLES in `07_Feedback/gaps.md`
- Formulering: "In project [X] zocht ik naar [Y], was niet in kennislaag"
- Dit soort gaten helpen Ainstein groeien

**C) Feedback van klant?**
→ Log in `07_Feedback/gaps.md` 
- Wat zei de klant dat Claude niet voorzag?
- Wat vroeg de klant om dat Ainstein niet voorstelde?

**D) Gewonnen of verloren?**
→ Noteer in `08_Outcomes/`
- Wat werkte? Wat niet? Waarom?
- Leerbare patronen voor volgende project

**E) Nieuwe kennis ontdekt?**
→ Als je iets belangrijks over de klant/industrie/approach ontdekt, noteer het
- Later wordt dit promoveerd naar kennislaag

**Synergie-check:** Elke project voert terug. Ainstein en volgende project wordt scherper.

---

#### Stap 9: Volgende project = duplicate + update

Klaar? Duplicate het project:
- Rechts-klik → **Duplicate**
- Update Project Memory (nieuwe klant/fase)
- Keep Instructions (dezelfde mindset)
- Keep Files (kennisbank, nu verrijkt via vorige project)
- Add: feedback-loop van vorige project als context

Dus: volgende project haalt al NIEUWE kennis eruit die vorige project toevoegde. **De cirkel.**

---

### Verificatie: Werkt de Synergie?

Voor je zegt "project klaar", test dit:

- [ ] **Drive connector:** Plak een Drive-link in het project → Claude leest het live ✓
- [ ] **Files actueel:** Zijn de 4 bestanden in Files geupload en leesbaar? ✓
- [ ] **Instructions working:** Stel een vage vraag ("Wat zouden we voor deze klant kunnen doen?") → moet terugvragen, uitdagen, niet direct antwoord geven ✓
- [ ] **Ownership labeling:** Vraag wie eigenaar is van een program-onderdeel → labelt `[Klant]`, `[Minkowski]`, of `[Nog bepalen]` ✓
- [ ] **Numbers:** Vraag naar iets dat NIET in Files staat (bijv. day rate van expert die niet in 04_Experts) → zegt expliciet "niet in bronnen" ✓
- [ ] **Terugkoppeling voorbereid:** Heb je alles genoteerd in Project Memory wat je AAN Ainstein wilt toevoegen? ✓

---

### Terugkoppeling in Praktijk

**Checklist voor na het project:**

- [ ] **Output klaar** → Upload naar `01_Proposals/[klant]/`
- [ ] **Gaten gelogd** → `07_Feedback/gaps.md`: "In project [klant] zocht ik naar X, niet in kennisbank"
- [ ] **Klantfeedback gelogd** → `07_Feedback/gaps.md`: "Klant vroeg om Y, Claude stelde het niet voor"
- [ ] **Win/loss gelogd** → `08_Outcomes/`: Wat werkten, wat niet, waarom
- [ ] **Nieuwe kennis** → Notaties voor toekomstige promotie naar kennislaag

---

### Troubleshooting

**Drive connector ziet Files niet**
→ Refresh pagina. Controleer: Shared Drive (niet persoonlijke Drive) geselecteerd.

**Claude geeft getallen/prijzen die niet in Files staan**
→ Instructions niet correct ingesteld. Check dat "Never invent numbers" erin staat.

**File-linking werkt niet (Claude kan link niet lezen)**
→ Zorg dat Drive connector actief is. Test met folder-link in plaats van bestand-link.

**Instructions voelen niet als Ainstein (generiek antwoord in plaats van challenger)**
→ Pas Instructions aan. Generiek template werkt niet — je moet het contextualiseren naar jouw project.

**Project Memory is chaotisch / te lang**
→ Oké om lang te zijn. Zorg voor structuur: kopjes, bullets, duidelijke scheidingen. Claude handelt dit goed.

**Terugkoppeling voelt als "extra werk"**
→ Dit is niet extra. Dit IS het project — zonder terugkoppeling is er geen synergie, dus geen schaal. Noteer gaten terwijl je werkt, niet achteraf.

---

### Referentie: Bestanden & Locaties

Alle bestanden in Shared Drive `Minkowski AInstein`:
- **Drive ID:** `0AFvBEDYKrnHbUk9PVA`
- **Bronnenlaag folders:**
  - `01_Proposals/` — gewonnen voorstellen (referentie)
  - `02_Tools/` — methodologie docs
  - `04_Experts/` — expert-index
  - `06_Marketing/_kennis/` — kennis_laag.md
  - `06_Marketing/` — verbal_identity.md
  - `07_Feedback/` — gaps.md (gaten-log)
  - `08_Outcomes/` — win/loss records

Eerste project? Zet alles in je persoonlijke Drive als backup, maar **werk altijd via Shared Drive connector** (teamwork!).

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
| Double Helix epistemologisch labelen: skills bijgewerkt + pipeline herrun geslaagd (30 juni, stop_reason=end_turn, 111k chars, Type-labels live in Drive). REDUCE via directe API-call; Promotiebesluiten-fallback; graceful truncation. | `008937a` e.v. | 29-30 juni 2026 |
| `kansen.md` aangemaakt in `06_Marketing/` (Drive ID `1lcSCyA3QBMwLQTCFCKhIWC4MqHMGDDQN`): 4 say-vs-sell kansen uit kennis-laag — NN Group zichtbaarheid, Wheel of Reasoning extern, Agentic AI positie, making-history-tagline drift. | Drive API | 30 juni 2026 |
| Entiteiten-register aangemaakt: `06_Marketing/_kennis/entiteiten.md` in Drive (ID: `1ZTRPn_hm_9T0OfUMCArYsUPU85zG_b3N`), 21 experts (Jörgen van der Sloot gecorrigeerd), 8 klanten, merge-skill bijgewerkt | `008937a` | 29 juni 2026 |
| `scripts/update_drive_file.py` gebouwd: update bestaand Drive-bestand via service account, lost MCP create-duplicaat probleem op | `8845648` | 29 juni 2026 |
| CLAUDE.md bijgewerkt met Double Helix, entiteiten-register, update_drive_file.py | `d43f689` | 29 juni 2026 |
| Drive-herstructurering: type-gebaseerd (01_Proposals t/m 08_Outcomes) → entiteit-gebaseerd (01_Clients, 02_Frameworks & Tools, 03_Experts, 04_Marketing, 05_Ainstein Knowledge Base). Drive handmatig door Thomas, code-aanpassingen 25 bestanden. | `015516a` | 30 juni 2026 |
| CLAUDE.md volledig bijgewerkt (Current State, skills, sessie-rituelen) | `1e3cd2e` | 22 juni 2026 |
| Kennis-laag Jörgen/Charlotte validatie verstuurd naar #about-ainstein — 7 items ter bevestiging; dagelijkse monitoring via scheduled task 09:05 | Slack MCP | 22 juni 2026 |
| Kennis-laag validatie: Charlotte bevestigt alle 7 items (100% klopt); 7 gecureerde .md documenten aangemaakt in Drive (4x 02_Tools, 3x 06_Marketing) | Ainstein scheduled task | 24 juni 2026 |
| Kennis-laag pipeline-visualisatie (bronnen → MAP/REDUCE → injectie → gebruik) — SVG diagram | Claude Code | 22 juni 2026 |
| Roadmap audit: 12 nieuwe items toegevoegd vanuit sessie-reviews, 2 achterhaalde items verwijderd | sessie | 22 juni 2026 |
| Markdown conversie cache volledig: `scripts/convert_to_markdown.py` converteert .docx/.pdf/.pptx/.gdoc → .md naast het origineel in Drive (geen aparte _cached/ map). Dynamische folder-discovery (hardcoded SOURCE_FOLDERS vervangen door Drive-root lookup). Deduplicatie op file ID. Apostrof-escaping in Drive API queries. PPTX OOM-limiet (>20MB skip). DOCX heading styles + PPTX slide-titels als Markdown headers. GitHub Actions red-X opgelost (datetime timezone bug dashboard). 40 bestanden gecachet, 0 fouten. | `e989b2b` | 29 juni 2026 |
| Schrijfstijl levend organisme: `minkowski_voice.md` verrijkt uit bronmateriaal (LinkedIn/Substack/website), VM-cron (ma 04:00), Drive-backup + restore na deploy, 9 skills krijgen voice als prefix | `5be9c11` + `ff4760d` | 26 juni 2026 |
| Kennis-laag map-reduce refactor | `c9bbf42` | 21 juni 2026 |
| Kennis-laag tijd-dimensie (Trend, gedateerde facetten, Historie) | `1a3820a` | 21 juni 2026 |
| Website-scraper minkowski.org + futuresready.com + team/experts | `dcbd99b` | 21 juni 2026 |
| LinkedIn/Medium/Substack scrapers + bronnen.json (10 bronnen) | `b716a23` | 21 juni 2026 |
