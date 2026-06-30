# Skill: match_experts

## Purpose
Use this skill when someone needs help selecting, comparing, or recommending experts, facilitators, or faculty members for a proposal, program, or client challenge.

The goal is to make expert selection more deliberate, comparable, and scalable.

## When to Use
Use this skill when the request includes questions like:
- Which experts fit this challenge?
- Who should be in the room?
- Which facilitator profile do we need?
- Can you shortlist strong options?
- Are we overusing the same people?
- What expertise is still missing?

## Inputs to Retrieve

**Start altijd hier — in deze volgorde:**
1. `03_Experts/minkowski_decision_layer.json` — gestructureerde index: expertise per expert, rollen, sectoren. Gebruik dit voor de eerste filtering voordat je individuele profielen leest.
2. `03_Experts/minkowski_team_profiles_index.json` — profielen-index met kerncompetenties en trefwoorden.
3. `03_Experts/Minkowski_AI_Assistant_Selection_Logic.docx` — de selectiecriteria die Minkowski hanteert. Raadpleeg dit als je twijfelt over rol-fit of combinaties.
4. Individuele `03_Experts/<naam>_Profile.docx` — voor de shortlist: lees het volledige profiel van elke kandidaat die je serieus overweegt. Er zijn 18 individuele profielen beschikbaar.
5. `03_Experts/00_Minkowski_Team_Profiles_Overview.docx` — teamoverzicht als contextuele aanvulling.

**Conditioneel ophalen:**
- `01_Clients` — voor voorbeelden van eerdere expert-combinaties in vergelijkbare opdrachten
- `02_Frameworks & Tools` — als het format of de methode het type expert bepaalt (b.v. Wheel of Reasoning vraagt een specifiek facilitatieprofiel)
- `04_Marketing` — als team-positionering commercieel relevant is in een voorstel

**Gebruik ook:**
- Client brief, programma-doelstelling, doelgroep, sessieformat, gewenste toon of geloofwaardigheidsniveau

## Matching Steps

### 1. Clarify the Need
Define:
- what the client challenge is
- what the session or program needs to achieve
- what kind of role is needed
- whether the need is content, facilitation, credibility, experience design, or a mix

### 2. Translate Need into Role Types
Break the need into role categories such as:
- lead facilitator
- subject-matter expert
- challenger
- storyteller
- experience facilitator
- strategic translator
- creative perspective
- credibility anchor

### 3. Retrieve Relevant Profiles
Search and shortlist people based on:
- expertise fit
- relevance to the challenge
- experience level
- fit with audience
- likely chemistry with the setup
- distinctiveness in a proposal context

### 4. Compare and Assess
For each strong option, assess:
- what they clearly add
- where they are strongest
- where they are less ideal
- whether they fit as lead, support, or specialist
- whether the same function could be covered by someone else

### 5. Flag Gaps and Risks
Flag issues such as:
- missing expertise
- too much overlap
- dependence on one familiar person
- weak diversity of perspective
- strong content fit but weak delivery fit
- good proposal optics but weak practical relevance

### 6. Recommend a Team Shape
Propose:
- ideal setup
- lean setup
- backup option if relevant

## Output Format

### Need Summary
What kind of expertise or facilitation the situation really requires.

### Recommended Roles
Which role types are needed.

### Shortlist
For each person:
- Name
- Best role
- Why they fit
- Strength
- Watch-out

### Team Recommendation
Recommended combination with rationale.

### Gaps or Risks
What is still missing or fragile.

## Operating Rules
- Match to the real need, not only to familiar names.
- Separate content expertise from facilitation capability.
- Do not recommend someone only because they are prominent.
- Be explicit when the source layer is too thin for confident matching.
- Help the user understand trade-offs, not just names.

## Quality Check
Before finalizing, ask:
Have I made expert selection more deliberate, more scalable, and less dependent on intuition alone?
