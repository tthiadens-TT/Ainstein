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
- `01_Clients` for similar proposals, structures, and wording — see Step 0 for how these are actually organized (loose final files, not a subfolder)
- `02_Frameworks & Tools` for methods, formats, and program logic
- `04_Marketing/Pricing` for commercial structure and pricing logic
- `03_Experts` for relevant profiles and staffing options
- `04_Marketing` for proposition language and positioning

Also use:
- client brief
- call notes
- meeting summaries
- deck material
- internal notes

## Proposal Steps

### 0. Retrieve Before Generating (always first)
Before drafting anything, retrieve the finalised, accepted proposals from `01_Clients`. This is the strongest source of proven structure, wording, and pricing logic — reuse it before generating anything new.

**Where to look:** `01_Clients` is mostly flat — client subfolders exist but the real proposals sit as loose files in the folder itself, not in a `Proposals` or `Outcomes` subfolder (those are empty scaffolding, not populated). Identify final proposals by filename pattern: contains `FINAL`, `Proposal`, or `Voorstel` (e.g. `Proposal NN Lead4 by Minkowski FINAL.md`, `Voorstel NN Retail Schade en Zorg FINAL.md`). A finalised proposal is 95–100% of the truth for what was actually agreed — design-phase deltas are usually minor nuance, not a reason to skip it.

**How to search:** search `01_Clients` for the same or an adjacent client/sector first. If nothing matches, broaden to any final proposal with a similar module logic or program type.

**What to do with what you find:** use it as the reference structure, wording, and pricing baseline. Generate only what cannot be retrieved — a genuinely new module, a client-specific angle, or content that doesn't exist yet in any prior proposal. Do not regenerate from scratch what a finalised proposal already solved.

**If nothing relevant exists:** say so explicitly before proceeding — this is a signal the source layer is thin for this case, not a reason to invent confident-sounding boilerplate.

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

### 3. Confirm Reusable Elements
Building on Step 0, confirm what from the retrieved final proposal(s) actually fits this case:
- similar client situations
- reusable proposal structures
- recurring module logic
- strong phrasing
- proof points or framing worth reusing

Reuse first. Only generate from zero what Step 0 did not surface.

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
