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

### Kennis-laag contextprobleem — status: gedeeltelijk opgelost
**Wat:** `scripts/run_kennisextractie.py` faalt bij grote datasets door contextoverstijging (267k+ chars bij iteratie 4-5).
**Al gedaan (commit `1a3820a`):**
- REDUCE timeout: 180s → 900s configureerbaar
- REDUCE max_tokens: 16.000 → 32.000
- Resumability: MAP slaat distillaties op naar temp-JSON; `--reduce-from <pad>` herstart alleen REDUCE
**Wat nog open is:** onduidelijk of 267k+ chars in de MAP-fase volledig is opgelost, of dat het nu gewoon langer duurt (timeout) en afbreekt. Volgende keer dat de extractie draait: checken of alle bronnen foutloos verwerkt worden.
**Volgende actie:** één volledige run uitvoeren op de VM en het resultaat beoordelen.

---

## 🟡 Volgende stap (prioriteit 1)

### Kennis-laag volledige run + beoordeling
**Wat:** `python3 scripts/run_kennisextractie.py` draaien op de VM, alle bronnen verwerken, resultaat in `06_Marketing/_kennis/kennis_laag.md` beoordelen.
**Waarom:** bevestigen dat de fix in `1a3820a` het contextprobleem daadwerkelijk oplost. Als het nog steeds vastloopt → dan pas map-reduce per bron bouwen.
**Actie Thomas:** run uitvoeren, resultaat delen.

---

## 📋 Backlog

### 1. Kennis-laag map-reduce fix (indien nodig)
**Wat:** als de volledige run nog steeds vastloopt op 267k+ chars → ombouwen naar extractie per bron als losse stap, daarna één synthese-aanroep.
**Waarom:** de huidige fix (timeout/max_tokens) lost het symptoom op maar niet de architectuuroorzaak.
**Status:** wacht op resultaat volledige run — misschien niet nodig.

### 2. Kennis-laag automatiseren
**Wat:** `run_kennisextractie.py` automatisch laten draaien via GitHub Actions scheduling.
**Waarom:** nu handmatig op VM — niet schaalbaar.
**Trigger:** na evidence-bar: ≥1 promotie door Thomas/Jörgen, of een say-vs-sell-gat dat tot actie heeft geleid.
**Vereist:** #1 (volledige run gevalideerd) eerst.

### 3. Kennis terugkoppeling naar bronnenlaag
**Wat:** mechanisme om geëxtraheerde kennis te bevorderen naar de vaste bronnenlaag (01–08) na handmatige bevestiging.
**Waarom:** nu blijft kennis in `06_Marketing/_kennis/kennis_laag.md` — losgekoppeld van de bronnenlaag die Ainstein gebruikt bij voorstellen en matching.
**Aanpak nog open:** mens promoot handmatig, of Ainstein leest `kennis_laag.md` mee bij elke aanroep.

### 4. 08_Outcomes vullen
**Wat:** NN Group voorstel toevoegen als eerste win/loss record.
**Waarom:** `08_Outcomes` is ingericht maar leeg. Ainstein heeft instructie om het te raadplegen bij elk voorstel — maar als het leeg is, is die waarde nul.
**Actie Thomas/Jörgen:** NN Group voorstel toevoegen (gewonnen of verloren, met context waarom).

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
| Kennis-laag bewijs-fase (scrapers + extractie in `scripts/`) | `1a3820a` e.a. | mei/juni 2026 |
| Kennis-laag REDUCE fix (timeout 900s, max_tokens 32k, resumability) | `1a3820a` | 21 juni 2026 |
| Plan B: Jamie webhook pipeline | PR #27 | mei 2026 |
| Ainstein karakter-update (uitdager/denkpartner) | PR #28 | 16 juni 2026 |
| Jamie meeting test (Hei-dag Waardestromen) — DM + taakreview werkt | live | 21 juni 2026 |
| Backlog centraliseren (dit bestand) | zie commit | 21 juni 2026 |
