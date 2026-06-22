# Ainstein Backlog

*Bijgewerkt: 21 juni 2026*
*Beheerd door: Claude Code + Thomas — elke sessie bijwerken*

Dit is de centrale backlog voor Ainstein. Alle openstaande items — acties, bugs, ideeën, todo's — staan hier met context en prioriteit. Niet in CLAUDE.md (dat is sessiememorie), niet in losse documenten.

**Gebruik:**
- Begin elke sessie: dit bestand lezen (Session Start Protocol stap 3)
- Sluit elke sessie af: dit bestand bijwerken
- Afgerond item: verplaatsen naar ✅ Gedaan, niet verwijderen

---

## 🔴 Actief probleem

**Geen actief blokkerend probleem op dit moment.**

*Kennis-laag contextprobleem opgelost — run van 21 juni 2026 succesvol afgerond.*

---

## 🟡 Volgende stap (prioriteit 1)

### 08_Outcomes vullen — meest urgente actie
**Wat:** Concrete win/loss-records toevoegen aan `08_Outcomes` in Drive.
**Waarom:** De kennis-laag run van 21 juni 2026 bevestigde dit expliciet als de grootste blinde vlek: Ainstein heeft instructie om `08_Outcomes` te raadplegen bij elk voorstel, maar de map is leeg. Commerciële lessen gaan verloren.
**Concrete lessen die nu wegvallen:**
- NN IC — gewonnen (mei 2026): wat werkte, welke argumentatie, welk tarief
- Cathalijne — verloren op tarief bij Pierre: wat was het gat, wat had anders gekund
**Actie Thomas/Jörgen:** deze twee cases invullen. Vijf minuten werk, directe waarde voor Ainstein bij elk volgend voorstel.

---

## 📋 Backlog

### 1. CLAUDE.md uitbreiden — niet-gedocumenteerde features
**Wat:** Meerdere features zijn geïmplementeerd maar ontbreken volledig in CLAUDE.md (sessiememorie). Ainstein weet dus niet dat ze bestaan.
**Ontbrekend:**
- `pptx_builder.py` — Minkowski-branded PPTX builder (meerdere brand-fixes, actief)
- `create_report_doc.py` — geformateerde Google Docs rapporten
- `skills/meeting_reviewer.md` — onafhankelijke meeting-review naast Jamie
- `skills/extract_knowledge.md` + `extract_knowledge_distilleer.md` + `extract_knowledge_merge.md` — kennis-laag skills
- `list_recent_files` tool in `tools.py` — recente Drive-bestanden opvragen
**Waarom:** gebouwd in lokale sessies, nooit gedocumenteerd in CLAUDE.md. Beter doen in lokale sessie (meer context beschikbaar).
**Actie:** lokale sessie starten, bestanden lezen, CLAUDE.md aanvullen.

### 2. Lokale sessie-audit — 25+ sessies doorzoeken
**Wat:** Thomas heeft 25+ lokale Claude Code-sessies die niet toegankelijk zijn vanuit remote omgevingen. Deze sessies bevatten mogelijk open items, beslissingen en features die niet zijn vastgelegd.
**Waarom:** de sessie-audit van 21 juni 2026 was onvolledig — slechts 11 van de 25+ sessies waren leesbaar. Resterende sessies (bijv. "Outstanding tasks review", "Set up external agent audit", "Optimize query speed with indexing", "Add GitHub logging for non-code events") kunnen open werk bevatten.
**Actie Thomas:** lokale sessie starten met instructie: "Lees alle sessiebestanden in dit project, extraheer open items, werk roadmap bij."

### 3. Kennis-laag automatiseren
**Wat:** `run_kennisextractie.py` automatisch laten draaien via GitHub Actions scheduling.
**Waarom:** nu handmatig op VM — niet schaalbaar.
**Trigger (nog niet bereikt):** ≥1 promotie van kennis naar bronnenlaag door Thomas/Jörgen, óf een say-vs-sell-gat dat aantoonbaar tot een commerciële actie heeft geleid.
**Status:** run van 21 juni geslaagd, fix gevalideerd. Evidence-bar nog niet gehaald.

### 4. Kennis terugkoppeling naar bronnenlaag
**Wat:** mechanisme om geëxtraheerde kennis te bevorderen naar de vaste bronnenlaag (01–08) na handmatige bevestiging.
**Waarom:** nu blijft kennis in `06_Marketing/_kennis/kennis_laag.md` — losgekoppeld van de bronnenlaag die Ainstein gebruikt bij voorstellen en matching.
**Aanpak nog open:** mens promoot handmatig, of Ainstein leest `kennis_laag.md` mee bij elke aanroep.

### 5. Webhook URL upgraden naar `webhook.minkowski.nl`
**Wat:** DuckDNS-URL vervangen door professioneel Minkowski-domein.
**Aanpak:** A-record `webhook.minkowski.nl → 35.253.206.86` toevoegen + certbot opnieuw uitvoeren (nginx config hoeft niet aan).
**Blokkade:** Thomas heeft nog geen toegang tot het Minkowski domein.

