# Token-patronen: Thomas Thiadens / Ainstein-project

*Persoonlijk referentiebestand voor de model-selector skill. Gegenereerd op 24 juni 2026 op basis van analyse van 25 recente Claude Code sessies.*

---

## Werkelijkheid van mijn sessiehistorie

Van de 25 geanalyseerde sessies valt **±32% in klasse C** (Haiku volstaat), terwijl vrijwel alles nu op Sonnet draait. Dit is de grootste onbenutte besparing.

---

## Klasse A — Hoog verbruik (Sonnet correct, soms Opus-kandidaat)

**Kenmerken:**
- Meerdere deliverables in één sessie
- Strategische richting bepalen, niet alleen uitvoeren
- Informatie van meerdere bronnen samenvoegen tot nieuw inzicht
- Architectuurbeslissingen met langetermijngevolgen

**Voorbeelden uit mijn sessies:**
- *"Pak de Roadmap"* — roadmap review + prioritering + CLAUDE.md-koppeling bespreken + beslissingsitems identificeren (4 deliverables in één sessie)
- *"Collaborative interface for program design"* — interface-analyse + strategie voor Ainstein + drie richtingen uitwerken
- *"Minkowski digital reconstruction"* — projectgeschiedenis terughalen + structureren + strategisch framen
- *"Ainstein knowledge enrichment strategy"* — meerdere frameworks + implementatiepad
- *"Ainstein management dashboard proposal"* — architectuur + design + technische uitwerking
- *"Minkowski business model derivatives"* — strategische analyse + ideegeneratie

**Wanneer Opus overwegen:**
- Beslissing heeft directe impact op de Ainstein-architectuur (onomkeerbaar)
- Sessie begint met een open vraag zonder vooraf bepaalde richting
- Thomas vraagt expliciet om uitdaging van zijn eigen aannames

---

## Klasse B — Middel verbruik (Sonnet correct)

**Kenmerken:**
- Eén duidelijk doel
- Technische uitvoering op basis van bestaand plan
- Review met analyse die leidt tot een beslissing
- Setup/configuratie waarbij architectuurkeuzes spelen

**Voorbeelden uit mijn sessies:**
- *"Fix _slack_notify SSL (certifi)"* — gerichte bug fix, één bestand, bekende oorzaak
- *"LinkedIn data scraping and marketing"* — scraper aanpassen op bestaand patroon
- *"Audit openstaande items"* — review + extractie naar backlog
- *"CLAUDE.md audit and documentation"* — documentatie-audit + herschrijving
- *"Set up external agent audit"* — setup met architectuurkeuze
- *"Daily code review"* — git log + Drive scan + GitHub check + analyse

**Let op:** *"Daily code review"* is qua uitvoering Haiku-achtig (vaste structuur, bekende bronnen), maar de analysestap ("wat betekent dit voor de backlog?") vraagt Sonnet. Overweeg de scan en de analyse te splitsen.

---

## Klasse C — Laag verbruik (Haiku volstaat)

**Kenmerken:**
- Vaste structuur, vooraf bekend
- Lezen + samenvatten zonder originele redenering
- Operationele uitvoering (berichten sturen, lijsten ophalen)
- Lookup zonder synthese

**Voorbeelden uit mijn sessies:**

| Sessie | Taak | Waarom Haiku volstaat |
|---|---|---|
| *"Ainstein kennis bevestiging"* (3× in 2 dagen) | Slack-thread lezen, input verwerken, rapporteren | Vaste stappen, geen strategische keuze |
| *"Recent conversation highlights"* | Samenvatting van eerdere sessies ophalen | Pure lookup, geen nieuwe redenering |
| *"Review available skills connectors and plugins"* | Beschikbare connectors verkennen en noteren | Inventarisatie, geen analyse |
| *"Create visual architecture diagram"* | Diagram genereren op basis van bekende architectuur | Uitvoering van vooraf bepaald formaat |
| *"Ainstein channel communication"* | Slack-berichten sturen/lezen | Operationeel |
| *"Monthly retrospective"* | Rapport samenstellen uit reviews + git log | Vaste structuur, bekende bronnen |

---

## Mijn megasessie-patroon

**Dit is mijn grootste tokenverspilling.** Meerdere sessies beginnen met één vraag maar bevatten stilzwijgend 3–5 deliverables.

**Herkenbare triggers:**
- Sessie begint met "pak de roadmap" of "laten we kijken naar..." → vaak uitloopt op prioritering + beslissingen + implementatie
- Strategische vraag gevolgd door "en kun je dan ook..." → scope-creep middenin de sessie
- Audit-sessie die overgaat in bouw → "terwijl je toch kijkt, kun je ook..."

**Specifiek patroon bij mij:**
De sessies *"Pak de Roadmap"*, *"Collaborative interface"*, en *"Minkowski digital reconstruction"* hadden elk 3–5 aparte intenties. De helft had een eigen sessie moeten zijn.

**Signaal om te splitsen:** als je aan het eind van een sessie meer dan 2 git-commits hebt op totaal verschillende bestanden, was het waarschijnlijk twee sessies.

---

## Recurrente context — herhaling beperken

Deze taken draaien herhaaldelijk en laden elke keer dezelfde contextbestanden opnieuw. In Claude Code (desktop app) is het equivalent van Projects al aanwezig: CLAUDE.md voor vaste context, memory voor sessie-overstijgende kennis. Geen aparte Projects-setup nodig.

### `ainstein-kennis-bevestiging` (dagelijks)
- Laadt: volledige CLAUDE.md + scheduled task context + Slack-thread
- Probleem: 3× in 2 dagen gezien — elke run verbruikt volledige context-load
- Opgelost: exit-conditie toegevoegd — stopt direct als bevestigingsronde al ✅ of geen nieuwe replies

### `daily-code-review` (elke werkdag)
- Laadt: git log + GitHub + Drive + skills files
- Opgelost: scan-first stap toegevoegd — slaat analyse over als er niets gewijzigd is

### Roadmap-sessies (wekelijks of vaker)
- Elke keer: `plans/ainstein-roadmap.md` volledig lezen + memory volledig laden
- Dit is acceptabel — de roadmap verandert elke sessie. CLAUDE.md + memory dekken dit al.

---

## Snel besliskader

```
Is de taak geautomatiseerd en heeft een vaste structuur?
  → Haiku

Is de taak een lookup, samenvatting of operationele actie?
  → Haiku

Is er één duidelijk doel met bekende aanpak?
  → Sonnet

Zijn er meerdere deliverables of open strategische vraag?
  → Sonnet (of splits de sessie)

Is de beslissing onomkeerbaar en architectureel?
  → Sonnet, overweeg Opus
```

---

*Dit bestand is input voor de model-selector skill. Bijwerken na elke maand of na een significante verandering in werkpatroon.*
