# Fable-brief: Proposal Engine 2.0 (idee 1 uit de Fable-sessie, 6 juli 2026)

*Geschreven door Claude Fable 5 als orchestratie-architect, vlak voor het sluiten van het Fable-window (7 juli 2026). Dit document is een zelfstandig uitvoerbare spec: een latere Opus- of Sonnet-sessie moet hiermee kunnen bouwen zonder de oorspronkelijke Slack-thread of Fable-sessie als context.*

## Wat & Waarom

**Wat:** een autonome, meertraps voorstel-pipeline. Input: een briefing (Slack-bericht, doc of debrief). Output: een revisie-klaar voorstel als Google Doc, gepost in Slack. De pipeline splitst het werk in vijf losse stappen met elk een eigen, kleine context, in plaats van één lange agent-loop die alles tegelijk doet.

**Waarom:** de huidige `build_proposal`-skill draait in één `run_agent`-call (max 15 iteraties, 8k output-tokens). Eén context doet retrieval, schrijven én zelfkritiek. Dat geeft drie structurele zwaktes: (1) de kritiek is niet onafhankelijk, dezelfde context die schreef beoordeelt zichzelf mild; (2) lange bronnen verdringen elkaar in het contextvenster; (3) kwaliteit varieert per run zonder dat een stap het opvangt. Het map-reduce patroon dat dit oplost is in dit project al bewezen: `run_kennisextractie.py` (distilleer per bron, merge daarna).

**Kernprincipe (uit de Fable-sessie):** het duurste model denkt en toetst, lichtere modellen voeren uit. Tokendiscipline is een ontwerpeis, geen bezuiniging achteraf.

## Architectuur

```
Briefing (Slack / doc / debrief sectie 11)
        │
  [1] INTAKE (Haiku)          — parse brief, ICP-toets (icp.md), klantdossier identificeren,
        │                        go/no-go. Bij no-go: stop met uitleg. Sub-dossier-regel
        │                        respecteren (LEAD3 vs. Inkomen Collectief binnen NN Group).
  [2] RETRIEVAL (Sonnet, parallel per bron)
        │                      — 4 parallelle distillatie-calls, elk leest één bronsoort en
        │                        levert een compact "evidence pack" (max ~2k tokens per pack):
        │                        a. 01_Clients/<klant>/Outcomes + eerdere voorstellen
        │                        b. vergelijkbare voorstellen bij andere klanten (zelfde vraagtype)
        │                        c. 04_Marketing/Pricing (letterlijke prijslogica, met bron-ID)
        │                        d. 03_Experts decision layer (expert-shortlist voor dit vraagtype)
  [3] DRAFT (Sonnet)           — build_proposal.md-skill + de evidence packs (NIET de ruwe
        │                        documenten). Volledige conceptversie.
  [4] ADVERSARIAL REVIEW (beste beschikbare model, verse context)
        │                      — aparte call die het concept sloopt: DVV-toets, beide merklagen
        │                        (Brand CORE = verbal_identity.md stijlregels én Brand FACTS =
        │                        brand_core.md feitelijke identiteit; sinds 6 juli 2026 beide
        │                        onvoorwaardelijk geïnjecteerd in run_agent, dus op run_agent
        │                        gebouwde stappen erven ze automatisch), positionering,
        │                        eigenaarschapslabels ([Klant]/[Minkowski]/[Nog te bepalen]),
        │                        audit op verzonnen cijfers (elke prijs moet traceren naar
        │                        pack c). Output: genummerde revisie-eisen.
  [5] REVISE & SHIP (Sonnet)   — verwerk revisie-eisen, doc aanmaken UITSLUITEND via
                                 create_gdoc() (het gebrande pad met _apply_basic_formatting:
                                 Helvetica Neue, koppen #287093), Slack-post met doc-URL en de
                                 bekende /refine-comments vervolgroute. Introduceer nooit een
                                 tweede doc-creatieroute: de Meeting Notes-bug van 6 juli 2026
                                 (f605536) ontstond precies zo, via een parallel pad
                                 (create_doc_via_drive) dat de formatting-stap miste.
```

## Ontwerpbeslissingen en waarom

