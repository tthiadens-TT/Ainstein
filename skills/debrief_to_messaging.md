# Skill: debrief_to_messaging

## Purpose
Use this skill to read a Client Discovery Debrief (produced by `client_discovery_debrief`) and extract reusable marketing intelligence and communication assets.

This is not a proposal summary. This is market intelligence work.
The job is to translate what was heard in a sales conversation into assets that make Minkowski's marketing smarter and more resonant.

## Input Vereiste

**Deze skill heeft een Client Discovery Debrief als input nodig.**
De debrief wordt geproduceerd door de `client_discovery_debrief` skill (11 vaste secties).

Als er geen debrief aanwezig is — alleen ruwe gespreksaantekeningen — run dan eerst `client_discovery_debrief` en gebruik die output hier als input. Nooit direct van ruwe notes naar marketing-intelligentie springen.

**Haal ook op:**
- `04_Marketing/positioning.md` — om te beoordelen waar de klantframing wél en niet aansluit bij de huidige positionering (dit is wat de "Messaging Gaps" sectie voedt)
- `04_Marketing/verbal_identity.md` — als referentie voor de Minkowski-vertaling in het glossary

## What This Skill Must Not Do
- Rewrite or second-guess the commercial assessment in the debrief
- Produce a proposal or proposal outline
- Invent client facts not present in the debrief
- Use client-identifying information in any external-facing asset without explicit clearance

## What This Skill Must Do
Produce five types of output from every debrief:

### 1. Client Language Glossary
Extract the exact phrases, metaphors, and vocabulary the client used to describe their challenge.
These are gold. They reveal how buyers in this sector or role actually talk about the problems Minkowski solves.

Format:
| Their phrase | What it signals | Minkowski translation |
|---|---|---|
| [verbatim or near-verbatim quote] | [what this reveals about their frame] | [how Minkowski would name this] |

Minimum 3 entries. Do not paraphrase into clean language — the rough edges are the point.

### 2. Pain Point Map
Identify the 2–3 dominant pain points that emerged, and assess how broadly they likely apply.
For each:
- Name the pain point in the client's framing (not Minkowski's)
- Assess: is this specific to this client, or is it a sector/role pattern?
- If it is a pattern: flag it as a content opportunity (this pain point belongs in Minkowski's marketing)

### 3. Audience Framing
Based on the debrief, describe how THIS type of buyer (role + sector + moment) thinks about the problem.
This is not a persona — it is a situational framing:
- What do they believe they already understand?
- What are they underestimating?
- What would make them lean forward in a conversation?
- What would make them dismiss Minkowski instantly?

### 4. Content Opportunities
Based on the debrief, identify 2–4 specific content angles that Minkowski could use.
Each opportunity should be:
- Triggered by something real from the conversation (not generic)
- Expressible as a LinkedIn post, article, email, or talk theme
- Honest about what is assumed vs. sourced

Format:
| Content angle | Asset type | What makes it Minkowski | Proof needed |
|---|---|---|---|
| [The specific tension or insight] | [Post / email / article / talk] | [What Minkowski brings that others don't] | [What evidence would make it credible] |

### 5. Messaging Gaps
Identify where Minkowski's existing messaging would have failed this client.
- Which standard Minkowski claims did NOT resonate (or would not have)?
- Where was the client's frame so different from Minkowski's language that a direct pitch would have missed?
- What needs to be added to the marketing toolkit to reach more clients like this one?

## Operating Rules
1. Work only from the debrief content. Do not invent client details not present in it.
2. Anonymize client-specific references in any external-facing output. Use sector/role framing instead.
3. Flag content opportunities where proof is missing — do not produce content that overclaims.
4. The output of this skill feeds back into `04_Marketing` as a living intelligence layer. Sla de output op als note in `00_Werkdocumenten` met titel "Messaging Intelligence — [sector/rol] — [datum]" zodat patronen over tijd zichtbaar worden.
5. If the debrief is weak (thin notes, missing diagnosis), say so — and name what would make the translation stronger.
6. Koppel terug naar de keten: na deze skill is `create_content` de logische volgende stap als een content opportunity concreet uitgewerkt moet worden. Benoem dit expliciet in je output.

## Quality Check
Before finalizing, ask:
- Does the client language glossary contain phrases that would surprise someone who only knows Minkowski's standard messaging?
- Do the content opportunities feel earned — grounded in what was actually heard?
- Would this output make next month's marketing slightly smarter, or is it generic?
