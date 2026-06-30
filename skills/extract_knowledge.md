# Skill: extract_knowledge

Je bouwt Minkowski's kennis-laag op door meerdere databronnen te kruisen. Twee taken, even belangrijk:

- **Verrijken** — "wat weten we er allemaal over?" Elke bron voegt facetten toe aan een onderwerp. Oorsprong maakt niet uit: twee bronnen van dezelfde stem die verschillende dingen zeggen, leveren allebei een stukje.
- **Bevestigen** — "klopt dit, is het geen ruis?" Telt alléén over **onafhankelijke oorsprongen**. Twee bronnen met dezelfde oorsprong = één bevestiging.

Onafhankelijkheid bepaalt *zekerheid*; verrijking bepaalt *compleetheid*. Dit is triangulatie (de gatenkaas), geen DIKW — frequentie meet consistentie, niet waarheid.

## Wat je in de prompt krijgt

- **Bron-lijst (JSON):** per bron een `oorsprong` (onafhankelijkheids-label) en een `locatie` (Drive-map). Meerdere bronnen mogen dezelfde oorsprong delen.
- **Eventueel de huidige kennis-laag** tussen `<HUIDIGE_LAAG>` … `</HUIDIGE_LAAG>`.
- **De datum van vandaag.**

**Twee modi:**
- **Geen `<HUIDIGE_LAAG>` in de prompt → ad-hoc modus.** Lever alleen de samenvatting (de twee gaten + opvallende bevindingen). Geen fenced blokken, geen laag.
- **Wél `<HUIDIGE_LAAG>` → laag-modus.** Doe de volledige merge en lever beide fenced blokken (zie Outputformaat).

## Wat een oorsprong betekent (voorbeelden)

- `jorgen-published` (LinkedIn, Substack) — wat Minkowski naar buiten **verkondigt**.
- `minkowski-intern` (Slack) — intern denken/operatie.
- `commercieel` (01_Clients) — wat we **verkopen/pitchen**.
- `klant` (01_Clients/<naam>/Programs of finale voorstel-doc) — programma-ontwerp en geaccepteerd voorstel zijn het sterkste signaal dat iets werkt. Volledig onafhankelijke stem.

## Werkwijze

**Stap 1 — Lees de huidige laag (laag-modus).**
Neem elk bestaand blok over. Onthoud welke entiteiten `gepromoveerd` of `afgewezen` zijn en wat in `## Promotiebesluiten` staat — die zijn **bevroren**: niet opnieuw als kandidaat opvoeren, wel last-seen bijwerken.

**Stap 2 — Verrijken: lees alle bronnen per oorsprong.**
Voor elke bron in de lijst: gebruik `list_folder` op de top-map uit `locatie` en filter op het pad, dan `read_file` op de relevante bestanden.
- Goedkope bronnen (`.md` in `_bronmateriaal`): lees volledig.
- Dure bronnen (`01_Clients`, `.docx`/`.pdf`): lees de **recentste per klant-submap, totaal ≤8**. Toets daarna kandidaat-onderwerpen liever met `search_files` dan alles voluit te lezen.
- Een lege/onleesbare bron: meld het expliciet, ga door (nooit stilzwijgend overslaan).

Verzamel per onderwerp (entiteit) de **facetten**: welke concrete dingen zeggen de bronnen erover, en bij welke oorsprong hoort elk facet?

Onderwerptypes: `thema | positionering | methode | taalpatroon | klant-/sectorpatroon | bewijspunt`. **Geen feiten** — experts en prijzen horen hier niet (die worden actueel gehouden, niet getrianguleerd).

**Stap 3 — Bevestigen: tel distinct oorsprongen.**
Per entiteit: hoeveel **onafhankelijke oorsprongen** noemen het?
- 1 oorsprong → onbevestigd
- 2 oorsprongen → informatie
- 3+ oorsprongen → kennis

Méér bronnen binnen één oorsprong verhoogt de zekerheid **niet** — voegt wél facetten toe.

**Stap 4 — De twee gaten (de kop).**
- **Verkondigd, niet verkocht** — alleen `jorgen-published`/`minkowski-intern`, niet in `commercieel`/`klant`. Mooie positionering die niet in voorstellen landt.
- **Verkocht, niet verkondigd** — alleen `commercieel`/`klant`, niet in de gepubliceerde stem. Onbenutte sterkte.

**Stap 5 — Merge naar de laag (laag-modus).**
Match nieuwe bevindingen op **genormaliseerde naam** (lowercase, leestekens weg, enkelvoud) tegen bestaande blokken; werk bestaande blokken bij i.p.v. dubbel toevoegen. Reproduceer elk bestaand blok verbatim tenzij je het wijzigt. Bump `Laatst gezien`. Raak `## Promotiebesluiten` **nooit** aan. Voer bevroren entiteiten niet opnieuw als kandidaat op.

## Outputformaat

**Ad-hoc modus** — gewone tekst:
```
**Verkondigd, niet verkocht:** [bullets of "niets opvallends"]
**Verkocht, niet verkondigd:** [bullets of "niets opvallends"]
**Nieuwe bevestigde kennis (3+ oorsprongen):** [bullets]
**Kanttekening:** [bv. dun klant-signaal als 01_Clients/<naam>/Outcomes leeg is]
```

**Laag-modus** — exact twee fenced blokken, niets eromheen dat ertussen hoort:

```
<<<LAAG_START>>>
# Kennis-laag — Minkowski
_Laatste run: {datum} | verrijken + bevestigen (onafhankelijke oorsprongen) | NIET de bronnenlaag — promotie is mensenwerk_

## Entiteiten

### {naam} — {type}
- Zekerheid: {ONBEVESTIGD|INFORMATIE|KENNIS} ({n} oorsprongen: {lijst})
- Facetten:
  - {facet} — {oorsprong} ({bron/datum})
- Eerst/laatst gezien: {datum} / {datum}
- Status: {promotie-kandidaat | onbenutte sterkte | verkondigd niet verkocht | gepromoveerd | afgewezen}

## Promotiebesluiten (sticky — niet opnieuw voorstellen)
{ongewijzigd overnemen}
<<<LAAG_END>>>

<<<SAMENVATTING_START>>>
{de vier kopjes uit de ad-hoc modus: de twee gaten, nieuwe promotie-kandidaten, kanttekening}
<<<SAMENVATTING_END>>>
```

## Regels

- Bewerk **nooit** de bronnenlaag (`verbal_identity.md`, `positioning.md` etc.) — promotie is mensenwerk.
- Curated docs en AI-syntheses zijn **geen bron** — ze zijn het promotiedoel. Lees ze niet als bron.
- Rapporteer feiten, geen interpretaties: "komt voor in `commercieel` + `klant`", niet "dit is belangrijk".
- Alle uitvoer in platte Markdown.
- Onleesbaar of leeg bestand: benoem het, ga door.
