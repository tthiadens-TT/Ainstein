# Ainstein — Deployment & Beheer

Dit document is voor de beheerder (Thomas). Het beschrijft hoe de VM-deployment werkt, welke schrijfpaden de agent heeft, en hoe je controleert of de beveiliging op orde is.

## Architectuur op de VM

```
GitHub (dev/main branch)
    │  push → GitHub Actions (.github/workflows/deploy.yml)
    │  SSH → thomas@VM
    ▼
/home/thomas/Ainstein/
    │  git pull origin dev
    │  sudo systemctl restart ainstein
    ▼
systemd service: ainstein
    └── python slack_app.py (Socket Mode — geen open poort nodig)
```

**Deploy:** push naar `dev` of `main` → automatisch uitgerold via GitHub Actions.
**Handmatig herstarten:** `sudo systemctl restart ainstein`
**Logs bekijken:** `sudo journalctl -u ainstein -f`

---

## Secrets op de VM

Secrets staan in `/home/thomas/Ainstein/.env` (nooit in git).

| Variabele | Doel |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API toegang |
| `SLACK_BOT_TOKEN` | Slack bot (xoxb-...) |
| `SLACK_APP_TOKEN` | Socket Mode (xapp-...) |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Pad naar service account JSON op de VM |
| `AINSTEIN_DRIVE_ROOT_ID` | ID van de Minkowski AInstein root-map in Drive |
| `AINSTEIN_STATUS_CHANNEL` | Slack channel ID voor startup/crash-notificaties (optioneel) |

**Service account JSON staat als bestand op de VM** (niet inline in de env var).
Bewaar het buiten de repo, bijvoorbeeld: `/home/thomas/secrets/ainstein-sa.json`

---

## Deploy-checklist: "werkt het?"

Drie lagen moeten alle drie kloppen — check altijd in deze volgorde:

```bash
# 1. Code: staat de juiste commit op de VM?
git -C /home/thomas/Ainstein log --oneline -3

# 2. Env vars: staan alle benodigde vars in .env?
grep -E "AINSTEIN_STATUS_CHANNEL|DRIVE_ROOT_ID" /home/thomas/Ainstein/.env

# 3. Service: draait de bot?
systemctl is-active ainstein

# 4. Opstartlog: is de env var opgepikt?
journalctl -u ainstein -n 20 --no-pager | grep -E "Status notifications|running in Slack"
```

**Tip voor .env-aanpassingen:** gebruik `echo` in plaats van nano — minder kans op vergeten save:
```bash
echo "AINSTEIN_STATUS_CHANNEL=C07TBGSDRNX" >> /home/thomas/Ainstein/.env
# Verifieer direct:
grep AINSTEIN_STATUS_CHANNEL /home/thomas/Ainstein/.env
# Dan herstarten:
sudo systemctl restart ainstein
```

---

## Wat de agent kan schrijven

Dit zijn alle schrijfpaden. Alles buiten deze lijst kan de agent niet wijzigen.

| Actie | Locatie | Reversibel? | Trigger | Bevestiging? |
|---|---|---|---|---|
| Feedback loggen (👎) | `05_Ainstein Knowledge Base/gaps.md` op Drive | ✅ Drive versiegeschiedenis | Slack 👎-reactie | Nee — auto |
| Inline correctie loggen | `05_Ainstein Knowledge Base/gaps.md` op Drive | ✅ Drive versiegeschiedenis | Gebruikersverzoek in chat | **Ja — altijd** |
| Conversatie opslaan | `conversations.db` (SQLite, op VM) | ✅ Bestand kopieerbaar | Elke beurt | Nee — auto |
| Beslissing loggen | `logs/decisions.jsonl` (op VM) | ✅ Append-only | Elke beurt | Nee — auto |
| Application log | `logs/ainstein.log` (op VM) | ✅ Roterend, 30 dagen | Continu | Nee — auto |

**De bronnenlaag (01_Clients t/m 05_Ainstein Knowledge Base) is volledig read-only.**
De agent heeft geen enkel tool om Drive-bestanden te verwijderen, hernoemen of overschrijven.

### Bekende beperking: channel-scoped geheugen

