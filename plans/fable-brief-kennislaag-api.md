# Fable-brief: de Minkowski-methode als querybare structuur (idee 5 uit de Fable-sessie, 6 juli 2026)

*Geschreven door Claude Fable 5 als orchestratie-architect, vlak voor het sluiten van het Fable-window (7 juli 2026). Zelfstandig uitvoerbare spec voor een latere Opus- of Sonnet-sessie. Belangrijk: dit document wijkt bewust af van de oorspronkelijke idee-formulering ("kennislaag als API") en legt uit waarom.*

## Wat & Waarom

**Wat:** een gestructureerd, machine-leesbaar toolregister van alle Minkowski-tools, -methodes en -formats (40+ items uit `02_Frameworks & Tools/02_Tools_Agent_README.md`), plus een deterministische query-tool in Ainsteins `tools.py` die erop filtert. Vragen als "welke tool past bij fase Awaken, 90 minuten, 12 deelnemers" worden een filter-operatie in plaats van een full-text zoektocht.

**Waarom:** Ainstein beantwoordt tool-vragen nu door de 41KB README in context te laden en te interpreteren. Dat is duur, traag en niet-deterministisch: dezelfde vraag kan verschillende antwoorden geven. Programmadesign, expert-onboarding en de Studio-productlijn hebben alle drie hetzelfde nodig: één canonieke, filterbare bron van waarheid over het gereedschap.

**Waarom géén REST-API (afwijking van het oorspronkelijke idee):** de oorspronkelijke formulering (`/api/tools?phase=awaken&duration=90min`) veronderstelt een aparte API-server: extra proces op de VM, extra endpoint, extra onderhoud, en de enige consument is een agent die net zo makkelijk een lokale functie aanroept. Het moderne patroon voor agent-toegankelijke kennis is: gestructureerde data in het repo + een tool-functie erbovenop. Zelfde capability, nul infrastructuur. Als er ooit een externe consument komt (bv. Studio als losse webapp), kan een dunne API-laag alsnog om het register heen; het register zelf verandert daar niet door.

## Ontwerp

### 1. Het register: `data/toolregister.yaml` (in het code-repo)

Eén YAML-bestand, één entry per tool. Het metadata-schema bestaat al en staat letterlijk in `02_Tools_Agent_README.md` (sectie "Metadata to capture where possible"):

```yaml
- id: futures-cone
  name: "Futures Cone / Cone of Possibilities"
  classification: tool          # framework | tool | method | exercise | template | format | role
  canon: part1                  # part1 (canoniek) | part5 (facilitatie) | seed (aanpassen vóór klantgebruik) | index-only
  purpose: "Map the full space of possible futures and widen imagination before strategy work"
  source_evidence: "02_Tools_Agent_README.md Part 1 #5; bevestigd Charlotte 2026-06-23"
  use_case: [trend-mapping, foresight, assumption-challenging]
  program_phase: awaken         # diagnose | design | awaken | assess | accelerate | activate | evaluate
  scope_module: 2
  facilitator_level: senior
  duration_min: 90
  group_min: 6
  group_max: 20
  complexity: medium            # easy | medium | hard
  language: en                  # en | nl | both
  ai_usable: true
```

Waarom YAML in het repo en niet een Drive-doc: versiebeheer per wijziging, review via PR, en de bot leest het zonder Drive-API-call. Drive blijft de bron voor de *documenten* (canvases, instructies); het register verwijst ernaar.

Waarom een `canon`-veld: de README onderscheidt expliciet canoniek materiaal (Part 1), de facilitatie-toolbox van Charlotte (Part 5), seed-content (Futures Readiness Canvas, 2-Day Sprint: "adapt before client use") en een index van nog niet gedocumenteerde tools. Dat onderscheid mag nooit wegvallen in een query-antwoord; Ainstein moet seed als seed labelen.

### 2. De query-tool: `query_tools()` in `tools.py`