### 6. Ainstein voert acties zelf uit na Slack-bevestiging
**Wat:** als Thomas/Jörgen "doe het maar" zegt in Slack, voert Ainstein de actie direct uit — bijv. `build_proposal` starten, expert zoeken, notitie aanmaken.
**Waarom:** nu stelt Ainstein voor en stopt — de vervolgstap is nog steeds handmatig.
**Architectuur:** Slack-reactie triggert vervolgactie via bestaande skill-flow. Complex — aparte sessie.

### 7. Prompt Coaching praktijktest
**Wat:** valideren of de Prompt Coaching sectie (brain.md) in de praktijk werkt.
**Waarom:** geïmplementeerd (commit `05ed433`) maar nooit geëvalueerd op effectiviteit.
**Actie Thomas/Jörgen:** testen met vage vragen in Slack, beoordelen of de coaching scherp en nuttig is.

### 8. Bug: `slack_nn-schade-inkomen_2026-05.md` onleesbaar
**Wat:** dit bestand is onleesbaar in twee onafhankelijke bronnen (Slack-scraper + Jamie). Structureel technisch probleem dat herhaling laat zien.
**Waarom:** als scraper-bestanden stelselmatig onleesbaar zijn, mist Ainstein bronmateriaal bij kennisextractie.
**Actie:** bestand inspecteren op VM, scraper-output checken op encoding/formaat-fouten.

### 9. Prompt Coaching format fixen
**Wat:** "max 4 regels" limiet in brain.md conflicteert met het vereiste formaat (divider + header + zin + blockquote = al 4 regels minimaal).
**Prioriteit:** laag — werkt in de praktijk, is een detail.
**Actie:** limiet versoepelen of coaching-blok compacter maken.

### 10. Say-vs-sell gaten adresseren
**Wat:** de kennis-laag run van 21 juni 2026 identificeerde concrete communicatiegaten. Dit zijn beslissingen voor Thomas/Jörgen, geen technische items.
**Gevonden gaten (verkocht, niet verkondigd):**
- NN Group als ankerklant — 300+ deelnemers, multi-year commitment, nauwelijks zichtbaar in publieke communicatie
- Wheel of Reasoning — consequent ingezet in programma's, volledig afwezig in Jörgens publieke communicatie
- Agentic AI als leiderschapsthema — intern aanwezig (LEAD3), niet uitgewerkt als publieke positie
**Gevonden drift (verkondigd, verdwijnend):**
- "Making history by changing the future" — actief (2021–2023) → afwezig (2026). Bewust besluit of stille drift?
- Duurzaamheid/klimaat — aanwezig in publieke communicatie 2021–2023, niet meer zichtbaar in 2026
**Actie Jörgen/Thomas:** beslissen welke gaten geadresseerd worden en in welk medium.

---

## ✅ Gedaan (archief)

| Item | Commit/PR | Datum |
|---|---|---|
| Ainstein Slack bot (SocketMode) | live | — |
| 08_Outcomes setup (win/loss geheugen) | `8425f0b` | — |
| Wekelijkse Drive backup | `39cd42d` | — |
| Rate limiting (max 10 calls/uur per user) | `3c8f264` | — |
| Block Kit formatting voor Slack | `b689c18` | — |
| Feedback loop (gaps.md in prompts, auto-review #ainstein-status) | live | — |
| Plan A: Prompt Coaching | `05ed433` | mei 2026 |
| Web search via Tavily + DDGS fallback | `7154a08` | mei 2026 |
| Dynamic Slack user lookup (vervangt MINKOWSKI_STAFF_MAP) | `cf18ff4` | mei 2026 |
| Vision/image support (JPEG/PNG) | `110b681` | mei 2026 |
| Kennis-laag bewijs-fase (scrapers + extractie in `scripts/`) | `1a3820a` e.a. | mei/juni 2026 |
| Kennis-laag REDUCE fix (timeout 900s, max_tokens 32k, resumability) | `1a3820a` | 21 juni 2026 |
| Plan B: Jamie webhook pipeline | PR #27 | mei 2026 |
| Ainstein karakter-update (uitdager/denkpartner) | PR #28 | 16 juni 2026 |
| Jamie meeting test (Hei-dag Waardestromen) — DM + taakreview werkt | live | 21 juni 2026 |
| Backlog centraliseren (dit bestand) | zie commit | 21 juni 2026 |
| Kennis-laag contextprobleem opgelost — fix gevalideerd via volledige run | `1a3820a` | 21 juni 2026 |
| Kennis-laag volledige run + beoordeling — alle 10 bronnen verwerkt, `kennis_laag.md` bijgewerkt | live op VM | 21 juni 2026 |
| Kennis-laag map-reduce fix — niet nodig gebleken, huidige architectuur voldoet | — | 21 juni 2026 |
