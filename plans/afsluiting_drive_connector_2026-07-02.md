# Afsluitingsdossier: Drive-connector blokkade

*Sessie 2 juli 2026. Status: dossier gesloten. Dit document is de naslag.*

---

## Wat & Waarom (lees dit eerst)

**Wat:** een volledige afsluiting van het terugkerende "AI-blokkade"-probleem op de Google Drive-connector, inclusief samenvatting, eerlijke evaluatie, afgeronde acties, geleerde lessen, een geverifieerde workaround, een bugrapport voor Anthropic, en de resterende open punten.

**Waarom:** dit probleem is over vijf weken herhaaldelijk ten onrechte "opgelost" verklaard. Het kostte veel tijd, tokens en geld, deels door echt onderzoek en deels door herhaalde te snelle conclusies. Dit document borgt de uitkomst zodat het niet nog een keer gebeurt, en zodat Thomas met Claude kan doorwerken zodra de blokkade weer opduikt.

---

## 1. Samenvatting: wat het probleem echt was

De MCP Google Drive-connector (die Claude Code sessies gebruiken) leest de Workspace Shared Drive "Minkowski AInstein" onbetrouwbaar. Concreet:

- **Geverifieerd mechanisme (test 2 juli):** bij een `parentId`-opvraging toont de connector wel de **submappen** van een Shared Drive-map, maar verbergt de **bestanden**. Daardoor lijkt een map met submappen te "werken" (`04_Marketing` gaf submappen terug maar verborg zijn 15 losse bestanden) en lijkt een map met alleen bestanden "leeg" (`03_Experts`: 54 bestanden, 0 submappen, dus lege respons). **Alle mappen hebben het probleem; het valt alleen niet op bij mappen met submappen.** Dit verklaart het raadsel "sommige mappen wel, andere niet": dat was een illusie.
- **Werkt wel:** lezen op een bekend file-ID (ook native Google Docs). **Werkt niet:** bestanden listen per map, en `list_recent_files` toont nooit bestanden. **Zoeken** (`fullText`/`title`) geeft daarnaast valse negatieven. Alles faalt STIL: geen fout, gewoon een lege of onvolledige lijst.
- **Losse tweede tool kapot:** `mcp__gdrive__search` faalt volledig (`MCP error -32603`, elke input).

**Root cause:** een open bug bij Anthropic (`anthropics/claude-code#53442`), vermoedelijk ontbrekende `supportsAllDrives`/`includeItemsFromAllDrives`/`corpora`-parameters. NIET een Google Workspace-instelling (die hypothese is onderzocht en verworpen). Wij kunnen de connector niet repareren.

**Waarom niet eerder als bekende bug herkend (terechte vraag van Thomas):** eerdere sessies wezen naar een plausibele *interne* oorzaak (onze eigen commit `15bec6c` schakelde over op `text/plain` .md-bestanden, "dus de AI-policy blokkeert text/plain"). Die zelf-consistente verklaring kortsloot het zoeken naar een externe, gemelde bug. Dat was fout: het is een connector-bug, geen gevolg van onze code.

**Waarom productie het niet kent, en het voor de migratie niet bestond:** de bot leest via het serviceaccount (raakt de connector nooit), en voor 21 mei stond de data in de persoonlijke Drive (My Drive), die de connector wel gewoon leest. De bug leeft uitsluitend op de combinatie (connector) x (Shared Drive). De migratie naar de Shared Drive legde hem bloot. Het gaat inderdaad om iets simpels, een map lezen, en juist daarom is het zo wrang dat het zo lang zoek was.

**De kern van de schade:** het falen is stil. Een lege uitkomst is niet te onderscheiden van "echt leeg". Daardoor leidde het herhaald tot foute conclusies, waaronder een volledig multi-agent onderzoek dat concludeerde dat de Drive-migratie van 21 mei "incompleet" was, terwijl een serviceaccount-scan bewees dat de hele bronnenlaag gewoon compleet in de Shared Drive staat.

---

