# Skill: extract_knowledge_distilleer (MAP-stap)

Je distilleert **één** databron tot een compacte lijst van onderwerpen (entiteiten) met hun facetten. Dit is de **map-stap** van de kennis-pipeline: elke bron wordt los verwerkt zodat de context klein blijft en nooit overloopt. Een latere **reduce-stap** kruist alle distillaties over onafhankelijke oorsprongen — dat doe jij hier expliciet **niet**.

## Wat je in de prompt krijgt
- **Eén bron:** `bron` (naam), `oorsprong` (onafhankelijkheids-label), `locatie` (Drive-map).
- **De datum van vandaag.**

## Werkwijze

**Stap 1 — Lees de bestanden in deze bron.**
Gebruik `list_folder` op de top-map uit `locatie` en filter op het pad, dan `read_file` op de relevante bestanden.
- Goedkope bronnen (`.md` in `_bronmateriaal`): lees volledig.
- Dure bronnen (`01_Proposals`, `.docx`/`.pdf`): lees de **recentste per klant-submap, totaal ≤8**. Toets kandidaat-onderwerpen liever met `search_files` dan alles voluit te lezen.
- Een leeg/onleesbaar bestand: meld het op een eigen regel (`- LET OP: {bestand} onleesbaar`), ga door — nooit stilzwijgend overslaan.

**Stap 2 — Verzamel per onderwerp de facetten.**
Welke concrete dingen zegt deze bron over dit onderwerp? Houd het compact: korte zinnen, geen lange citaten.

**Tijd vastleggen.** Noteer per facet de **periode/het jaar** als de bron een datum heeft (publicatiedatum van een artikel/post, datum in een transcript). Schrijf het als `(jaar)` of `(jaar-jaar)` achter het facet. Heeft de bron geen datum, laat het weg. Noteer onderaan het blok de **periode die deze bron beslaat** (oudste → nieuwste datum die je zag). Dit voedt de tijd-analyse in de reduce-stap.

**Onderwerptypes:** `thema | positionering | methode | taalpatroon | klant-/sectorpatroon | bewijspunt`.
**Geen feiten** — prijzen, dagtarieven, expertnamen, aantallen horen hier niet (die worden actueel gehouden, niet getrianguleerd).

**Epistemologisch type per entiteit** — label elke entiteit met één van:
- `feit` — specifiek en verifieerbaar: methodenaam, klantvermelding, dateerbare uitspraak, concreet resultaat
- `overtuiging` — consistent verkondigd standpunt dat niet extern toetsbaar is: positioneringsclaim, filosofische stelling, mening
- `afleiding` — patroon zichtbaar in taal of gedrag, maar nooit zo expliciet benoemd door de bron

## Outputformaat — exact één fenced blok, niets eromheen

```
<<<DISTILLATIE_START>>>
bron: {bron} | oorsprong: {oorsprong} | gelezen: {n} bestand(en) | periode: {oudste}–{nieuwste of "onbekend"}
- {entiteit} — {type} | epistemologisch: {feit | overtuiging | afleiding}
  - {concreet facet} ({jaar indien bekend})
  - {concreet facet}
- {entiteit} — {type} | epistemologisch: {feit | overtuiging | afleiding}
  - {concreet facet} ({jaar-jaar})
<<<DISTILLATIE_END>>>
```

## Regels
- Bewerk **nooit** een bestand. Alleen lezen.
- Rapporteer wát de bron zegt — geen oordeel, geen interpretatie, geen "dit is belangrijk".
- Tel **niet** zelf oorsprongen of zekerheid; dat is de reduce-stap. Jij levert alleen de facetten van déze ene bron.
- Compact blijven: dit blok wordt samen met alle andere distillaties aan de reduce-stap gevoerd. Hoe bondiger, hoe beter.
- Alle uitvoer in platte Markdown.
