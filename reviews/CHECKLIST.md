# Ainstein Code Review Checklist

Gebruik dit naast de standaard `/review` skill. Ainstein-specifieke aandachtsgebieden die in generieke reviews niet vanzelf naar boven komen.

---

## 1. Drive API correctheid

- [ ] Zijn Drive queries recursief als dat nodig is? (`'{fid}' in parents` = alleen directe kinderen)
- [ ] Worden `supportsAllDrives=True` en `includeItemsFromAllDrives=True` meegegeven voor Shared Drive calls?
- [ ] Wordt `parentId` altijd expliciet opgegeven bij `create_file`? (weglaten → root Drive)
- [ ] Worden Drive-binaire bestanden (docx/pdf/xlsx) gecached, of opnieuw gedownload bij elke aanroep?
- [ ] Bij `files_upload_v2` naar Slack: `file=io.BytesIO(bytes)`, niet `content=bytes`

## 2. Credentials en secrets

- [ ] Worden tijdelijke bestanden met service account JSON altijd verwijderd (try/finally of context manager)?
- [ ] Worden raw exceptions met Google API details (project IDs, quota URLs) naar Slack gestuurd?
- [ ] Worden Slack-tokens alleen meegestuurd naar `files.slack.com` / `slack-files.com` URLs?

## 3. Concurrency en cache

- [ ] Is de lazy-init van `_CACHE_DB` beschermd door `_READ_CACHE_LOCK`?
- [ ] Zijn alle code-paden die bestanden lezen gerouteerd via de cache (`_read_text`), ook Drive-binaire downloads?
- [ ] Wordt de cache ongeldig gemaakt bij Drive-wijzigingen (of is TTL acceptabel)?

## 4. Rate limiting volledigheid

- [ ] Geven alle slash-command handlers `user_id` door aan `_run_and_reply`?
- [ ] Kan `user_id` leeg zijn via bot-events (`app_mention` zonder `user` field)?

## 5. Feedback loop

- [ ] Is `fresh`-detectie in `feedback.py` juist in Drive mode (niet afhankelijk van lokaal bestandssysteem)?
- [ ] Hebben Block Kit-only berichten een `text` fallback voor `handle_reaction` (anders verdwijnt 👎)?
- [ ] Wordt `_HEADER` niet dubbel geschreven (zowel door `feedback.py` als door `drive_append_feedback`)?

## 6. Backup en outcomes

- [ ] Gebruikt `_cleanup_old_snapshots` paginering (`nextPageToken`) bij >100 snapshots?
- [ ] Worden backup-fouten gelogd én gemeld (niet alleen lokaal genegeerd)?
- [ ] Hebben `conversations.db` en `outcomes.db` elk een schema-versie check?

## 7. Geheugen en conversaties

- [ ] Worden zowel user- als assistant-berichten opgeslagen? (doubles de geheugengroei per beurt)
- [ ] Is channel-scoped memory (`mem_key = thread_ts or channel`) gedocumenteerd als bewuste keuze?
- [ ] Is er een max-grootte check op opgeslagen conversaties om context-overflow te voorkomen?

## 8. Slack error handling

- [ ] Worden alle foutberichten naar gebruikers getoond als gebruiksvriendelijke tekst (geen tracebacks)?
- [ ] Zijn alle berichtpaden (reply, thread reply, slash, error) consistent in Block Kit vs. plain text?
- [ ] Worden 👎-reacties op error-berichten correct afgehandeld (niet stil genegeerd)?

---

## Wat altijd gecheckt wordt (standaard `/review` dekt dit al)

- Secrets in code of logs
- Brede `except Exception` die fouten verzwelgen
- Ontbrekende tests voor nieuwe kritieke paden
- Dependencies gepind in `requirements.lock`
- CI-gate blokkert bij syntax-fouten

---

## Cadans

Na elke significante bouwfase (±10+ commits of nieuw architectuuronderdeel). Review-bestanden staan in `reviews/YYYY-MM-DD.md`.