## 2. Evaluatie (eerlijk)

**Wat misging:**
- De blokkade dook op in **minstens 7 eerdere sessies** (transcript-zoekactie, 2 juni t/m 30 juni: "Charlotte's recent files", "Daily code review", "LinkedIn scraping", "Outstanding tasks review", "Martijn Aslander", "Roadmap/backlog", "Ainstein project overview"). Waarschijnlijk meer, want er is alleen op de term "ineligible" gezocht. Thomas' vermoeden dat het een veelvoud van 3 keer was, klopt.
- Het leidde ~3 keer tot een volledig onderzoek met een verkeerde eindconclusie (o.a. 22 juni "geen actie nodig" `a18fe6e`; 29 juni "04_Experts is leeg", beide fout). Een sessie (29 juni) legde vast dat Thomas het opgelost wilde, niet gedocumenteerd. Dus: heel veel tijd, tokens en geld verloren, verspreid over weken.
- Deze sessie herhaalde Claude het patroon zelf: drie keer met stellige toon een "oplossing" (Workspace-instelling, Smart Features, GitHub-issue) voor er getest werd.
- De multi-agent inventarisatie van `AInstein_OUD` bouwde conclusies op de kapotte connector, precies de val die net was gedocumenteerd. De subagents (en Claude, die hun output doorgaf) trapten er alsnog in.
- Het transcript-onderzoek (hoe vaak het opdook) had veel eerder gemoeten; Thomas moest erop wijzen dat alle sessies naslaanbaar waren.

**Wat goed ging:**
- Thomas' herhaalde "weet je het zeker" en "we lopen toch tegen die blokkade aan" dwongen af dat er uiteindelijk getest werd in plaats van getheoretiseerd.
- Het serviceaccount-script gaf definitieve grondwaarheid, los van de kapotte connector.
- De echte fout (herkenning, niet de workaround) is blootgelegd en geborgd.

**Kosten:** aanzienlijk in tijd en tokens. Het echte technische probleem was klein; het leeuwendeel ging naar de foute conclusies en naar onderzoek dat deels nodig en deels verspild was.

---

## 3. Afgeronde acties (deze sessie, op `main`)

| Actie | Commit |
|---|---|
| Read-only verificatiescript `scripts/verify_shared_drive.py` (leest Shared Drive via serviceaccount) | `fd7f5e4` |
| Fix: repo-root op sys.path | `c76d878` |
| Fix: `.env` laden bij handmatige run | `d1c33ad` |
| Roadmap: connector-item herschreven (van "opgelost/root cause" naar "bekende beperking, root cause onbekend") | `859ae6b` |
| Roadmap: opruimpunten, OAuth-secret, Optie 2-beslissing, adopt-fix-trigger | `38a9c23` |
| CLAUDE.md: herkenningsalarm + Operating Rule 19 | `376a4e5` |
| CLAUDE.md: self-serve read-only VM-verificatie bij blokkade | `3acc1f8` |
| Geheugen bijgewerkt: `connector_access_paths.md`, `feedback_way_of_working.md` | (memory, buiten repo) |
| `AInstein_OUD` verwijderd door Thomas (bleek volledig redundant) | handmatig |
| Dit dossier + bugrapport in `plans/`, redundante repo-kopie OAuth-secret verwijderd | deze commit |

---

## 4. Wat we hebben geleerd

**Over het probleem:**
1. Geen enkele connector-uitkomst over de Shared Drive is betrouwbaar, positief noch negatief. Enige betrouwbare lezer = het serviceaccount op de VM.
2. De migratie van 21 mei was compleet. De "incompleet"-conclusie was een artefact van de bug.
3. De notitie in `entiteiten.md` ("expertprofielen staan alleen in de persoonlijke Drive, niet in de Shared Drive", 29 juni) was niet zomaar achterhaald, ze was van meet af aan FOUT: een verkeerde conclusie die de connector-bug in de gecureerde kennislaag heeft geschreven. Geverifieerd: de 54 expertbestanden staan wel in `03_Experts`. Dit toont de diepste schade van de bug: hij besmette niet alleen sessies, maar ook het geheugen en de kennislaag zelf.

