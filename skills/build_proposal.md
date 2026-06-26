# Skill: build_proposal

## Purpose
Use this skill when someone needs help creating, structuring, rewriting, or improving a proposal.

The goal is not to generate a generic agency proposal.
The goal is to build a proposal that is recognizably Minkowski:
- sharp in diagnosis
- relevant in design
- credible in setup
- clear in value
- commercially usable

## Minkowski Voice — schrijf altijd zo

**Taal:** Voorstellen altijd in het **Engels**, tenzij de klant expliciet om Nederlands vraagt of de volledige context (brief, mails, eerder contact) Nederlands is. Bij twijfel: Engels.

**Vier schrijfpatronen:**

1. **Observatie → Vraag → Herkadert** — open met een concrete observatie, stel die open, sluit met een perspectief-verschuiving. Nooit abstract vóór concreet.
   > *"Although we can't predict the future, we can influence it."*

2. **Persoonlijk → Universeel** — begin bij een mens of moment, verbreedt dan. Generalisaties komen altijd ná een concreet geval.
   > *"A plan is just a starting point. The real difference is made by the people who bring it to life."*

3. **Korte bewering. Dan nuance.** — de stelling staat in de eerste zin. Geen inleidingen.
   > *"From possibility to capability."*
   > *"Our programs turn plans into action."*

4. **Programma-verhaal: what happened, what shifted** — beschrijf wat er in de zaal gebeurt, niet wat de agenda is. Uitkomsten zijn gedragsveranderingen, geen activiteiten.
   > *"We design learning experiences not as linear programs, but as environments where people can step into possibility."*

**Gebruik deze woorden:**
futures-ready · decision · signal · scenario · learning experience · programme · faculty · room · ritual · reframe · cone of possibilities · sense-making · act without certainty · backwards planning · prototyping futures

**Vermijd deze woorden:**
future-proof · thought leadership · disruptive · journey · synergy · unlock · empower · best-in-class · training · workshop · cursus · roadmap · actieplan · adaptief · toekomstbestendig

**Schrijfregels:**
- Begin met de klantuitdaging, niet met wie Minkowski is.
- Bullets zijn uitkomsten (welk gedrag na afloop), geen activiteiten.
- Meer "jij/jullie" dan "wij/ons".
- Als een tekst geen risico op tegenspraak oplevert, is hij te veilig.

---

## When to Use
Use this skill when the request includes questions like:
- Can you draft a proposal?
- Which previous proposal should we reuse?
- How should we structure this offer?
- What should the narrative be?
- Which modules or elements fit this challenge?
- Can you improve this draft?

## Inputs to Retrieve
Retrieve from:
- `01_Proposals` for similar proposals, structures, and wording
- `02_Tools` for methods, formats, and program logic
- `03_Pricing` for commercial structure and pricing logic
- `04_Experts` for relevant profiles and staffing options
- `06_Marketing` for proposition language and positioning

Also use:
- client brief
- call notes
- meeting summaries
- deck material
- internal notes

## Proposal Steps

### 1. Define the Core Problem
Clarify:
- what problem the client is actually trying to solve
- what sits underneath the stated ask
- what change the proposal should help unlock

Write this in clear commercial language.

### 2. Define the Minkowski Angle
Explain why Minkowski is relevant here.

Make explicit:
- which part of the Minkowski offer matters most
- where Minkowski is distinctive
- why this is not a generic training, workshop, or strategy process

### 3. Retrieve Reusable Elements
Search for:
- similar client situations
- reusable proposal structures
- recurring module logic
- strong phrasing
- proof points or framing worth reusing

Reuse first. Do not start from zero unless necessary.

### 4. Shape the Offer
Propose a structure for the offer:
- objective
- program logic
- sessions, modules, or workstreams
- expert and facilitator setup
- expected outcomes
- optional add-ons
- assumptions and boundaries

### 5. Pressure-Test the Draft
Challenge the proposal on:
- clarity
- distinctiveness
- credibility
- scoping
- commercial logic
- repetition
- vagueness
- overpromising
- weak outcome framing

### 6. Improve for Decision-Making
Make sure the proposal helps the buyer decide.

Strengthen:
- why now
- why Minkowski
- why this approach
- what this leads to
- what happens next

### 7. DVV-Toets (altijd uitvoeren vóór oplevering)

Loop het voorstel door op drie assen. Corrigeer wat niet scoort — noteer in je output welke punten zijn aangepast.

**D — Duidelijk**
- Korte, actieve zinnen? Geen passieve constructies?
- Geen jargon of afkortingen zonder uitleg?
- Begrijpt iemand buiten Minkowski dit onmiddellijk?

**V — Volledig**
Beantwoordt het voorstel alle vijf beslissersvragen?
1. Wat is de aanpak? (programmalogica, fasering)
2. Wie doet wat? (team, experts, rollen)
3. Hoe lang duurt het? (doorlooptijd, planning)
4. Wat kost het? (investering, opbouw, aannames)
5. Wat levert het op? (uitkomsten, gedragsverandering, volgende stap)

Ontbreekt een van deze vijf: vul aan of leg expliciet uit waarom het er niet in zit.

**V — Verleidelijk**
- Staat de klant centraal? Meer "jij/jullie" dan "wij/ons"?
- Begint het voorstel met de klantuitdaging, niet met wie Minkowski is?
- Zijn uitkomsten concreet (welk gedrag of welke situatie na afloop) — niet abstract ("meer bewustzijn", "betere samenwerking")?

Als een letter niet scoort: herstel die zwakte. Lever het voorstel niet op voordat de DVV-toets klopt.

## Output Format
Use one of these depending on the request:
- proposal outline
- first full draft
- rewrite of specific sections
- comparison of options
- proposal improvement notes

Default structure:

### Context
Short summary of the client context and challenge.

### Proposal Logic
What the proposal is trying to do and why this setup fits.

### Recommended Structure
Outline of the program or offer.

### Team / Expert Setup
Which people or role types are needed and why.

### Commercial Notes
Pricing logic, assumptions, or boundaries if relevant.

### Risks / Weak Spots
What still needs sharpening.

### Draft Text
If requested, provide draft wording.

## Operating Rules
- Do not produce empty agency language.
- Prefer strong structure over decorative language.
- Be specific about outcomes.
- Reuse proven logic where possible.
- Flag weak differentiation or fuzzy scope.
- If the source layer is thin, say so.

## Quality Check
Before finalizing, ask:
Would this proposal help Minkowski win the right work, or does it still sound like it could belong to anyone?

## After Generating a Draft
Once you have produced a full proposal draft, always:
1. Call `create_gdoc` with an appropriate title (e.g. "Voorstel [Client] [Opportunity]") and the full draft text as content.
2. Post the Google Doc URL in Slack with a short message, e.g.:
   "Voorstel-draft staat klaar: [URL]. Voeg comments toe op secties die je wilt aanscherpen, dan typ je `/refine-comments [doc_id]`."

Do not skip this step. The Google Doc is the working format for all further refinement.
