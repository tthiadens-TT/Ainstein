# Skill: briefing_writer

Je taak is het vullen van een vaste Meetingnote-template op basis van een transcript en Jamie-output.

## Outputformaat — gebruik exact deze structuur

```
# Meetingnote — {Organisatie} — {Datum}

**{Naam Minkowski-lead} × {Naam gesprekspartner}** · {Functie} · {Relatie} · {Datum & tijd}

---

## Context
{2–3 zinnen: wie is de organisatie, wat is hun rol, relevante achtergrond}

## Aanleiding
{Wat bracht dit gesprek op gang? Wat speelde er bij de klant?}

## Kern van het vraagstuk
{Het probleem zoals de klant het ervaart — zo dicht mogelijk bij hun eigen woorden}

## Vraag aan Minkowski
{Expliciet of impliciet: wat wil de klant van ons? Als het impliciet is, vermeld dat.}

## Aanbevolen volgende stap
{Concreet: wie doet wat, wanneer}

---

## Samenvatting
{Jamie's samenvatting, gecorrigeerd en ingekort door Ainstein — alleen wat relevant is}

## Acties
- {Wie} — {wat} — {wanneer (indien bekend)}

---

## Insights — [NAAM MINKOWSKI-LEAD]
[INSIGHTS — vul hier in]

---
*Gegenereerd door Ainstein op basis van Jamie-transcript · {Datum}*
```

## Regels

- Vul elk veld in op basis van het transcript en de Jamie-output die je ontvangt
- De sectieheader `## Insights — [NAAM MINKOWSKI-LEAD]` schrijf je letterlijk zo — vervang [NAAM MINKOWSKI-LEAD] NIET door de echte naam
- De Insights-inhoud laat je altijd staan als `[INSIGHTS — vul hier in]`
- Geen speculatie: als iets niet in het transcript staat, schrijf dan "Niet besproken" of "Onbekend"
- Schrijf "Geen acties gelogd." als er geen taken zijn
- Taal volgt het gesprek (NL of EN)
- Gebruik GEEN tools — output direct de ingevulde template, niets anders
- Max 500 woorden totaal
