# Skill: extract_style_patterns

## Purpose

Extraheer en verrijk schrijfstijlpatronen van Minkowski op basis van bronmateriaal (LinkedIn-posts, Substack-artikelen, websiteteksten). Doel: de PATTERNS-zone van `skills/minkowski_voice.md` actueel houden als Minkowski's stem evolueert.

Dit is een **descriptieve** taak — beschrijf hoe Minkowski en Jörgen daadwerkelijk schrijven, niet hoe ze zouden moeten schrijven. Stijl wordt waargenomen, niet verzonnen.

**Scope sinds 2026-07-06:** je ziet en bewerkt uitsluitend de PATTERNS-zone (vier schrijfpatronen, vocabulaire-tabel, directe citaten, NL/EN-verschil). De vaste kernregels (taalregel, verboden woorden, em dash-verbod, schrijfregels) staan in `verbal_identity.md` — die zie je niet en mag je niet verzinnen of herhalen.

## Input

Je ontvangt:
- De huidige PATTERNS-inhoud (tussen `<HUIDIGE_PATTERNS>` tags) — niet het volledige bestand, alleen de evoluerende laag
- Bronmateriaal — recente LinkedIn-posts, Substack-artikelen, websiteteksten (tussen `<BRONNEN>` tags)

## Taak

Analyseer het bronmateriaal en identificeer:

1. **Nieuwe vocabulaire** — woorden of uitdrukkingen die Minkowski/Jörgen gebruiken maar nog niet in de vocabulairetabel staan. Let op: wat staat er naast de bekende woorden? Nieuwe termen die patronen vormen.

2. **Nieuwe directe citaten** — krachtige zinnen die rechtstreeks bruikbaar zijn als voorbeeld of in voorstellen. Alleen verifieerbare, letterlijke citaten — nooit parafraseren.

3. **Patroonobservaties** — zijn er nieuwe schrijfpatronen zichtbaar die de vier bestaande aanvullen of nuanceren? Wees terughoudend: voeg alleen toe als het een echt nieuw patroon is, niet een variant van de vier bestaande.

4. **Stijlverschuivingen** — is de toon of focus merkbaar verschoven ten opzichte van wat in de huidige stem staat? Wees expliciet als iets vervagend is.

## Outputformaat

Lever precies één fenced blok met de **volledige bijgewerkte PATTERNS-inhoud** — geen diff, geen commentaar erbuiten, alleen de volledige tekst van de PATTERNS-zone (vier schrijfpatronen, vocabulaire, citaten, NL/EN-verschil).

Begin het blok met `<<<STEM_START>>>` en sluit af met `<<<STEM_END>>>`.

Bewaar de structuur van de huidige PATTERNS-inhoud. Voeg toe, verwijder verouderde termen, pas voorbeeldcitaten aan.

## Kwaliteitscheck vóór oplevering

- Staan er geen verzonnen citaten in? Alleen letterlijke bronnen.
- Is de vocabulairetabel specifieker dan het generieke equivalent? Niet alleen "gebruik X niet Y" maar waárom X beter is.
- Zijn de vier kernpatronen intact? Die zijn stabiel tenzij het bronmateriaal écht iets nieuws laat zien.
- Heb je geen taalregel, verboden-woordenlijst of em dash-regel toegevoegd? Die horen hier niet — die staan in `verbal_identity.md` en vallen buiten jouw scope.
