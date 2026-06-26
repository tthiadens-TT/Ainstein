# Skill: extract_style_patterns

## Purpose

Extraheer en verrijk schrijfstijlpatronen van Minkowski op basis van bronmateriaal (LinkedIn-posts, Substack-artikelen, websiteteksten). Doel: `skills/minkowski_voice.md` actueel houden als Minkowski's stem evolueert.

Dit is een **descriptieven** taak — beschrijf hoe Minkowski en Jörgen daadwerkelijk schrijven, niet hoe ze zouden moeten schrijven. Stijl wordt waargenomen, niet verzonnen.

## Input

Je ontvangt:
- De huidige `minkowski_voice.md` inhoud (tussen `<HUIDIGE_STEM>` tags)
- Bronmateriaal — recente LinkedIn-posts, Substack-artikelen, websiteteksten (tussen `<BRONNEN>` tags)

## Taak

Analyseer het bronmateriaal en identificeer:

1. **Nieuwe vocabulaire** — woorden of uitdrukkingen die Minkowski/Jörgen gebruiken maar nog niet in de vocabulairetabel staan. Let op: wat staat er naast de bekende woorden? Nieuwe termen die patronen vormen.

2. **Nieuwe directe citaten** — krachtige zinnen die rechtstreeks bruikbaar zijn als voorbeeld of in voorstellen. Alleen verifieerbare, letterlijke citaten — nooit parafraseren.

3. **Patroonobservaties** — zijn er nieuwe schrijfpatronen zichtbaar die de vier bestaande aanvullen of nuanceren? Wees terughoudend: voeg alleen toe als het een echt nieuw patroon is, niet een variant van de vier bestaande.

4. **Stijlverschuivingen** — is de toon of focus merkbaar verschoven ten opzichte van wat in de huidige stem staat? Wees expliciet als iets vervagend is.

## Outputformaat

Lever precies één fenced blok met de **volledige bijgewerkte inhoud** van `minkowski_voice.md` — geen diff, geen commentaar erbuiten, alleen de volledige tekst.

Begin het blok met `<<<STEM_START>>>` en sluit af met `<<<STEM_END>>>`.

Bewaar de structuur van het huidige bestand. Voeg toe, verwijder verouderde termen, pas voorbeeldcitaten aan. Verander de koptekst (*Laatste update: DATUM*) naar de datum van vandaag.

## Kwaliteitscheck vóór oplevering

- Staan er geen verzonnen citaten in? Alleen letterlijke bronnen.
- Is de vocabulairetabel specifieker dan het generieke equivalent? Niet alleen "gebruik X niet Y" maar waárom X beter is.
- Zijn de vier kernpatronen intact? Die zijn stabiel tenzij het bronmateriaal écht iets nieuws laat zien.
- Is de taalregel (EN voor klantgerichte output) ongewijzigd?
