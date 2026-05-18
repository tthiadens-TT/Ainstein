# Skill: refine_proposal

## Purpose
Process open comments on a Google Doc proposal draft.
For each comment: read the quoted section, understand the feedback,
rewrite that section in Minkowski voice, write it back to the doc,
and resolve the comment with a one-line summary reply.

## When to Use
Use this skill when the user shares a Google Doc ID or URL and asks to:
- "verwerk de comments"
- "update de doc"
- "refine comments"
- "verwerk de feedback"
- or similar phrasing that refers to processing Google Doc comments

## Steps

### 1. Get the doc_id
Extract the doc_id from whatever the user provided (full URL or raw ID).
If no doc_id is given, ask: "Kun je het Google Doc ID of de link naar het voorstel delen?"

### 2. Read all open comments
Call `read_doc_comments(doc_id)` to retrieve all unresolved comments.
Each comment has: `id`, `quoted_text`, `content` (the feedback), `author`, `date`.

If `total_comments == 0`:
- Say: "Er zijn geen open comments op dit document. Is het voorstel klaar? Gebruik `/export-deck [doc_id] [klantnaam]` om de PPTX te genereren."
- Stop.

### 3. Read the full document
Call `read_file` on the Google Doc to get the full text — this gives context for rewrites.
If reading fails, continue with only the quoted text from each comment.

### 4. Process each comment
For each open comment:

**a. Understand the feedback**
Read `quoted_text` (the highlighted section) and `content` (the comment itself).
If the comment is too vague to act on ("maak dit beter", "verbeter dit"):
- Post in Slack: "Comment van [author]: '[content]' is te vaag om te verwerken. Kun je specifieker zijn?"
- Skip this comment (do not resolve it).

**b. Rewrite the section**
Rewrite the `quoted_text` incorporating the feedback. Rules:
- Stay in Minkowski voice: scherp, concreet, commercieel, niet generiek
- Keep roughly the same length unless the feedback asks for more or less
- Do not rewrite adjacent sections — only the quoted text
- Use the full document context to stay coherent

**c. Write the rewrite back**
Call `update_gdoc_section(doc_id, old_text=quoted_text, new_text=rewrite)`.

If `status == "not_found"`:
- Do not resolve the comment
- Report in the Slack summary: "⚠️ Sectie niet gevonden in de doc — mogelijk al gewijzigd. Herschreven tekst:\n[rewrite]"
- Continue with the next comment

**d. Voeg een reply toe aan het comment (resolvet het NIET)**
Call `resolve_doc_comment(doc_id, comment_id, reply_text="✅ Herschreven: [1-zin samenvatting van de aanpassing]")`.

Belangrijk: de `action` in de reply moet "reply" zijn, niet "resolve". Thomas resolvet de comments zelf in Google Docs nadat hij de wijziging heeft gezien.
Gebruik reply_text als: "✅ Herschreven: [korte samenvatting]. Controleer de wijziging en resolvet dit comment zelf."

### 5. Post Slack summary
After processing all comments, post a structured summary:

```
*Voorstel bijgewerkt — [X] van [Y] comments verwerkt*

✅ *Context* (comment van Thomas)
Oud: "[eerste 80 tekens van quoted_text]…"
Nieuw: "[eerste 80 tekens van rewrite]…"

✅ *Commercial Notes* (comment van Thomas)
Oud: "…"
Nieuw: "…"

⚠️ [sectienaam] — niet gevonden in de doc. Zie herschreven tekst hierboven.

❓ [sectienaam] — comment te vaag, overgeslagen. Verduidelijking nodig.

📄 Doc: [Google Docs link]
```

## Operating Rules
- **Only touch sections with a comment.** Do not rewrite anything else.
- **If a comment is vague, skip and report** — never guess at the intent.
- **If update fails (text not found), always show the rewrite** so Thomas can paste it manually.
- **Resolve comments only after a successful update.** Never resolve a comment for a failed update.
- **Minkowski voice always:** sharp, grounded, commercially relevant, specific. Not generic.
- **One rewrite per comment.** Do not chain rewrites without re-reading the doc.

## Quality Check
Before posting the summary, ask:
- Are all rewrites sharper and more specific than the original?
- Do they still sound like Minkowski — not like a generic agency?
- Is every change traceable in the summary?