**Over hoe Claude werkt, de belangrijkste les:**
4. Bij "waarom werkt X niet"-vragen: eerst een directe, live test, nooit eerst een theorie of externe bron als verklaring.
5. Delegeren aan subagents ontslaat niet van de betrouwbaarheidscheck van hun gereedschap. Een negatieve conclusie van een subagent die op een bekend-kapot instrument leunt, is ruis, geen bevinding.
6. De echte faalmodus was herkenning midden in een grotere taak, niet de workaround. Daarom staat de fix nu als herkenningsalarm in CLAUDE.md (elke sessie gelezen), niet als losse procedure.
7. Het verify-script kon lokaal niet getest worden (de serviceaccount-sleutel staat alleen op de VM) en er waren drie fix-rondes nodig (ontbrekend `sys.path`, ontbrekende `.env`-load). Les: bij een nieuw script in `scripts/` eerst de bestaande zusterscripts als sjabloon nemen, die hadden beide patronen al.

**Strategisch inzicht (uit de "ondenken"-analyse):**
8. De connector mag nergens een dragend pad zijn, niet in sessies en niet in Claude Projects. Het serviceaccount is de enige betrouwbare leeslaag. De echte vraag was niet "hoe fixen we de connector", maar "wat willen we eigenlijk": dat Jorgen en Charlotte zonder Thomas met actuele kennis kunnen werken, zonder dat er stil verkeerde data insluipt.

---

## 5. Verificatie & test (werkt de workaround, en komt de blokkade terug?)

**Workaround, vers getest 2 juli 2026 (read-only, via VM serviceaccount):**
- `03_Experts` (map die de connector leeg teruggeeft): script gaf 54 bestanden.
- `02_Frameworks & Tools` (idem): script gaf 12 bestanden.
- Volledige Shared Drive: 358 bestanden in 59 mappen.

De workaround werkt. Claude kan hem ook zelf aanroepen vanuit een lokale sessie via SSH naar de VM, read-only, bewezen op `03_Experts`, zonder Thomas te onderbreken.

**Komt de blokkade nooit meer terug? Eerlijk antwoord:**
- Dat is NIET te garanderen. De blokkade is een bug in Anthropic's connector, buiten onze macht. Hij kan blijven bestaan of terugkeren in sessies.
- Maar de workaround (serviceaccount) is architectureel onafhankelijk van de connector en dus immuun. En het herkenningsalarm zorgt dat Claude de blokkade voortaan herkent in plaats van er foute conclusies op te bouwen.
- Netto: de blokkade kan terugkomen, maar hij kan het werk niet meer stilzwijgend derailen.

**Als Anthropic een oplossing heeft, gaan we die gebruiken:**
- Vastgelegd als trigger in de roadmap: monitor `#53442` en de Claude Code changelog. Zodra het issue sluit of een Shared Drive / `supportsAllDrives`-fix wordt gemeld: hertest de connector met dezelfde parentId- en fullText-checks tegen `03_Experts`. Werkt het betrouwbaar, dan mag de connector weer een dragend pad worden.

---

## 6. Bugrapport / klacht voor Anthropic

**Eerlijke verwachting:** er is geen formeel klachtenkanaal met vergoeding voor bestede tokens. De hoogste hefboom is een reactie op het bestaande open issue `#53442` (20+ melders), plus eventueel `/bug` in een interactieve Claude Code-terminal.

**Kern van de klacht:** het probleem is niet alleen dat het faalt, maar dat het STIL faalt, wat herhaald tot foute conclusies en veel verspilde tijd/tokens leidde.

