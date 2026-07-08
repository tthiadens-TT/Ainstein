# Ainstein Backlog

*Bijgewerkt: 8 juli 2026, avond (twee bugs uit de daily-review gefixed: em dash-lek in de Slack-klantregel + ``` -codeblok-lek in elke Meetingnote, beide mechanisch gedicht. Roadmap opgeschoond: stale regels gecorrigeerd, 3 zoekgeraakte repo-audit-bevindingen als losse items teruggezet. Eerder vandaag: kennislaag bron-governance uitgezocht — LinkedIn-Jörgen-bron bleek incompleet, compleetheids-grendel + consolidatiescript gebouwd. Zie sectie "Kennislaag bron-governance".)*
*Beheerd door: Claude Code + Thomas — elke sessie bijwerken*

Dit is de centrale backlog voor Ainstein. Alle openstaande items — acties, bugs, ideeën, todo's — staan hier met context en prioriteit. Niet in CLAUDE.md (dat is sessiememorie), niet in losse documenten.

**Gebruik:**
- Begin elke sessie: dit bestand lezen (Session Start Protocol stap 3)
- Sluit elke sessie af: dit bestand bijwerken
- Afgerond item: verplaatsen naar ✅ Gedaan, niet verwijderen

---

## 🟠 Bekende, blijvende beperking (niet "actief probleem" — zie geschiedenis-waarschuwing)

### Drive MCP-connector: child-listing op specifieke Shared Drive-submappen werkt niet
**Dit item is op 22 juni 2026 ten onrechte als "opgelost" afgesloten (commit `a18fe6e`) en op 29 juni ten onrechte toegeschreven aan een Google Workspace AI-beleidsinstelling. Beide bleken bij grondig, multi-agent onderzoek op 1 juli 2026 onjuist. Sluit dit item niet af zonder een nieuwe, onafhankelijk geverifieerde test — zie `memory/connector_access_paths.md` voor de volledige geschiedenis van foutieve afsluitingen.**

**Symptoom (bevestigd, herhaald getest 1 juli 2026):**
- `search_files` met `parentId` op een Shared Drive-map geeft structureel geen bestanden terug — stil, geen foutmelding, soms een `nextPageToken` zonder inhoud.
- **Mechanisme (geverifieerd 2 juli):** de connector toont wél submappen, maar verbergt bestanden. Een map mét submappen lijkt daardoor te "werken" (`04_Marketing` toonde submappen maar verborg 15 losse bestanden), een map met alléén bestanden lijkt "leeg" (`03_Experts`: 54 bestanden → lege respons). Alle mappen hebben het probleem; de eerdere conclusie "niet universeel, 04_Marketing werkt wél" was een illusie.
- `list_recent_files` toont op geen getest niveau losse Shared Drive-bestanden, alleen mappen.
- Los probleem, andere tool: `mcp__gdrive__search` is volledig disfunctioneel (7/7 pogingen, ook triviale input, geven `MCP error -32603: invalid_request`).

**Root cause:** NIET bevestigd. Geen Google Workspace-instelling (die hypothese is expliciet verworpen, niet ondersteund door onderzoek). Extern GitHub-issue `anthropics/claude-code#53442` beschrijft een gelijkend patroon, staat nog open (laatste activiteit 26 juni 2026), geen reactie van een Anthropic-medewerker, geen fix aangekondigd.

**Wat wél werkt, getest en kruisgeverifieerd:**
1. **Buiten een Claude Code sessie (productiepad, altijd betrouwbaar):** VM + service account. Nooit geraakt door dit probleem.
2. **Binnen een sessie, als VM-route niet beschikbaar is:** breed zoeken (`title`/`fullText`, zonder `parentId`), daarna **verplicht** elk resultaat met `get_file_metadata` terugcontroleren tegen de verwachte parent. Zonder die stap onveilig: leverde bij test 24 overtuigende spookresultaten op uit een oude, gearchiveerde map (`AInstein_OUD`, ander account). Volledig doorpagineren — een lege `files`-array met `nextPageToken` betekent niet "klaar."

**Niet doen:** dit item afsluiten als "opgelost" zonder verse, onafhankelijke test. Niet opnieuw een Google Workspace-instelling voorstellen als oorzaak.

**Uitbreiding 2 juli 2026 (belangrijk):** de connector geeft óók valse negatieven bij ZOEKEN (`fullText`/`title`), niet alleen bij mapopvraging. Bewezen: een serviceaccount-scan toonde dat de hele bronnenlaag compleet in de Shared Drive staat, terwijl connector-zoekopdrachten kernbestanden "niet vonden". **Conclusie: geen enkele connector-uitkomst over de Shared Drive is betrouwbaar, positief noch negatief.** Enige betrouwbare lezer = serviceaccount op de VM. Gereedschap hiervoor: `scripts/verify_shared_drive.py` (read-only, draait op de VM). Gebruik dit voor grondwaarheid bij elke vraag "staat X wel/niet in de Drive".

**Adopteer de Anthropic-fix zodra die er is (afspraak Thomas):** monitor GitHub-issue `#53442` en de Claude Code changelog. Zodra het issue sluit of de changelog een Shared Drive / `supportsAllDrives`-fix noemt: hertest de connector met dezelfde parentId- en fullText-checks tegen `03_Experts` (`1ml1O6XS766fbS3bfejqlh14qNvyI-nbB`). Werkt het dan betrouwbaar, dan mag de connector weer een dragend pad worden (en herleeft de connector-route van Optie 2). Tot die tijd: serviceaccount is leidend.

---

## 📋 Backlog — Drive opruiming (na serviceaccount-scan 2 juli 2026)

Gevonden via de betrouwbare serviceaccount-scan, dus echte bevindingen (geen connector-artefact). Niet urgent.
**→ Valt onder het koepelitem "Bronlaag-ordening ontwerpen" (sectie Kennislaag bron-governance). Niet los oppakken; plannen als onderdeel van dat ordeningstraject.**

### Dubbele/overbodige bestanden opruimen (rest — laag)
Grotendeels gedaan (3 juli, zie ✅ Gedaan): stray `06_Marketing`, dubbele lege `_kennis`, 2x `.DS_Store`, en de bewezen-identieke `260601_Opzet NN LEAD3`-dubbel opgeruimd. Legacy `slack_C09CEQ29AU8` Google Docs: 0 gevonden, al eerder weg. Wat nog rest:
- **BESLISSING NODIG:** `00_Werkdocumenten` heeft `LEAD3_NN_Group_Opzet_updated.pptx` **4x met drie verschillende groottes** (62467/62801/63074 b). Dit zijn géén schone duplicaten maar mogelijk verschillende versies van een klant-deck. Niet blind verwijderd. Thomas: welke is de canonieke versie? Dan ruim ik de rest op.
- ~~`01_Clients/.../Test/Meetingnotes`: 4x identieke `Meetingnote 2026-06-26 — Test kennismaking`~~ **Onderzocht en vrijgegeven (7 juli, review-Cleared):** testartefacten uit het verifiëren van de brand-formatting-fix, staan in een `Test`-map (niet een echte klantmap), geen dataverlies-risico. Kunnen blijven staan of handmatig weg door Thomas; geen actie vereist.
**Prioriteit:** laag, blokkeert niets.

### Drie repo-audit-bevindingen die "apart genoteerd" claimden maar nergens landden
**Gevonden door daily-code-review 8 juli 2026:** de archief-regel (`plans/ainstein-roadmap.md`, ✅ Gedaan-tabel, repo-audit-entry 8 juli) noemt drie bevindingen als "apart genoteerd — zie backlog", maar geen van de drie kwam ooit in een actieve backlog-sectie terecht. Ze bestonden alleen in die ene archiefzin, die niet wordt teruggelezen voor open items. Hierbij alsnog toegevoegd:
- ~~**LinkedIn Jörgen-bronvarianten**~~ — inmiddels **niet meer een los item**: volledig uitgezocht en aangepakt op 8 juli, zie sectie "Kennislaag bron-governance" hierboven (dat is nu de canonieke plek voor dit onderwerp, met veel meer diepgang dan deze oorspronkelijke bevinding).
- **NN Group lege submappen** — de serviceaccount-scan (2 juli) vond dat NN Group's per-klant submapstructuur grotendeels leeg steigerwerk is (vergelijkbaar met het `01_Clients`-patroon dat Thomas op 8 juli signaleerde, zie "Bronlaag-ordening ontwerpen"). Nog niet inhoudelijk beoordeeld of dit steigerwerk gevuld moet worden of weg mag. **Actie:** meenemen in het bronlaag-ordeningstraject, geen apart traject nodig.
- **Onboarding-doc-naamgeving** — `00_Werkdocumenten` heeft zowel `Ainstein Onboarding Guide` (Google Doc) als `Ainstein_ONBOARDING.md` (plain-text). Onbekend of dit twee actieve documenten zijn of een verweesde dubbeling (zelfde patroon als het LinkedIn-lek: een cache/export naast een origineel). **Actie:** inhoud vergelijken (zoals bij de LinkedIn-consolidatie) vóór opruimen — niet blind op bestandsgrootte/naam kiezen.
**Prioriteit:** laag voor de eerste twee (meelopen in groter traject), laag-en-klein voor de derde (kan los, snel).

---

## 🟠 Kennislaag bron-governance (uitgezocht 8 juli 2026)

**Kern:** de kennislaag-pijplijn leest per bron een Drive-*map* (`bronnen.json`), niet een versie. Er was geen compleetheids-check. Gevolg: voor LinkedIn-Jörgen las de pijplijn een handmatige scrape van **42 posts** (`linkedin_jorgen_archief.md`, 21 juni), terwijl een completere scrape van **120 posts** (27 mei) verweesd als Google Doc in de root van `_bronmateriaal/` lag, ongelezen. Ainstein kreeg dus een derde van Jörgens LinkedIn-stem. Grondwaarheid geverifieerd via serviceaccount op de VM (niet de connector).

**Wat is gedaan (code, live via deploy):**
- `scrape_linkedin.py` **compleetheids-grendel**: stabiele bestandsnaam (`linkedin_<origin>.md`, geen datum meer) + weigert een bestaande rijkere bron te overschrijven met minder posts + convergeert naar één bestand. Voorkomt de oorzaak: de VM-scraper haalt maar ~6 seed-posts en kon zo een handmatige rijke bron verpesten. Docstring recht. 82/82 tests groen.
- `scripts/consolidate_linkedin_source.py` gebouwd (eenmalig, dry-run default). Overlap-grendel via tekst-shingles: ruimt een wees alleen op als zijn inhoud ≥92% in het canonieke bestand zit. Dry-run op de VM geverifieerd.

**Wat Thomas moet doen (VM-schrijfactie, kan niet via read-only SSH):**
```
# op de VM, na deploy:
cd ~/Ainstein && python3 scripts/consolidate_linkedin_source.py            # herlees dry-run
cd ~/Ainstein && python3 scripts/consolidate_linkedin_source.py --apply    # uitvoeren
```
Wat --apply doet (lossless): schrijft de 120-post VOLLEDIG als `linkedin_jorgen.md` in de pijplijn-map; laat `linkedin_jorgen_archief.md` (42, 80% gedekt → ~20% unieke, waarschijnlijk nieuwere posts) STAAN en vlagt hem; ruimt de 97%-gedekte Substack-wees op; laat de Minkowski-varianten (beide 24 posts) staan. De distilleer-stap leest de hele map, dus Ainstein krijgt meteen de **unie** (120 + unieke 42). **Verwijder daarna `consolidate_linkedin_source.py`** (eenmalig hulpmiddel).

**Vervolgstappen (na apply):**
1. **Double Helix opnieuw draaien** — pas dan profiteert `kennis_laag.md` van 120 i.p.v. 42 posts. `python3 scripts/run_kennisextractie.py` op de VM (map-reduce, ~64k tokens).
2. **Echte ontdubbeling tot één bestand per bron** (Thomas' doelarchitectuur): een geverifieerde merge-pass die VOLLEDIG + de unieke archief-posts (+ de twee Minkowski-varianten) samenvoegt tot één canonieke `.md` per bron, zodat er niet twee overlappende bestanden in de map blijven. Dit is een aparte, te verifiëren stap (LLM-merge met coverage-check op ≈100% dekking van beide bronnen), geen blinde concat.
3. **Overige scrapers gelijktrekken** — `substack`/`medium` gebruiken jaar-in-de-naam (meerdere bestanden per bron), `slack` heeft nog een mix van legacy Google Docs + `.md`. Beoordelen of één-bestand-per-bron + `.md`-only overal moet gelden.

### Bronlaag-ordening ontwerpen (`01_Clients` als startpunt) — nieuw 8 juli 2026
**Aanleiding:** Thomas toonde `01_Clients` in Drive: tientallen losse `.md`-bestanden (voorstellen, needs-analyses, transcripten, forwards, cache) plat door elkaar, met een paar echte klantmappen ertussen (NN Group, Jetske Ultee, Holland & Barrett). Dit is geen architectuur. Ainstein-ruis, mensonvindbaar, cache niet te onderscheiden van echte docs.
**Wat:** een ordenend principe voor de hele bronlaag, afgedwongen i.p.v. gehoopt. Richting (te beoordelen, zie concept-plan): per entiteit een submap met vaste interne indeling; cache náást origineel, nooit in de root; één canoniek document per ding (finale/geaccordeerde versie leidend); naamgeving die structuur draagt. De top-laag is sinds 30 juni entiteit-gebaseerd; die logica moet nú ook *binnen* de mappen.
**Dit is het KOEPELITEM voor alle Drive-ordening.** De volgende losse items zijn facetten hiervan en worden onder deze ene aanpak uitgevoerd (niet meer los oppakken):
- 🔴 URGENT cache-rommel (157 bestanden in folder-roots, waarvan 41 in `01_Clients`) — "cache náást origineel, niet in root" is precies deel van het ordenend principe. NB: het opruimen zelf houdt zijn eigen verificatie-waarschuwing (niet afsluiten zonder `verify_cache_structure.py` → SCHOON).
- 📋 Drive opruiming: 4x `LEAD3_NN_Group_Opzet_updated.pptx` in `00_Werkdocumenten` + 4x identieke Test-Meetingnotes — "één canoniek document per ding" lost dit soort versie-duplicaten structureel op.
- "kennis-bestanden verplaatsen naar `05_Ainstein Knowledge Base`" (Technisch-backlog) — een structurele verplaatsing die in het ordeningsontwerp thuishoort.
**Prioriteit:** medium-hoog — raakt zowel mensbruikbaarheid als de kwaliteit van wat Ainstein leest. Eerst ontwerp + akkoord Thomas, dan uitvoeren (grotendeels Drive-werk + evt. code voor cache-plaatsing). De losse cleanup-items hierboven blijven staan waar ze staan (met hun eigen instructies/guards), maar worden gepland als onderdeel van dit ene ordeningstraject.
**Volledig concept:** `plans/kennislaag-bron-verrijking-concept.md`.

### Bevestigingsroutine `ainstein-kennis-bevestiging` — herontwerp nodig
**Beoordeeld 8 juli 2026 (op Thomas' verzoek).** De scheduled task (dagelijks 09:05) bewaakt één vaste Slack-thread uit 22 juni met dezelfde **7 kennisitems die Charlotte op 24 juni al 100% bevestigde**. De thread is dood, de lijst bevroren; de dagelijkse run doet niets zinnigs meer. Ontwerpfout: gekoppeld aan één momentopname i.p.v. een levende stroom kandidaat-kennis.
**Aanbeveling:** (1) nu deactiveren (ronde afgerond — de routine zegt in zijn eigen Stap 0 dat dat mag); (2) herontwerpen tot een **levende bevestigingsloop**: leest na elke kennis-extractie de nieuwe `promotie-kandidaat`-items uit `kennis_laag.md`, legt alleen de níéuwe voor aan Jörgen/Charlotte, verwerkt reacties, legt promotie vast (mensenwerk). **Blokkade voor heractivering:** de routine doet autonome SSH-writes + `git push`, wat botst met de read-only-VM-regel in CLAUDE.md — dit raakt de open Loop-Charter/guardrails-beslissing. Eerst die guardrails, dan bouwen.
**Actie Thomas:** akkoord om te deactiveren + akkoord op de herontwerp-richting (of alternatief).

---

## 🔴 URGENT — Cache-rommel opruimen (prioriteit 1, blokkeert afsluiting)

**Dit is de enige open actie op het cache-dossier. Zie `### Markdown cache: platte plaatsing — code gefixed, data-cleanup nog open` verderop in dit bestand voor de volledige fix-geschiedenis; die sectie verwijst hierheen en claimt zelf geen "opgelost" meer.**

**Probleem:** 157 cache-bestanden staan nog in folder-roots. Automatische API-deletie faalde (Google Drive file-ID sync-lag: `cleanup_direct.py` en `cleanup_batch_delete.py` meldden beide "0 deleted, 157 failed").

**Opnieuw geverifieerd 6 juli 2026 via `scripts/verify_cache_structure.py` op de VM (grondwaarheid, niet de connector) — exact hetzelfde aantal als bij ontdekking op 4 juli, dus nog niets van opgeruimd:**
- `04_Marketing`: 86
- `01_Clients`: 41
- `03_Experts`: 25
- `02_Frameworks & Tools`: 3
- `05_Ainstein Knowledge Base`: 2
- **Totaal: 157**

**Nevenschade ontdekt 6 juli:** 41 van de 157 rommel-bestanden staan in `01_Clients` (o.a. kale tekstversies van NN LEAD3/LEAD4-voorstellen en debriefs). Wie handmatig door klantmappen browst kan de cache-versie per ongeluk aanzien voor een los, nieuw document.

**Actie:** handmatige Drive UI opruiming (de enige route die nog niet geprobeerd is):
1. Open Google Drive (Minkowski AInstein Shared Drive)
2. Per root-folder: selecteer alle .md-bestanden met `**Gecachet:**` header
3. Delete

**Bestandenlijst voor opruiming:**
- `04_Marketing/slack_C0*.md` (50+ bestanden)
- `04_Marketing/README_*.md`, `LinkedIn Posts — *.md`, `Substack Artikelen — *.md`, `Minkowski_*.md`, `MK-new-brandbook.md`
- `03_Experts/*_Profile.md` (21 bestanden) + `README_04_Experts.md`, decision/selection logic docs
- `02_Frameworks & Tools/README_02_Tools.md`, `Ppt Template`, `Minkowski Tools & Models`
- `01_Clients/Meetingnote_*.md`, `*Fwd_*.md`, `LEAD 3 — *.md`, `LEAD 4 — *.md`, `NN Group_*.md`, `NN Retail_*.md`, `*Slides*.md`, projectplan docs

**Criteria voor verwijdering:** bestand eindigt op `.md` EN bevat `**Gecachet:**` in eerste 400 chars.

**Status:** Thomas handelt uit zodra hij in Drive kan. Nog steeds 157/157 aanwezig — geen voortgang sinds 4 juli.
**Prioriteit:** blokkeert afsluiting van cache-fix — pas dan gesloten. Sluit dit item niet af op basis van een script-run; automatische deletie is al twee keer bewezen kapot (stale file-ID's). Alleen handmatige Drive UI-actie of een herbevestigde `verify_cache_structure.py` → `✅ SCHOON` telt als bewijs.

---

## 🟡 Volgende stap (prioriteit 2)

### Jamie-fix live valideren bij eerstvolgende echte meeting
**Waarom:** de klant/traject-fix (`762447b`, meeting_reviewer Stap 0) is een gedragsverandering in Ainstein's redeneren, geen deterministische bug-fix. Unit-tests slagen, maar dat Ainstein nooit meer het verkeerde NN-sub-dossier (LEAD3 vs. Inkomen Collectief) koppelt is nog niet bewezen op een echte meeting.
**Actie (bij eerstvolgende Jamie-meeting):** controleer in `#ainstein-status` of (a) de 'Klant/traject:'-regel klopt met wat het gesprek echt was, en (b) de DM er opgeruimd uitziet (Block Kit, titel bovenaan). Klopt het niet: log in gaps.md + heropenen.
**Prioriteit:** doen zodra er een meeting via Jamie binnenkomt. Dit is de enige echte proef op de Jørgen-fix.

### [optioneel, laag] Bestanden ook rename-proof maken
**Nu:** mappen zijn rename-proof via `drive_structure.py`, maar bestanden worden nog op naam opgezocht (`kennis_laag.md`, `verbal_identity.md`, `gaps.md`, `entiteiten.md`, expertprofielen).
**Advies (Claude):** bewust NIET nu doen. Bestanden worden zelden hernoemd (de 30-juni-pijn was mappen), er is geen spookbestand-datalek-equivalent (een hernoemd bestand → nette faal + log, geen stille data-split), en de lookups gebruiken al deels substring-zoek. Kosten-baten valt nu negatief uit.
**Trigger om wél op te pakken:** zodra een bestand daadwerkelijk hernoemd moet worden of een tweede vindplaats krijgt. Dan: file-resolutie via een `drive_structure`-achtige helper (op stabiele sleutel i.p.v. exacte naam).

---

## 📋 Backlog — Technisch (bouwwerk)

### Proposal Engine 2.0 bouwen (Fable-brief, idee 1)
**Wat:** vijf-staps voorstel-pipeline (intake → parallelle retrieval naar evidence packs → draft → onafhankelijke adversarial review → ship via `create_gdoc`). Volledige uitvoerbare spec: `plans/fable-brief-proposal-engine.md` (geschreven door Fable, 6 juli, vóór sluiting van het Fable-window). Uitvoering kan op Opus/Sonnet.
**Volgorde Jörgen:** na validatie van de whats-your-future tool (idee 4 → 1 → 5).

### Kennislaag als querybaar toolregister (Fable-brief, idee 5)
**Wat:** `data/toolregister.yaml` (40+ tools uit 02_Tools README, metadata-schema bestaat al) + deterministische `query_tools()` in `tools.py`. Géén REST-API. Herbruikbaar door Minkowski Studio. Spec: `plans/fable-brief-kennislaag-api.md`. Let op stap K4: menselijke verificatie van het register is verplicht, niet overslaan.

### whats-your-future v2-opties (na praktijkvalidatie)
**Wat:** pas oppakken nadat de tool in een echt discovery-gesprek is gebruikt: (a) publiceren op de VM achter nginx voor een deelbare URL (dan gelden de 4 deployment-vragen), (b) NL-versie, (c) officieel logo-bestand uit `04_Marketing/Logo/` embedden i.p.v. tekst-wordmark, (d) kwartaal-refresh van `data.js` door Ainstein (ritueel staat in de tool-README).

### Retrieval-first in build_proposal
**Wat:** `skills/build_proposal.md` aanpassen: stap 1 wordt eerst de finale geaccordeerde voorstellen ophalen als referentie, dan pas genereren. Genereer alleen wat niet op te halen is.
**Bron (geverifieerd 7 juli 2026):** losse `FINAL`/`Proposal`/`Voorstel`-bestanden in de root van `01_Clients` (bv. `Proposal NN Lead4 by Minkowski FINAL.md`, `Voorstel NN Retail Schade en Zorg FINAL.md`). NIET een Outcomes- of Proposals-map: die bestaan niet (leeg steigerwerk). Het finale voorstel = 95-100% van de waarheid; ontwerpfase-delta is meestal kleine nuance.
**Niet meer geblokkeerd:** de oude blokkade "folder-migratie + Outcomes vullen" vervalt. De bron bestaat al, alleen ongeordend (herkenning op naampatroon). Wél nuttig: idee 5 (toolregister) maakt dit ophalen betrouwbaar i.p.v. gok via full-text search.

### Origin-gewicht in merge-skill (synaptic stratification licht)
**Wat:** zekerheid niet meer als `count(distinct origins)` maar als `sum(weights)`. Klant-stem weegt zwaarder dan intern-Slack.
**Wanneer:** na Double Helix stabiel in productie.

### kennis-bestanden verplaatsen naar 05_Ainstein Knowledge Base (latere fase)
**Wat:** `kennis_laag.md`, `entiteiten.md`, `minkowski_voice.md` verplaatsen van `04_Marketing/_kennis/` naar `05_Ainstein Knowledge Base/`. De kennis is ook marketingkennis — urgentie is laag, maar hoort architectureel bij Ainstein, niet bij Marketing.
**Actie:** Drive + code (bronnen.json, tools.py kennis-pad, agent.py injectie-pad).
**Prioriteit:** laag. **→ Meenemen in het koepelitem "Bronlaag-ordening ontwerpen".**

### Stale mapnaam-verwijzingen in deze roadmap zelf opschonen
**Wat:** de 30-juni-hernoeming (`06_Marketing` naar `04_Marketing`, `04_Experts` naar `03_Experts`) is in code en Drive volledig afgehandeld, maar de roadmap-tekst zelf verwijst nog naar de oude namen in de Claude Projects-tutorial (de "Files vullen"-tabel, de connector-troubleshooting en de referentie-sectie onderaan). Geverifieerd 5 juli: meerdere `06_Marketing`- en `04_Experts`-vermeldingen in die secties.
**Waarom het telt:** die tutorial stuurt teamleden naar mappen die niet meer bestaan. Actueel misleidend, geen cosmetiek.
**Let op:** de historische entries in het ✅-archief die `06_Marketing`/`04_Experts` noemen NIET wijzigen; dat is correcte geschiedenis van wat toen gebeurde.
**Actie:** de niet-historische verwijzingen bijwerken naar de huidige namen, of de sinds 30 juni sowieso deels verouderde Claude Projects-tutorial in één keer herzien.
**Prioriteit:** laag, maar doen vóór de tutorial weer voor onboarding gebruikt wordt.

### Markdown cache: platte plaatsing — code gefixed, data-cleanup nog open

**Let op (correctie 6 juli 2026):** deze sectie heette eerder "VOLLEDIG OPGELOST". Dat klopte niet — alleen de root-cause in de code is gefixed. De 157 bestaande rommel-bestanden staan er nog steeds, ongewijzigd sinds ontdekking. **De enige actuele status van de data-cleanup staat in de `🔴 URGENT`-sectie bovenaan dit bestand — die is leidend, niet deze sectie.**

**Probleem (ontdekt 4 juli):** `convert_to_markdown.py` schreef alle cache-`.md` naar folder-root (`04_Marketing/`, `01_Clients/`, etc.), niet naast het origineel. Dit veroorzaakte 157+ cache-bestanden als chaos-dump in roots. Onleesbaar, niet schaalbaar.

**Root-cause (geverifieerd):** 
- Commit **eddd8f5** (29 juni) introduceerde **recursieve** file-listing
- Comment zei: "schrijf naast origineel"
- Code deed: `cache_folder_id = src_folder_id` (hardcoded root)
- Deze **design-fout** ging door review omdat het script niet was getest
- Commit **e989b2b** maakte het erger (verborg het achter dynamische discovery)
- Script draaide 3 juli → rommel zichtbaar

**Wat wél echt klaar is — de code-fix (live, voorkomt herhaling):**
1. **709b9d7** — Code-fix: `cache_folder_id = parent_ids[0]` per bestand. Nieuwe conversie-runs schrijven correct.
2. **fdff82a** — Python 3.9 type-hint compat (Optional, Tuple)
3. **a69546d** — `CACHE_DESIGN.md` (design vastgelegd, voorkoming ingebouwd)
4. **7a90988** — `verify_cache_structure.py` (detecteert rommel automatisch — dit is het script dat vandaag opnieuw 157 violations teruggaf)

**Wat NIET klaar is — de opruiming van de 157 bestaande bestanden:**
- **b620407** (`cleanup_stray_cache.py`), **4d4c286** (`cleanup_batch_delete.py`) en **46f675a** (`cleanup_direct.py`) zijn drie pogingen om de bestaande rommel automatisch te verwijderen. **Alle drie zijn mislukt** — Google Drive API geeft 404 op de file-ID's ondanks dat folder-listing ze toont (stale file-ID sync-lag, mogelijk gerelateerd aan connector-bug #53442). Resultaat: drie bijna-identieke scripts in `scripts/` die geen van alle werken. **Opgelost 8 juli 2026:** de twee overbodige (`cleanup_batch_delete.py`, `cleanup_direct.py`) zijn verwijderd, `cleanup_stray_cache.py` (met `--dry-run`) blijft over met een waarschuwing in de docstring — zie Gedaan-archief.
- Enige overgebleven route: handmatige Drive UI-opruiming door Thomas — zie 🔴 URGENT-sectie.

**Voorkoming toekomst:**
- Design is expliciet in `scripts/CACHE_DESIGN.md` — niemand schrijft stiekem naar roots
- Verificatie ingebouwd: `verify_cache_structure.py` wordt part of normal checks
- PR-review: design raadplegen vóór cache-wijzigingen

### 00_Roadmap Drive-docs verhuizen (Thomas, ~5 min)
**Wat:** Twee docs in `00_Roadmap` Drive-folder ("OPTIE 2 — Claude Projects Tutorial", "OPTIE 3 — MCP Server Architecture") verplaatsen naar `05_Ainstein Knowledge Base/Roadmap/`. Daarna lege `00_Roadmap` verwijderen.
**Actie Thomas:** review eerst of de docs nog actueel zijn, daarna verplaatsen in Drive.
**Prioriteit:** laag.

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

### Smart meeting routing verificeren in productie
**Wat:** `transcript_processor.py` detecteert meeting types (discovery/check_in/follow_up/internal) en routeert naar de juiste skill. Code bestaat, maar is nog niet geverifieerd met een echte Jörgen-Jamie meeting waarbij het type-detectie expliciet getest is.
**Actie:** na de eerste Jörgen-meeting via Jamie: check logs op `meeting_type` — klopt het gedetecteerde type?
**Prioriteit:** laag — wachten op volgende echte meeting.

### `pptx_builder.py` hardcoded relationship ID
**Wat:** `rid = "rIdSenEB"` (regel 123) is hardcoded. Bij een tweede font collideren relationship-IDs in `presentation.xml.rels`.
**Actie:** dynamisch genereren bij uitbreiding. Nu geen actie nodig.
**Prioriteit:** laag — pas relevant als tweede font wordt toegevoegd.

### Klantbronnen als kennisbron — websites, jaarverslagen, nieuws
**Wat:** publiek beschikbare informatie over (potentiële) klanten toevoegen als bron aan de kennis-laag. Per klant: website, jaarverslag, persberichten, LinkedIn. Geeft Ainstein context over de wereld van de klant — vóórdat een voorstel of meeting begint.
**Eerste kandidaat:** NN Group (ankerklant, 300+ deelnemers, multi-year). Thomas denkt dat er al een sessie/item over bestaat — nog te traceren.
**Aanpak:** `scrape_client.py` per klant, output naar `04_Marketing/_bronmateriaal/klanten/<klantnaam>/`. Zelfde plain-text .md bakje als andere bronnen. Origine: `klant-extern`.
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

### Loop Charter: bouwen of laten vallen? (verkend 30 juni, nooit geïmplementeerd)
**Wat:** de sessie "Loop Charter application" (30 juni) verkende een werkwijze uit een Notion-artikel: een Claude die zelfstandig doorloopt tot een klus af is (vindt werk, doet het stuk voor stuk, checkt met bewijs, onthoudt de staat in een `LOOP-STATE.md`, stopt als klaar). De sessie pivotte volledig naar de Drive-fix; de Loop Charter zelf is nooit gebouwd. Er zijn charter-kandidaten geschetst met labels [BOUWBAAR]/[STRATEGISCH], maar geen loop, geen state-bestand, geen schedule.
**Optie A (bouwen):** een afgebakende autonome loop voor Ainstein, bijvoorbeeld een terugkerende zelf-verbetertaak (kennislaag verrijken, gaps opvolgen) die doorloopt tot klaar. Vereist harde guardrails: read-only tenzij expliciet, geen productie-schrijfacties zonder verificatie, één-sessie-tegelijk (de parallel-drift van deze week laat zien waarom).
**Optie B (laten vallen):** de bestaande scheduled tasks (daily-code-review, kennis-bevestiging) dekken het meeste al af; een generieke autonome loop voegt risico toe zonder bewezen behoefte.
**Aanbeveling (Claude):** niet nu bouwen. Eerst de guardrails-vraag beantwoorden en één concrete, waardevolle loop-usecase kiezen. Zonder duidelijke usecase is dit een oplossing die een probleem zoekt.
**Beslissing Thomas:** A (welke usecase?) of B (idee sluiten).
**Aanvulling (sessie 5 juli, Loop Charter opnieuw bekeken als Claude Code-expert):**
- **Drie loop-mechanismen, kies bewust:** in-sessie `/loop` (herhaalt in het huidige gesprek), geplande cloud-agent via `/schedule` (nieuwe sessie op tijdstip, met Slack-notificatie), of headless `claude -p "$(cat charter.md)"` + cron op de VM. Optie A vraagt dus geen nieuwe infrastructuur; `/schedule` of een cron-regel volstaat.
- **Tegenspraak bij de voorbeeld-usecase:** "kennislaag verrijken" (genoemd bij Optie A) is juist een zwakke eerste loop. `run_kennisextractie.py` verwerkt elke bron al deterministisch; er is geen beslisser per stap, dus het is cron-werk (goedkoper zónder loop) en het is duur (map-reduce, circa 64k tokens). Het artikel waarschuwt zelf: kies je eerste loop niet op het duurste werk.
- **Sterkere eerste usecase:** laag-risico werk met veel kleine stukjes waar wél een beslisser nodig is en flag-only volstaat (bijvoorbeeld een Drive- of documentatie-consistentiecheck die afwijkingen op een "voor mij"-lijst zet, nooit zelf verwijdert). Precies het type dat de teruggekomen `06_Marketing` deze week had gevangen.
- **Randvoorwaarde nu vervuld:** Drive-toegang werkt weer en `drive_structure.py` maakt paden rename-proof, dus een Drive-lezende charter is nu technisch mogelijk. Op 30 juni was dat nog geblokkeerd.

### Richtingkeuze simulatielaag: oordeel- en uitkomstenregister starten? (verkenning 2 juli 2026)
**Wat:** de verkenning `docs/verkenning-simulatielaag-general-intuition.md` (ook als Google Doc in `00_Werkdocumenten`) concludeert: de sterkste vertaling van de General Intuition-mechaniek is richting D+A, een oordeel- en uitkomstenregister (beslissingen + verwachtingen + latere uitkomsten vastleggen als cumulatieve asset). Bewoonbare scenario's (C) zijn de commerciële horizon maar horen ná de datafundering.
**Herzien 7 juli 2026:** de "uitkomsten"-helft van dit idee vervalt grotendeels. Deal-uitkomsten hoeven niet apart geregistreerd: het akkoord zit in het finale voorstel (`FINAL`-bestand in `01_Clients`), 95-100% van de waarheid. Er is geen `08_Outcomes`-template om te vullen (fantoom-map, leeg steigerwerk). Wat WEL een apart en onbeantwoord idee blijft: een **oordelen-en-verwachtingen**-register (voorspellingen van experts vastleggen om ze later te toetsen), dat is iets anders dan deal-uitkomsten.
**Voorgestelde kleinste eerste stap (herzien):**
1. VERVALLEN: handmatig uitkomsten loggen in 08_Outcomes. In plaats daarvan: retrieval-first in `build_proposal` (haalt uit de bestaande finale voorstellen) is de echte eerste stap, zie Technisch-backlog.
2. `meeting_reviewer` uitbreiden met sectie "Oordelen en verwachtingen" → append-only register in Drive (skill-tekstwijziging, geen nieuwe architectuur). Alleen als de open vraag hieronder JA is.
3. Maandelijks terugkijk-moment in `#ainstein-status`: welke open voorspellingen hebben een uitkomst?
**Open vraag [aanname in doc]:** willen Jörgen en de experts dat hun oordeel vastgelegd en herbruikbaar wordt? Nooit expliciet besproken. Dit is de enige echte beslissing die dit item nog draagt.
**Beslissing Thomas/Jörgen:** akkoord op deze richting en eerste stap, of andere prioritering.

### Optie 2 (Claude Projects): connector eerst testen, niet aannemen — gecorrigeerd 2 juli 2026
**Correctie:** de connector-blokkade was nooit een gemeld Optie 2-probleem; dat was een inferentie van Claude, geen waargenomen feit. Of de Projects-connector dezelfde file-hiding bug heeft als de Claude Code-connector is ONBEKEND (zelfde connector-familie, dus plausibel, maar niet getest sinds de herstructurering van 30 juni).
**Wel bewezen (Claude Code-kant):** de sessie-connector leest de Shared Drive in beide richtingen onbetrouwbaar (stil lege lijsten, valse negatieven bij zoeken, spookdata uit oude mappen). Voor een niet-technische gebruiker als Jörgen zou dat de gevaarlijkste situatie zijn: stil een fout antwoord dat hij niet kan diagnosticeren.
**Actie vóór lancering Optie 2:** test één keer in een echt Claude Project of browse en file-lezen op de Shared Drive betrouwbaar werken (bv. "wat staat er in 03_Experts?" en een Drive-link laten lezen, resultaat vergelijken met `verify_shared_drive.py`-output). Werkt het: connector mag dragend zijn. Faalt het: Files-first inrichten of doorschuiven naar de service-account-route (Optie 3).
**Beslissing Thomas/Jörgen:** wanneer deze test te doen, en bij falen welke route.

### Beslissing evidence-bar kennis-laag: wanneer automatiseren?
**Wat:** de trigger voor automatisering (`run_kennisextractie.py` via GitHub Actions) is gekoppeld aan een evidence-bar. Die heeft nog geen concrete deadline.
**Criteria uit roadmap:** ≥1 promotie van kennis naar bronnenlaag, óf een say-vs-sell-gat dat aantoonbaar tot een commerciële actie leidde.
**Actie Thomas/Jörgen:** geef de evidence-bar een concrete datum of concrete actie als trigger. Anders blijft dit eeuwig open.

### Kwaliteitscheck eerste productie-output meeting_reviewer
**Wat:** twee Drive-docs van 18 juni zijn nog niet handmatig beoordeeld: `260618_Gespreksnotitie _ Voorbereiding Hei-dag Waardestromen` en `260618_Debrief_SNI_NonLife_Leiderschapsprogramma`. Dit is de validatiestap vóór Ainstein breder ingezet wordt bij klantgesprekken.
**Actie Thomas:** open beide docs in Drive en beoordeel of de analyse correct en commercieel bruikbaar is.

### Kwaliteitsbeoordeling 7 gecureerde kennislaag-docs
**Wat:** de 7 documenten die op 24 juni zijn aangemaakt na Charlotte's validatie (4x in `02_Frameworks & Tools`, 3x in `04_Marketing` — zie ✅ Gedaan-archief) zijn nog niet inhoudelijk beoordeeld op kwaliteit/bruikbaarheid.
**Actie Thomas/Jörgen:** lees de 7 docs (via `read_file_cached`, niet de connector) en beoordeel of de synthese klopt en commercieel bruikbaar is.
**Eerst gevlagd:** 25 juni 2026 (carry-forward in reviews, nooit in roadmap zelf opgenomen — hier alsnog toegevoegd 6 juli 2026).
**Prioriteit:** medium — bepaalt of de kennislaag-methode het vertrouwen krijgt om breder te schalen.

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

### GitHub-credentials saneren: MCP her-authenticeren + PAT uit remote-URL halen
**Onderzocht 2 juli 2026 — volledige credential-inventaris:**
- MCP-connector: `Bad credentials` (verlopen; eerst gevlagd 2026-06-15).
- macOS-keychain-entry github.com: 401, óók verouderd.
- **De enige werkende credential is een PAT die in platte tekst in de remote-URL staat** (`.git/config`). Daarmee werkt push én de GitHub API (bewezen: klacht geplaatst op anthropics/claude-code#53442). Werkende route vanuit sessies gedocumenteerd in `memory/connector_access_paths.md`.
**Actie Thomas (één sanering, ~15 min):**
1. Genereer één nieuw Personal Access Token op github.com (repo + read:org scopes)
2. Vernieuw de GitHub MCP-connector ermee (Claude Code desktop: Settings > Connectors)
3. Zet de keychain-entry recht en haal de token uit de remote-URL: `git remote set-url origin https://github.com/tthiadens-TT/Ainstein.git` — bij de eerste push vraagt git om de nieuwe token en bewaart die in de keychain
4. Trek de oude PAT (uit de remote-URL) in op github.com — die heeft in platte tekst in `.git/config` en in sessie-output gestaan
**Prioriteit:** medium-hoog — geen productie-impact, maar drie verschillende credential-plekken waarvan twee dood en één in platte tekst is onhoudbaar en veroorzaakte deze sessie opnieuw uitzoekwerk.
**Update 5 juli 2026:** ook de `gh` CLI is niet geïnstalleerd in de lokale/daily-review-omgeving — dit is nu 3 dagen op rij (3, 4, 5 juli) een blinde vlek voor PR/issue-status in elke daily-code-review. `daily-code-review`-skill is vandaag aangepast om automatisch op de GitHub MCP-tools terug te vallen zodra `gh` ontbreekt, maar zolang de MCP-auth ook stuk is (zie hierboven) blijft PR/issue-status structureel onbekend. Deze sanering lost dus twee losse problemen in één keer op.
**Deelverificatie 8 juli 2026:** stap 3 blijkt al gedaan — `git remote -v` toont een schone HTTPS-URL zonder embedded token (waarschijnlijk via de keychain-herstel-actie van 6 juli, zie memory `connector_access_paths.md`). `gh` CLI ontbreekt nog steeds (geverifieerd: `which gh` geeft niets). Niet geverifieerd: of de oude PAT is ingetrokken op github.com (stap 4, alleen Thomas kan dat) en of de GitHub MCP-connector inmiddels vernieuwd is (stap 2). Restant: stap 2 (MCP her-auth) + stap 4 (oude PAT intrekken) + `gh` CLI installeren.

### ✅ `_detect_meeting_type()` misclassificatie-risico
**OPGELOST 5 juli 2026.** Eerst gevlagd 2026-07-04, herbevestigd nog open op 2026-07-05, daarna direct gefixt. Meeting werd als `internal` geclassificeerd zodra geen deelnemer een niet-Minkowski e-maildomein had — ook als dat kwam doordat Jamie simpelweg geen e-mailveld aan een deelnemer had gekoppeld (bv. "Speaker 1"). Fix: deelnemers zonder e-mailveld blokkeren nu de interne classificatie (ze zijn geen bewijs van "geen externen", ze zijn onbekend). 5 nieuwe tests in `tests/test_detect_meeting_type.py`, inclusief het exacte Lead3-scenario van 3 juli als regressietest. Volledige suite (51/51) groen.

### ✅ Insights-update toont onterecht altijd "✅" bij mislukte placeholder-vervanging
**OPGELOST 5 juli 2026.** Eerst gevlagd 2026-07-04, herbevestigd nog open op 2026-07-05, daarna direct gefixt. `update_gdoc_section()` geeft bij een ontbrekende placeholder `status: "not_found"` terug zonder te raisen — `slack_app.py` controleerde die status niet en toonde altijd "✅ Insights toegevoegd". Fix: nieuwe helper `_insights_update_message()` in `slack_app.py` checkt de status van beide vervangingen en toont een eerlijke ⚠️-melding als een placeholder niet is gevonden. 4 nieuwe tests in `tests/test_insights_update_message.py`.

### MCP-koppelingen — twee open beslissingen
**Calendar MCP:** ✅ token vernieuwd (19 mei 2026), "minkowski"-account correct op `thomas@minkowski.org` gezet. Minkowski-agenda zelf nog leeg — vul zakelijke afspraken in als je agenda-context in briefings wilt.
**Gmail MCP:** werkt, maar leest `tthiadens@gmail.com`. Beslissing: moet Ainstein de Minkowski-inbox (`thomas@minkowski.org`) kunnen lezen, en voor welk gebruik?
**Notion MCP:** verbonden, maar 0 pagina's gedeeld. Eenmalige handeling in Notion UI (Settings → Connections). Beslissing: welke pagina's wil je beschikbaar maken?

---

## 📋 Backlog — Architectuuropties (Major Decisions)

### OPTIE 2: Claude Projects Goed Inrichten — Tutorial & Checklist
> ⚠️ **Verouderde mapnamen (markering 7 juli 2026):** dit hele tutorialblok hieronder gebruikt de pre-migratie type-structuur (`01_Proposals`, `07_Feedback`, `08_Outcomes`) die op 30 juni is vervangen door de entiteit-structuur (`01_Clients`, gaps.md in `05_Ainstein Knowledge Base`). `08_Outcomes` is bovendien een fantoom-map (zie Technisch-backlog + CLAUDE.md). Lees de mapverwijzingen hieronder als achterhaald; het werkwijze-idee (samen in een Project aan een voorstel werken met feedback-loop) blijft geldig. Bij activeren eerst de paden actualiseren.

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
| Slack status-berichten (start/stop/crash) toonden UTC maar labelden zichzelf "(Amsterdam)" — `datetime.now()` was naive (server-local = UTC op de VM). Bevestigd via 4 restart-berichten 8 juli tussen 07:03-07:47 CEST die zichzelf "05:xx" noemden. Fix: `_AMS = ZoneInfo("Europe/Amsterdam")` + `datetime.now(_AMS)` op alle drie plekken (start/stop/crash), zelfde patroon als `agent.py:19`. 2 nieuwe tests, 90/90 groen. | `slack_app.py` | 8 juli 2026 |
| Foutief metadata-label gecorrigeerd in het al opgeslagen Lead3-Jamie-bakje (`04_Marketing/_bronmateriaal/jamie/2026-07-03_Lead3 Leadership Program Design_19z10qfa.md`). Bestand van vóór de `_detect_meeting_type()`-fix (`92f20ba`, 5 juli): stond nog als "Type: internal, Klant/context: intern Minkowski-overleg" terwijl de transcript-inhoud zelf expliciet "NN's AI specialists (Michael and Jerry)" noemt — een NN Group/Lead3-klantsessie. Gecorrigeerd naar "Type: client, Klant/context: NN Group — Lead3 Leadership Program Design", met bronvermelding van de correctie in de regel zelf. Alleen de ene metadata-regel gewijzigd (geverifieerd byte-voor-byte), rest van de ruwe transcript (het Aslander-goud) ongemoeid. Backup bewaard vóór schrijven, terugleesverificatie geslaagd. Eerst gevlagd: daily-review 2026-07-04. | Drive (service account, lokaal) | 8 juli 2026 |
| Twee bugs uit daily-review 8 juli gefixed. (1) Em dash-lek: `_extract_client_line()` in `transcript_processor.py` gaf de LLM-gegenereerde "Klant/traject"-regel ongefilterd door aan Slack, en het model negeerde het CORE em dash-verbod herhaaldelijk (~2/3 van de gevallen op 7-8 juli). Mechanische guard toegevoegd (`—` → `,`) i.p.v. alleen op prompt-adherentie te vertrouwen. (2) Codeblok-lek: `skills/briefing_writer.md` toont zijn eigen outputtemplate binnen een ```-codeblok om het format te demonstreren; Haiku reproduceerde dat blok soms letterlijk, waardoor elke Meetingnote begon/eindigde met een kale ``` -regel (eerst gevlagd 7 juli, direct zichtbaar naast de net gefixte merk-opmaak `f605536`). Nieuwe `_strip_code_fence()` in `transcript_processor.py`, verwijdert een omringende fence alleen als die de VOLLEDIGE respons omvat (een losse code-snippet middenin blijft intact). 6 nieuwe tests (1 em dash + 5 fence-cases), 88/88 groen. | transcript_processor.py | 8 juli 2026 |
| Kennislaag bron-governance uitgezocht + LinkedIn-compleetheids-lek gedicht (code-deel). Bewezen via serviceaccount op de VM: de pijplijn las 42 posts (`linkedin_jorgen_archief.md`) terwijl een 120-post-scrape (27 mei) verweesd in de root lag. `scrape_linkedin.py` compleetheids-grendel gebouwd (`_count_posts` + `_pick_richest`: stabiele naam, weigert overschrijven met minder, convergeert naar één bestand); docstring recht. `scripts/consolidate_linkedin_source.py` (eenmalig, dry-run default, overlap-grendel via shingles) — dry-run geverifieerd op de VM. Toegevoegd aan `audit_claude_md.py` SKIP_MODULES. 82/82 tests groen, audit geslaagd. Data-apply (VM-write) + Double Helix-herrun + echte merge-tot-één-bestand + routine-herontwerp staan als vervolg in de sectie "Kennislaag bron-governance". Mijn eerdere sessiediagnose ("twee versies vechten in één map") was fout en is door VM-verificatie gecorrigeerd — de map was schoon, de rommel lag verweesd in de root. | scraper-fix + consolidatiescript | 8 juli 2026 |
| Repo-audit met workflow (4 parallelle scans + onafhankelijke verificatie per bevinding, 27 agents, 22 kandidaat-bevindingen, 21 bevestigd). Direct uitgevoerd na dubbele verificatie (zelf herhaald, niet alleen de workflow geloofd): 8 stale remote branches verwijderd (`claude/ainstein-slack-questions-AmZir`, `claude/busy-dhawan-14fcc1`, `claude/charlotte-recent-documents-Nm1Tp`, `claude/confident-babbage-4fafaf`, `claude/determined-haslett-2386c1`, `claude/quirky-jemison-02ab60`, `claude/review-code-plans-CrWIC`, `fix/startup-logging-and-deploy-check` — allemaal 0 unieke commits t.o.v. main, of al via ander pad aanwezig). Roadmap-item "Prompt Coaching format fixen" verwijderd: probleem al op 31 mei gefixed (`0953e5d`), geverifieerd dat "max 4 regels" niet meer in `brain.md` staat. `HANDOFF.md` verwijderd: volledig achterhaalde eenmalige sessie-overdracht (31 mei) die een Jamie-integratie als "nog te bouwen" beschreef terwijl die allang live is. Overige bevindingen (LinkedIn Jörgen-bronvarianten, LEAD3-pptx-duplicaten, `list_drive_changes.py`, Test/Meetingnotes-groei, NN Group lege submappen, onboarding-doc-naamgeving) staan apart genoteerd — zie backlog, vereisten eerst een beslissing of dieper onderzoek. | roadmap-edit + `git push origin --delete` (8x) | 8 juli 2026 |
| `tools.py` Tavily `search_depth` niet meer hardcoded. `TAVILY_SEARCH_DEPTH` env var toegevoegd (default `"basic"`, was hardcoded `"advanced"`), gedocumenteerd in `.env.example`. Voorkomt onbewust sneller opmaken van het gratis Tavily-quotum (1.000 zoekopdrachten/maand). Geen tests raakten de oude hardcoded waarde. Testsuite 82/82 groen, audit_claude_md geslaagd. | geen aparte hash bekend bij schrijven | 8 juli 2026 |
| Stale backlog-item verwijderd: "Bug: `feedback.py` auto-review trigger onbetrouwbaar" beschreef een probleem dat al op 3 juli was opgelost (`d551b64`, persistent maken van `_open_count` via `logs/open_count.txt`) en al in dit archief stond. Geverifieerd door de huidige code te lezen: fix staat er en werkt. Dubbel-boeking in de open backlog gecorrigeerd. | verificatie + roadmap-edit | 8 juli 2026 |
| `audit_claude_md.py` toegevoegd aan CI. **Vóór het toevoegen eerst geverifieerd dat de check zelf slaagt** (`python3 scripts/audit_claude_md.py` gaf initieel 14 ontbrekende items — was direct als blokkerende CI-stap toegevoegd, zou elke toekomstige deploy hebben gebroken). CLAUDE.md aangevuld met 6 echt ontbrekende productie-scripts (`drive_structure.py`, `convert_to_markdown.py`, `verify_cache_structure.py`, `restore_voice.py`, `update_stijl.py`, `backfill_jamie_meetings.py`) en 3 skills (`briefing_writer`, `extract_style_patterns`, `minkowski_voice`). 3 one-off/testscripts (`cleanup_stray_cache.py`, `migrate_stray_marketing.py`, `test_jamie_webhook.py`) bewust naar `SKIP_MODULES` — al gedocumenteerd in roadmap/CACHE_DESIGN.md, geen architectuur. Audit slaagt nu (0 issues), stap toegevoegd aan `.github/workflows/deploy.yml` na de syntax-check, binnen dezelfde job als `deploy` (dus faalt CI vóór deploy als iemand een module/skill vergeet te documenteren). Testsuite 82/82 groen na wijziging. | roadmap-item, geen aparte commit-hash bekend bij schrijven | 8 juli 2026 |
| Drie bijna-identieke cache-cleanup-scripts geconsolideerd tot één. `cleanup_batch_delete.py` en `cleanup_direct.py` verwijderd (geverifieerd: geen cron, geen tests, geen andere code refereert eraan — alleen genoemd in roadmap-proza). `cleanup_stray_cache.py` (enige met `--dry-run`) blijft over, met een toegevoegde waarschuwing in de docstring dat het op 5 juli faalde op stale Drive file-ID's en niet zonder heroverweging opnieuw gedraaid moet worden. | roadmap-item, geen aparte commit-hash bekend bij schrijven | 8 juli 2026 |
| Bug `slack_nn-schade-inkomen_2026-05.md` onleesbaar — **onderzocht en weerlegd, geen bug.** Bestand rechtstreeks gelezen via het serviceaccount op de VM (grondwaarheid, niet de connector): 20.211 bytes, valide UTF-8, geen controletekens, geen null-bytes, geen vervangingstekens, begin en eind van het bestand inhoudelijk correct en compleet (Slack-gesprek 25-26 mei 2026, #nn-schade-inkomen). Er bestaat maar één bestand met deze naam (geen verborgen duplicaat met corrupte inhoud). Conclusie: de oorspronkelijke "onleesbaar"-melding (21 juni 2026) was vrijwel zeker een connector-false-negative (hetzelfde patroon als het HERKENNINGSALARM in CLAUDE.md), geen data-corruptie. Geen codewijziging nodig. | Drive-verificatie via SSH+serviceaccount | 8 juli 2026 |
| Ainstein: live Slack-leestool. `list_slack_channels`, `read_slack_channel`, `search_slack` toegevoegd aan `tools.py`, zelfde patroon als de bestaande Drive-tools. Vult laag 3 (contextlaag, real-time per vraag) van de kennisgroeistrategie — Ainstein kon Slack eerder alleen schrijven, nooit lezen. Bot-token had `channels:history`/`channels:read` al, live geverifieerd op de VM, geen nieuwe Slack-scope-aanvraag nodig. 9 nieuwe tests (volledig gemockt), suite 82/82 groen. Live smoke-test op de VM tegen echte Slack API geslaagd. Gepusht naar main en dus via GitHub Actions auto-deploy live op de VM (geverifieerd via `git log`, niet aangenomen — de roadmap-tekst zei nog "wacht op akkoord" maar dat was al achterhaald). | `2883d1f` | 7 juli 2026 |
| Fable-sessie (idee 4 uit de Ainstein Slack-thread): "What's Your Future?" gebouwd als `whats-your-future/` — statisch facilitator-instrument voor discovery-gesprekken (Cone of Possibilities: probable/plausible/preferable, 4 ICP-sectoren × 4 thema's = 48 scenario's + leiderschapsvragen, 3 signal-houdingen, Copy-session-summary naar Ainstein-pipeline, print-output). Orchestrator-patroon bewezen: Fable plande/verifieerde, 3× Sonnet + 1× Haiku bouwden, 1 revisieronde (stem-consistentie). Brand-learnings uit parallelle sessie direct toegepast: fontrollen gecorrigeerd (Sen ExtraBold alleen wordmark, Helvetica Neue koppen, Light body). Plus twee zelfstandig uitvoerbare Fable-briefs voor idee 1 en 5 in `plans/fable-brief-*.md`. End-to-end getest via Playwright (scoring-randen, klembord, alle stappen). | `1386b68`, `5e6d509` | 6 juli 2026 |
| GitHub keychain-incident opgelost: een 401 op een verouderd tweede token liet git álle github.com-keychain-entries wissen (osxkeychain wist op host, niet op account) — pushen brak machinebreed. Werkend token teruggezet vanaf de VM-credential-store (met expliciet akkoord Thomas, buiten auto-modus; eerst gevalideerd via API-call). Herstelroute + valkuil gedocumenteerd in memory `connector_access_paths.md`. GitHub MCP-token blijft verlopen (bestaand roadmap-item). | keychain-herstel | 6 juli 2026 |
| Brand consistency audit afgerond — 5 commits live: f59a099 (CORE/PATTERNS scheiding + sentinel-parsing), 6ace92c (Brand CORE onvoorwaardelijk injectie), 880003c (brand_core.md feitelijke basis injectie), 36c55f7 (Minkowski-kleur/font op alle Google Docs), f605536 (Meeting Notes vermerking). Probleem 1: `update_stijl.py` dupliceerde wekelijks met fragiel kopftekst-matching, nu sentinel-based (hard-fail op ontbrekende markers, geen stille append). Probleem 2: CORE-regels stonden dubbel (verbal_identity.md + minkowski_voice.md), nu enkel in verbal_identity.md, via agent.py onvoorwaardelijk geïnjecteerd. Probleem 3: visual_identity.md was leeg — gevuld met geverifieerde waarden uit pptx_builder.py + brondocument, gelabeld als "code-afgeleid/onbevestigd". Test-isolatie: 22 nieuwe tests toegevoegd (4 testbestanden), suite 73/73 groen. 200 OK webhook-test. | `f59a099` t/m `f605536` | 6 juli 2026 |
| Roadmap-inconsistentie recht getrokken: cache-opruiming stond tegelijk als "🔴 URGENT, blokkeert afsluiting" én als "✅ VOLLEDIG OPGELOST". Herbevestigd via `verify_cache_structure.py` op de VM (grondwaarheid): alle 157 violations staan nog steeds in de folder-roots (86 `04_Marketing`, 41 `01_Clients`, 25 `03_Experts`, 3 `02_Frameworks & Tools`, 2 `05_Ainstein Knowledge Base`) — geen voortgang sinds 4 juli. De ✅-sectie herschreven zodat de 🔴 URGENT-sectie de enige actuele status is. Nieuw follow-up-item toegevoegd: drie mislukte, bijna-identieke cleanup-scripts consolideren. Gevonden door daily-code-review 6 juli. | Drive-verificatie + roadmap-edit | 6 juli 2026 |
| Twee bugs uit de daily-code-review van 4-5 juli geverifieerd opgelost in `92f20ba`: `_detect_meeting_type()` classificeerde een klantgesprek stilzwijgend als intern zodra een deelnemer geen e-mailveld had; Insights-reply toonde altijd "✅" ongeacht of `update_gdoc_section()` de placeholder vond. Geverifieerd door de diff te lezen (niet aangenomen) + testsuite lokaal gedraaid: 51/51 groen. | `92f20ba` | 6 juli 2026 (geverifieerd, gefixt 5 juli) |
| Twee stale backlog-items verwijderd: (1) "Losse screenshots in repo-root opruimen" — bestanden bevestigd verdwenen uit de working directory; (2) "Legacy Google Doc Slack-bestanden verwijderen uit Drive" — was al opgelost en genoteerd in dit archief op 3 juli ("0 gevonden, al eerder weg"), stond ten onrechte nog als open item verderop in de roadmap. | roadmap-edit | 6 juli 2026 |
| `entiteiten.md` foute noot verwijderd: de "Technische noot (29 juni)" claimde dat expertprofielen alleen in de persoonlijke Drive stonden, NIET in de Shared Drive. Onafhankelijk geverifieerd via serviceaccount: `03_Experts` bevat 54 items waarvan 23 expertprofielen (.docx). Bug-artefact van de connector-blokkade. Noot verwijderd via serviceaccount (80→71 regels, byte-identiek teruggelezen, backup bewaard). Restant gesignaleerd: Beheerregels verwijzen nog naar oude mapnaam `04_Experts` (moet `03_Experts`). | Drive | 3 juli 2026 |
| dev-branch opgeruimd: lokaal + remote `dev` verwijderd en losse stash gedropt. Geverifieerd dat alle waardevolle inhoud al superseded is op main (skills `6fff459`, save_note-refactor, `DEPLOYMENT.md`, deploy.yml health-check, en de stash-fix `_send_chunked` lege-tekst-guard staan al op main). Herstel-SHA vastgelegd: `git branch dev faf53f0`. | lokaal + remote | 3 juli 2026 |
| Auto-review-teller persistent gemaakt: `feedback._open_count` nulde bij elke botherstart (drempel 10 werd mogelijk nooit gehaald). Nu best-effort naar `logs/open_count.txt` (gitignored), in-memory teller als fallback, geladen bij import. 2 tests toegevoegd, suite 42 groen. Carry-forward daily-review sinds 18 juni. | `d551b64` | 3 juli 2026 |
| Drive-cosmetica opgeruimd (verifieer-vóór-actie): 2x `.DS_Store` naar prullenbak; `260601_Opzet NN LEAD3`-dubbel via tekst-export bewezen byte-identiek → eerdere kopie getrasht, tweede behouden. Legacy `slack_C09CEQ29AU8` Google Docs: 0 gevonden (al weg). NIET aangeraakt: 4x `LEAD3_NN_Group_Opzet_updated.pptx` (drie verschillende groottes = mogelijk versies, beslissing Thomas). | Drive | 3 juli 2026 |
| Testsuite-isolatie + productie-data hersteld (gevonden door daily-code-review 3 juli). `tests/conftest.py` toegevoegd: autouse-fixture haalt `GOOGLE_SERVICE_ACCOUNT_FILE`/`_JSON` weg vóór elke test, zodat `pytest` nooit meer naar de live Drive schrijft. Was een stil lek: `_is_drive_mode()` sprong in de productie-tak zodra `.env` geladen was, waardoor elke volledige testrun testfixture-feedback toevoegde aan het live `05_Ainstein Knowledge Base/gaps.md` (dat in elke conversatie in de systeemprompt komt). Suite nu 40 groen, 0 Drive-writes (was 33 groen/7 rood). Live `gaps.md` opgeschoond via serviceaccount: 49 fixture-entries (`U1`/`U2`, threads `1700.123`/`1800.456`/`1`) verwijderd, 4 echte feedback-entries behouden, byte-identiek geverifieerd na upload (backup bewaard). | `47ffdc5` + Drive | 3 juli 2026 |
| Jamie-pijplijn scherper na melding Jörgen (klant/traject-verwarring: NN-debrief werd op verkeerd dossier geanalyseerd, kanaalpost noemde 'LEAD3' bij een Inkomen-Collectief-gesprek). (1) `infer_client_name()` in `jamie.py` verzint geen klantnamen meer (fallback 'eerste 3 woorden van de titel' verwijderd, gaf labels als "McKinsey Benchmark en"); `skills/meeting_reviewer.md` krijgt Stap 0 (klant/traject zelf vaststellen uit titel/samenvatting/transcript, sub-dossier-regel NN Group/LEAD3, vraag bij twijfel i.p.v. gok); `transcript_processor.py` toont eigen 'Klant/traject:'-regel via `_extract_client_line`. (2) Insights-koppeling race condition: `_pending_insights` hield maar 1 koppeling per kanaal → tweede meeting overschreef stil de eerste; nu lijst per kanaal met titel-matching + expliciete vraag bij ambiguïteit. (3) DM omgebouwd naar Block Kit (`_build_dm_blocks`, `_chunk_text`), dode `_post_dm_status` verwijderd. 4 nieuwe testbestanden (19 tests). Live op VM (service herstart ná commit). Let op: gedragsfix in LLM-redeneerstap, nog niet bewezen op een echte meeting (zie open verificatie-item). | `762447b`, `59db17f`, `7cded90` | 2 juli 2026 |
| Verweesde data gemigreerd + spookmap opgeruimd + kraan-dicht bewezen. `scripts/migrate_stray_marketing.py` (dry-run/apply, prullenbak-veilig): 2 unieke juli-Slack-bestanden verplaatst naar echte `04_Marketing`, 2 juni-bestanden gemergd (30-juni-berichten die de echte map miste alsnog bewaard, `nn-ks-it` 5→6KB, `nn-lead3` 4,5→9KB), 1 identiek bestand + dubbele lege `_kennis` naar prullenbak, stray `06_Marketing` volledig weg. Bewijs kraan dicht: live Slack-scraper resolvet naar echte `04_Marketing`-slackmap en maakt géén nieuwe `06_Marketing` aan. Root heeft weer precies 6 mappen (00–05). | `5cd2bec` e.v. | 3 juli 2026 |
| Alle oude mapnamen uit huidige-systeem-docs verwijderd (scraper-docstrings, tools.py tool-descriptions/comments, gdoc_tools, convert_to_markdown, README-tabel, DEPLOYMENT, HANDOFF, `.claude/projects.json`). Gedateerde meirapporten in `reports/` bewust ongemoeid (historisch). | `a519900` | 3 juli 2026 |
| Dynamische Drive-mapresolutie: `drive_structure.py` toegevoegd (herkent top-level mappen aan nummer-voorvoegsel 00_ t/m 05_, niet aan naam; fail loud, nooit top-level spookmap, oudste-wint bij duplicaten). Alle scrapers (slack/linkedin/medium/substack/website), `update_stijl`, `restore_voice`, `run_kennisextractie` en `tools.save_text_bakje` omgebouwd van hardcoded `("06_Marketing", …)` naar `drive_structure`. `tools._build_drive_folder_ids` registreert rol-aliassen op voorvoegsel (folder_ids.get('04_Marketing') rename-proof). Dode code `scripts/setup_outcomes.py` verwijderd. Geverifieerd op VM: zelftest resolvet alle rollen correct naar de échte mappen (niet de spookmap), oudste-wint pikt gevulde `_kennis`. Datalek gestopt. | `bd836c6` | 2 juli 2026 |
| Verkenning simulatielaag / General Intuition-mechaniek afgerond: fase 1-inventarisatie (businessmodel Minkowski eerst, dan Ainstein), 4 richtingen (beslis-ledger, adversariale simulatie, bewoonbare scenario's, expert-intuïtie vangen), DVV-toets + onderscheidendheidsonderzoek (6 zoekacties: Gong, Principle, synthetic personas, wargaming, GI-feitencheck: aankondiging 25 juni 2026, niet januari). Advies: D+A eerst. Document in `docs/` + Google Doc in `00_Werkdocumenten`. Beslispunt toegevoegd aan Beslissingen-sectie. | deze sessie | 2 juli 2026 |
| Drive-connector-dossier fundamenteel uitgezocht (multi-agent onderzoek + serviceaccount-scan). Uitkomst: (1) connector-blokkade is een open Anthropic-bug (#53442), geen Workspace-instelling, geen fix in onze hand; (2) connector geeft valse negatieven bij zowel mappen als zoeken, enige betrouwbare lezer = serviceaccount; (3) migratie 21 mei was COMPLEET, `AInstein_OUD` was redundant en is door Thomas verwijderd; (4) drie eerdere "opgelost"-afsluitingen waren onjuist, nu gedocumenteerd tegen herhaling. `scripts/verify_shared_drive.py` toegevoegd als grondwaarheid-tool. | `c76d878`, `d1c33ad` e.v. | 2 juli 2026 |
| Bug gefixed: meeting-titel verdween uit Jamie-DM sinds commit 7c588d0 (26 juni) toen `_build_dm_blocks()` werd vervangen door platte `debrief_text`. Titel-regel (`:microphone: *titel*`) teruggezet in `_post_slack_notification()`. Gevonden n.a.v. melding Jörgen in Slack. Getest via `scripts/test_jamie_webhook.py` op live VM — bevestigd werkend. | `b589816` | 1 juli 2026 |
| 41 `claude/*` branches + bijbehorende worktrees opgeruimd (elk gecontroleerd op ongecommit werk vóór verwijdering; 1 branch met verouderd font-work via `git branch -D`, inhoud stond al nieuwer op main) | lokaal, geen commit | 1 juli 2026 |
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