1. **Evidence packs in plaats van ruwe bronnen naar de draft-stap.** De draft-context blijft klein en de herkomst van elke claim is traceerbaar (elk pack vermeldt bron-bestand + Drive-ID). Dit is dezelfde reden waarom de kennisextractie map-reduce werd: één bron per context, nooit overflow.
2. **De review-stap krijgt een verse context en het beste model.** Onafhankelijkheid is het punt. De reviewer ziet het concept, de packs en de merkregels, maar niet het denkproces van de schrijver. Dit is de stap waar kwaliteit wordt gewonnen; hier niet op besparen.
3. **Prijzen alleen letterlijk uit pack c.** De bekende foutmodus (regel 1 en 9 van de Operating Rules: nooit cijfers verzinnen) wordt afdwingbaar: de reviewer verwerpt elke prijs zonder bronvermelding. Staat er niets in Pricing voor dit vraagtype, dan zegt het voorstel dat expliciet.
4. **Checkpointing per stap vanaf dag één.** Elke stap schrijft zijn output naar `logs/proposal_runs/<run_id>/stap<N>.json`. Een run die faalt in stap 4 herstart met `--resume-from 4`. Les uit het geheugen: resumability vroeg inbouwen in dure meertraps-pipelines, niet achteraf.
5. **Triggers, in volgorde van bouwen:** (a) handmatig Slack-commando (bv. `/voorstel <briefing>` of mention), (b) automatisch wanneer `client_discovery_debrief` sectie 11 een voorstel aankondigt (bestaand roadmap-item), (c) Jamie-meeting met expliciete voorstel-actie. Begin met (a); (b) en (c) zijn dezelfde pipeline met een andere ingang.

## Implementatieplan met model-toewijzingen

| Stap | Werk | Model (uitvoering) | Omvang |
|---|---|---|---|
| B1 | `scripts/proposal_engine.py`: orchestrator met de 5 stappen, checkpointing, `--resume-from` | Sonnet bouwt, mens/hoofdsessie reviewt | ~1 dag |
| B2 | Nieuwe skills: `proposal_intake.md` (stap 1) en `proposal_review.md` (stap 4); `build_proposal.md` blijft ongewijzigd de draft-skill | Sonnet schrijft, hoofdsessie scherpt | half dagdeel |
| B3 | Retrieval-distillatie prompts (stap 2a-d) als aparte skill-bestanden, elk met vast output-schema (evidence pack) | Sonnet | half dagdeel |
| B4 | Slack-ingang: commando-handler in `slack_app.py` die de orchestrator start en voortgang per stap in een thread post | Sonnet | half dagdeel |
| B5 | Testset: 2 historische briefings (bv. een gewonnen en een verloren case) end-to-end draaien, output vergelijken met het echte voorstel | hoofdsessie + Thomas | 1 dagdeel |

Runtime-modellen binnen de pipeline: stap 1 Haiku, stap 2/3/5 Sonnet, stap 4 het beste beschikbare model (nu Opus 4.8; was dit window Fable geweest).

## Risico's en mitigaties

- **Evidence pack mist het beslissende document** (Drive-zoeken is onbetrouwbaar via connectors, maar het serviceaccount-pad op de VM werkt al maanden stabiel; de pipeline draait op de VM, dus dit risico is klein). Mitigatie: retrieval-stappen loggen wélke bestanden gelezen zijn; het voorstel eindigt met een bronnenlijst.
- **Kosten per run.** Vijf stappen met parallelle retrieval is duurder dan één call. Meet per stap (trace zit al in `run_agent`); als stap 2 te duur wordt, cache evidence packs per klant en ververs alleen bij nieuwe documenten.
- **Autonomie versus controle.** Aanname uit de oorspronkelijke Ainstein-sessie die nog getoetst moet worden bij Jörgen/Thomas: wil Minkowski een volautomatisch concept, of altijd een menselijke tussenstop na stap 1 (go/no-go)? Bouw de tussenstop als vlag (`--auto` / interactief), beslis daarna op basis van gebruik.

## Succescriteria

1. Een briefing van 10 regels levert binnen ~10 minuten een Google Doc-concept op dat de DVV-toets aantoonbaar heeft doorstaan (reviewer-verslag als bijlage in de thread).
2. Elke prijs en elk expertnoemer in het concept traceert naar een bronbestand.
3. Thomas' redactietijd per voorstel daalt merkbaar (nulmeting: huidige tijd per voorstel vastleggen vóór de bouw).
4. De pipeline is herstartbaar op elke stap zonder de vorige stappen opnieuw te betalen.