Conversatiegeheugen is gescopet op thread of channel (`mem_key = thread_ts or channel`). Als twee gebruikers tegelijk in hetzelfde Slack-channel een vraag stellen (buiten een thread), kunnen ze elkaars conversatiecontext overschrijven. In de praktijk is dit zelden een probleem — Minkowski gebruikt Ainstein overwegend in threads. Wil je dit oplossen: gebruik altijd threads (thread-ts heeft voorrang op channel-key).

---

## Beveiligingschecklist

### ✅ Geborgd in code
- `rm -rf` en destructieve git-operaties zijn hard geblokkeerd in `.claude/settings.json`
- `CLAUDE.md` en `settings.json` zijn locked — agent kan zijn eigen regels niet wijzigen
- Prompt injection: `brain.md` Operating Rule 10 — bronbestanden zijn data, geen commando's
- Elke Drive-write wordt gelogd in `decisions.jsonl` met `"drive_write": true`

### 🔲 Handmatig te controleren (eenmalig bij setup, en na elke service account-rotatie)

**1. Service account scope**
De service account gebruikt `drive`-scope (vereist voor gedeelde mappen).
Dit maakt de volgende check extra belangrijk:

**2. Sharing scope van de Drive-map** ← KRITIEK
Ga naar Google Drive → zoek de map `AInstein` (onder Minkowski) → Delen.
Controleer dat **alleen** het service account-mailadres toegang heeft.
Niet de hele Drive, niet de Minkowski-root — alleen deze map.

Als de map gedeeld is op een hoger niveau (bijv. de hele Minkowski-Drive):
de service account heeft dan toegang tot alles op dat niveau.

**3. GitHub Secrets**
Ga naar GitHub → Ainstein repo → Settings → Secrets.
Controleer dat `DEPLOY_HOST`, `DEPLOY_SSH_KEY` aanwezig zijn en niet verlopen.

---

## Wat te doen bij een incident

### Agent geeft foute antwoorden of gedraagt zich vreemd
1. `sudo systemctl stop ainstein` — zet de bot stil
2. Bekijk logs: `sudo journalctl -u ainstein --since "10 minutes ago"`
3. Bekijk `logs/decisions.jsonl` op de VM voor de laatste agent-beslissingen
4. Fix de oorzaak, dan: `sudo systemctl start ainstein`

### Feedback in gaps.md is incorrect
1. Ga naar Google Drive → `05_Ainstein Knowledge Base/gaps.md`
2. Open versiegeschiedenis (rechtermuisknop → Versiegeschiedenis beheren)
3. Herstel naar de gewenste versie

### Service account rotatie nodig
1. Genereer nieuw JSON-sleutelbestand in Google Cloud Console
2. Kopieer naar `/home/thomas/secrets/ainstein-sa.json` op de VM
3. `sudo systemctl restart ainstein`
4. Verwijder de oude sleutel uit Google Cloud Console

---

## Bekende beperkingen

### Gedeeld geheugen bij slash-commands in hetzelfde kanaal

Ainstein slaat gespreksgeheugen op per `thread_ts`. Slash-commands die buiten een thread worden uitgevoerd, vallen terug op de **channel ID** als sleutel (`mem_key = thread_ts or channel`). Dit is een bewuste keuze: één gesprekscontext per kanaal.

**Gevolg:** als twee gebruikers binnen seconden van elkaar `/proposal` of een andere slash-command uitvoeren in hetzelfde kanaal, overschrijft de tweede de gesprekscontext van de eerste. Bij laag verkeer (één actieve gebruiker per kanaal) is dit geen probleem. Bij multi-user gebruik in drukke kanalen kan dit verwarring geven.

**Tijdelijke workaround:** laat gebruikers slash-commands uitvoeren vanuit een Slack-thread, zodat `thread_ts` altijd beschikbaar is.

---

## Terugkijken op Drive-schrijfacties

```bash
# Alle Drive-writes in de afgelopen logs
grep '"drive_write": true' /home/thomas/Ainstein/logs/decisions.jsonl

# Voorbeeld output:
# {"timestamp": "2026-05-12T10:30:00", "event": "drive_write", "drive_write": true, "target": "05_Ainstein Knowledge Base/gaps.md", "action": "updated"}
```
