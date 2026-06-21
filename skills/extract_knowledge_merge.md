# Skill: extract_knowledge_merge (REDUCE-stap)

Je krijgt **distillaties van meerdere bronnen** (elk al teruggebracht tot entiteiten + facetten, met hun `oorsprong`) plus de **huidige kennis-laag**. Je kruist ze en werkt de laag bij. Je leest **geen** bronnen meer — alles wat je nodig hebt zit in de distillaties. Geen tool-aanroepen nodig.

Twee taken, even belangrijk:
- **Verrijken** — voeg facetten uit alle distillaties samen per entiteit. Oorsprong maakt niet uit voor compleetheid: twee bronnen van dezelfde stem die verschillende dingen zeggen, leveren allebei een facet.
- **Bevestigen** — telt alléén over **onafhankelijke oorsprongen**. Twee distillaties met dezelfde `oorsprong` = één bevestiging.

Onafhankelijkheid bepaalt *zekerheid*; verrijking bepaalt *compleetheid*. Dit is triangulatie (de gatenkaas), geen DIKW — frequentie meet consistentie, niet waarheid.

## Wat een oorsprong betekent (voorbeelden)
- `jorgen` / `minkowski` — wat Minkowski naar buiten **verkondigt** (LinkedIn, Substack, Medium, website). Let op: al deze eigen kanalen zijn ten hoogste twee stemmen (`jorgen`, `minkowski`), géén losse bevestigingen per kanaal.
- `minkowski-intern` (Slack) — intern denken/operatie.
- `commercieel` (01_Proposals) — wat we **verkopen/pitchen**.
- `klant` (08_Outcomes) — win/verlies; een volledig onafhankelijke stem.
- `gesprekken` (Jamie) — meetings; klanten/experts/collega's.

## Werkwijze

**Stap 1 — Lees de huidige laag.**
Neem elk bestaand blok over. Onthoud welke entiteiten `gepromoveerd`/`afgewezen` zijn en wat in `## Promotiebesluiten` staat — die zijn **bevroren**: niet opnieuw als kandidaat opvoeren, wel last-seen bijwerken.

**Stap 2 — Voeg de distillaties samen per entiteit.**
Match op **genormaliseerde naam** (lowercase, leestekens weg, enkelvoud). Verzamel alle facetten en noteer bij elk facet de `oorsprong`.

**Stap 3 — Bevestigen: tel distinct oorsprongen.**
- 1 oorsprong → ONBEVESTIGD
- 2 oorsprongen → INFORMATIE
- 3+ oorsprongen → KENNIS

Méér distillaties binnen één oorsprong verhoogt de zekerheid **niet** — voegt wél facetten toe.

**Stap 4 — De twee gaten (de kop).**
- **Verkondigd, niet verkocht** — alleen `jorgen`/`minkowski`/`minkowski-intern`, niet in `commercieel`/`klant`. Mooie positionering die niet in voorstellen landt.
- **Verkocht, niet verkondigd** — alleen `commercieel`/`klant`, niet in de gepubliceerde stem. Onbenutte sterkte.

**Stap 5 — Merge naar de laag.**
Werk bestaande blokken bij i.p.v. dubbel toevoegen. Reproduceer elk bestaand blok verbatim tenzij je het wijzigt. Bump `Laatst gezien`. Raak `## Promotiebesluiten` **nooit** aan. Voer bevroren entiteiten niet opnieuw als kandidaat op.

## Outputformaat — exact twee fenced blokken, niets eromheen dat ertussen hoort

```
<<<LAAG_START>>>
# Kennis-laag — Minkowski
_Laatste run: {datum} | verrijken + bevestigen (onafhankelijke oorsprongen) | NIET de bronnenlaag — promotie is mensenwerk_

## Entiteiten

### {naam} — {type}
- Zekerheid: {ONBEVESTIGD|INFORMATIE|KENNIS} ({n} oorsprongen: {lijst})
- Facetten:
  - {facet} — {oorsprong}
- Eerst/laatst gezien: {datum} / {datum}
- Status: {promotie-kandidaat | onbenutte sterkte | verkondigd niet verkocht | gepromoveerd | afgewezen}

## Promotiebesluiten (sticky — niet opnieuw voorstellen)
{ongewijzigd overnemen}
<<<LAAG_END>>>

<<<SAMENVATTING_START>>>
**Verkondigd, niet verkocht:** [bullets of "niets opvallends"]
**Verkocht, niet verkondigd:** [bullets of "niets opvallends"]
**Nieuwe bevestigde kennis (3+ oorsprongen):** [bullets]
**Kanttekening:** [bv. dun klant-signaal als 08_Outcomes leeg is]
<<<SAMENVATTING_END>>>
```

## Regels
- Bewerk **nooit** de bronnenlaag — promotie is mensenwerk.
- Rapporteer feiten, geen interpretaties: "komt voor in `commercieel` + `klant`", niet "dit is belangrijk".
- Alle uitvoer in platte Markdown.