Pure Python-filter, geen LLM-call, deterministisch en gratis:

```python
query_tools(phase="awaken", max_duration=90, group_size=12, complexity=None, goal=None)
→ [{"id": "futures-cone", "name": ..., "why_match": ...}, ...]
```

`goal` matcht op `use_case`-tags (exacte tags, geen semantiek; semantische matching doet het model zelf op de teruggegeven shortlist). De tool wordt geregistreerd in het bestaande tool-schema zodat elke skill hem kan aanroepen; `match_experts` en `build_proposal` gaan hem direct gebruiken voor programma-opbouw.

### 3. Vulling van het register (map-reduce, bewezen patroon)

| Stap | Werk | Model |
|---|---|---|
| K1 | Schema definitief + 3 handmatige voorbeeld-entries (Futures Cone, Wheel of Reasoning, SCOPE) als gouden standaard | hoofdsessie |
| K2 | Extractie per bron, parallel: (a) README Part 1, (b) Part 5 + Dutch layer, (c) Charlotte's docx + pptx-index via Drive | Sonnet, 3 calls |
| K3 | Merge + dedupe (Wheel of Reasoning staat in twee lagen; Part 1 is de diepere referentie) + kruising met entiteiten.md "Methodes en frameworks" | Sonnet |
| K4 | **Menselijke verificatie: Thomas/Jörgen/Charlotte keuren het register.** Promotie is mensenwerk, zelfde regel als bij de kennislaag. Vooral `canon`, `facilitator_level` en ontbrekende parameters | mens |
| K5 | `query_tools()` implementeren + tests + skill-instructies bijwerken (match_experts, build_proposal verwijzen naar de tool) | Sonnet |

Index-only tools (Odin Development Compass, Design Sprint, etc.): opnemen met `canon: index-only` en alleen naam + bronverwijzing. Niet verzinnen wat er niet gedocumenteerd is; het register maakt gaten zichtbaar in plaats van ze te verbergen.

## Strategische koppeling (aanvulling, niet gevraagd in het oorspronkelijke idee)

**Minkowski Studio** (het SessionLab-vervanger-prototype op `~/minkowski-studio`) heeft exact dezelfde databehoefte: een sessie-ontwerper die tools sleept in een runsheet wil filteren op duur, groepsgrootte en fase. Bouw het register zó dat Studio het ongewijzigd kan consumeren (dat is precies waarom YAML/JSON met strakke velden wint van een Ainstein-interne oplossing). Eén register, twee producten: Ainstein antwoordt ermee, Studio ontwerpt ermee. Dit maakt het register het meest herbruikbare artefact van de drie Fable-ideeën.

## Risico's

- **Register veroudert naast de README.** Mitigatie: het register is leidend voor parameters, de README voor proza; de daily-code-review checkt bij wijzigingen in `02_Tools`-materiaal of het register mee is. Uiteindelijk kan de README-tooltabel uit het register gegenereerd worden (omkering, latere stap).
- **Verleiding tot semantiek in de query-tool.** Houd de tool dom (filters, tags). Zodra er "slimme" matching in de Python-laag sluipt, wordt het gedrag ondoorzichtig en ontstaat een tweede, concurrerende redeneerlaag naast het model.
- **K4 wordt overgeslagen onder tijdsdruk.** Niet doen: een fout `facilitator_level` of `canon`-label in het register schaalt de fout naar élk programma-ontwerp dat erop bouwt.

## Succescriteria

1. "Geef me een check-in van 15 minuten voor 25 mensen" levert via `query_tools` altijd dezelfde, correcte shortlist (deterministisch).
2. Elke entry traceert naar bronmateriaal; seed en index-only zijn als zodanig gelabeld in elk antwoord.
3. Studio kan het bestand inladen zonder transformatie.
4. De 41KB README hoeft niet meer standaard in context voor tool-vragen (meetbaar: tokens per tool-vraag dalen).