Het volledige, plak-klare rapport (Engels) staat naast dit dossier: `plans/anthropic_bugreport_53442.md`. Kernpunten:
1. Silent false-negatives op Shared Drives, bij zowel mapopvraging als zoeken; mechanisme: submappen zichtbaar, bestanden verborgen.
2. Verzoek: stuur de drie Drive-API-vlaggen mee; en als een query geen Shared Drive kan dekken, geef een FOUT in plaats van een stille lege lijst.
3. Fix `mcp__gdrive__search` (-32603).
4. Documenteer Shared Drive-ondersteuning in het help-artikel.

---

## 7. Wat we nog moeten of zouden kunnen doen, en waarom

| Punt | Prioriteit | Waarom | Eigenaar |
|---|---|---|---|
| **Bugrapport indienen op `#53442`** | Doen | Enige weg naar de echte fix; laat onze reproductie meewegen. Rapport staat klaar in `plans/anthropic_bugreport_53442.md` | Thomas |
| **Code-migratie afmaken + orphaned folders opruimen** | **Medium-hoog** | Onderzocht en herbevestigd: de 30-juni-hernoeming is in Drive gedaan maar NIET in de code. 13 verwijzingen naar oude mapnamen in 9 Python-bestanden (`tools.py`, `scrape_*.py`, `update_stijl.py`, `restore_voice.py`, `run_kennisextractie.py`), plus `.claude/projects.json`. Gevolg: scrapers maken de oude map (`06_Marketing`) opnieuw aan en schrijven verse data (Slack, LinkedIn, voice) naar een verweesde map die Ainstein niet leest. Actieve data-split, geen cosmetische rommel. **Volgorde:** eerst code fixen, dan orphaned data naar `04_Marketing` migreren, dan pas orphans + dubbele lege `_kennis` (30 juni-artefact) + `.DS_Store` weg. Weggooien voor de code-fix = de map komt terug | Claude (code) + Thomas |
| **Optie 2 (Claude Projects): eerst testen, niet aannemen** | Open vraag | De blokkade was NOOIT een gemeld Optie 2-probleem; dat was een inferentie. Onbekend of de Projects-connector dezelfde file-hiding bug heeft. Actie: test dat een keer voor Optie 2 op de connector gebaseerd wordt; faalt het, dan is de service-account-route (Optie 3) het antwoord | Thomas/Jorgen |
| **`entiteiten.md` foute noot verwijderen** | Laag-medium | De noot is aantoonbaar fout (profielen staan wel in `03_Experts`), een bug-artefact in de kennislaag. Verwijderen voorkomt dat een toekomstige sessie de fout weer overneemt. Vereist schrijfpad via VM (`update_drive_file.py`); SSH vanuit sessies is read-only, dus dit hoort bij een reguliere werkstroom | Bij eerstvolgende bewerking |
| **Adopt-fix hertest** zodra Anthropic levert | Wachten | Connector weer bruikbaar maken als de bug gefixt is | Claude, op trigger |

Afgehandeld in deze sessie (was open punt): redundante repo-kopie van het OAuth-secret verwijderd na byte-voor-byte verificatie dat `~/.minkowski_gdrive_credentials.json` (het echte, in gebruik bij `setup_gdrive_auth.py`) identiek is.

---

## 8. Beslissingen (genomen)

1. **SSH naar de VM: bestaande toegang, zelfopgelegde read-only grens.** Claude heeft zichzelf geen toegang gegeven, dat kan niet; de Bash-tool draait op Thomas' laptop, als Thomas, en erft de toegang die daar al is (SSH-key, git push, connectors). De SSH-toegang is technisch een volledige shell en `git push` kan productie wijzigen via de deploy. De "read-only" is dus een regel in CLAUDE.md, geen technische grendel; ze berust op discipline, niet op een slot.
   **Gekozen (2 juli 2026): laten zoals het is.** Read-only regel op vertrouwen; staat in CLAUDE.md (commit `3acc1f8`). Heroverweeg een technisch beperkt pad (read-only sleutel of beperkte SSH-key) als de VM-toegang ooit breder gebruikt gaat worden.
2. **Dit afsluitingsdossier + bugrapport in de repo bewaren:** gedaan, dit bestand en `plans/anthropic_bugreport_53442.md`.
