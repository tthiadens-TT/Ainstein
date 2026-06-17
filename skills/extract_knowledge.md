# Skill: extract_knowledge

Je past het Aslander IA-principe toe op de ruwe databronnen van Minkowski.

Kernprincipe (gatenkaas): een naam, concept of patroon dat in meerdere ONAFHANKELIJKE bronnen
verschijnt is betrouwbaarder dan een eenmalige vermelding.
- 1 bron = data (mogelijk ruis)
- 2 bronnen = informatie (patroon waarneembaar)
- 3+ bronnen = kennis (betrouwbaar, promotie-kandidaat)

## Werkwijze

**Stap 1 — Lees elke bron onafhankelijk**
Lees de bakjes in `06_Marketing/_bronmateriaal/` één voor één:
- `slack/` — Slack-berichten per kanaal per maand
- `linkedin/` — LinkedIn-posts van Jörgen en Minkowski
- `substack/` — Substack-artikelen van Jörgen

Gebruik search_files en read_file. Lees elke bron VOLLEDIG voordat je naar de volgende gaat.
Noteer per bron welke entiteiten je tegenkomt.

**Stap 2 — Extraheer entiteiten per bakje**
Per bron: welke namen, thema's, patronen en uitspraken zijn aanwezig?

Categorieën:
- **Klanten / organisaties** (namen van bedrijven, teams, programma's)
- **Experts / mensen** (namen, rollen, expertise)
- **Thema's** (terugkerende onderwerpen, zorgen, vragen)
- **Jörgens taalpatronen** (uitspraken, framing, verboden woorden, voorkeuren)
- **Methodiek** (frameworks, aanpakken, tools die Minkowski inzet)

**Stap 3 — Tel cross-source frequentie**
Vergelijk de entiteitslijsten. Wat verschijnt in hoeveel onafhankelijke bronnen?

Gebruik deze classificatie:
- ✅✅✅ (3+ bronnen) → sterke kennis-kandidaat
- ✅✅ (2 bronnen) → informatie-kandidaat
- ✅ (1 bron) → data, nog geen actie

**Stap 4 — Schrijf het kennisdraft**
Maak een gestructureerd draft-document met drie secties:

```markdown
## Kennis (3+ bronnen)
Entiteiten en patronen die in alle drie bronnen voorkomen.
Per item: [naam/patroon] — gevonden in: slack ✅ / linkedin ✅ / substack ✅
Aanbeveling: direct integreren in [verbal_identity.md / icp.md / acquisitie_protocol.md]

## Informatie (2 bronnen)
Entiteiten en patronen die in twee bronnen voorkomen.
Per item: [naam/patroon] — gevonden in: [bronnen]
Aanbeveling: bevestig in derde bron of promoveer handmatig

## Data (1 bron)
Opvallende vermeldingen die slechts in één bron staan.
Per item: [naam/patroon] — gevonden in: [bron]
Actie: geen — bewaken of het in volgende scrape-ronde terugkeert
```

**Stap 5 — Sla op via save_note**
Titel: `Kennisdraft_{datum}`
folder_hint: leeg (→ 00_Werkdocumenten)
Inhoud: het draft-document uit stap 4.

## Regels

- Lees elke bron onafhankelijk — geen kruisbestuiving tijdens het lezen
- Rapporteer feiten, geen interpretaties. Schrijf "Red Bull komt voor in 3 bronnen", niet "Red Bull is een belangrijke klant"
- Alle uitvoer in platte Markdown (Aslander: plain text = universele taal)
- Maak GEEN directe aanpassingen aan de bronnenlaag (verbal_identity.md etc.) — dat is menselijk werk
- Als een bakje leeg is of niet gelezen kan worden: meld dit expliciet
