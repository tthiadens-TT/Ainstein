# Cache Design — convert_to_markdown.py

## **Doel**
Ainstein leest veel grote bestanden (Word, PowerPoint, PDF). Omzetten naar plain-text Markdown (.md) en cachen, zodat volgende reads sneller en goedkoper zijn.

## **Kritiek design-principe: CACHE NAAST ORIGINEEL**

**Regel 1: Elk cache-bestand staat in DEZELFDE map als zijn origineel-bestand.**

```
Origineel: 04_Marketing/_bronmateriaal/slack-dump.pdf
Cache:     04_Marketing/_bronmateriaal/slack-dump.md  ← NIET in 04_Marketing-root!

Origineel: 01_Clients/NN Group/Proposals/voorstel.docx
Cache:     01_Clients/NN Group/Proposals/voorstel.md  ← NIET in 01_Clients-root!
```

### Waarom?
1. **Schaalbaar:** Cache-bestanden volgen de huidige folder-structuur. Geen rommel in roots.
2. **Logisch:** Lezen in Ainstein zoekt cache op naam → parent-folder bepaalt waar.
3. **Wartbaar:** Oude cache simpel weg te ruimen (in die folder).
4. **Future-proof:** Als folder-structuur verandert, cache-lokatie verandert mee.

### Wat NIET werkt
```
❌ FOUT: alles in folder-root
  04_Marketing/slack-dump.md
  04_Marketing/voorstel.md
  04_Marketing/brandbook.md
  ...98 meer cache-bestanden hier...
  
→ Onleesbaar, moeilijk terug te vinden, niet schaalbaar
```

---

## **Hoe het werkt**

### convert_to_markdown.py: recursieve listing + parent-based writing

```python
# STAP 1: Recursief alle bestanden in folder verzamelen
files = _drive_list_files_in_folder(service, folder_id)
# Result: bestanden uit 04_Marketing EN 04_Marketing/_bronmateriaal EN 04_Marketing/_kennis

# STAP 2: Voor ELK bestand bepalen waar cache hoort
for f in files:
    parent_ids = f.get("parents", [])        # Waar hoort DIT bestand?
    cache_folder_id = parent_ids[0]          # Schrijf cache daar
    _upload_markdown(service, name, content, cache_folder_id)
```

**Key:** `f.get("parents")` = **waar staat dit bestand**. Cache gaat daar naast.

---

## **Fout-scenario (commit 709b9d7 fixed dit)**

```python
# ❌ FOUT (eddd8f5, e989b2b):
for f in files:
    cache_folder_id = folder_id  # Hard-coded root! Alles gaat naar root
    _upload_markdown(service, name, content, cache_folder_id)
    
Result: 86 cache-bestanden uit submappen landen allemaal in 04_Marketing-root
```

### Waarom gebeurde het?
1. **eddd8f5:** Introduceerde recursief zoeken, maar cache-bestemming was hard-coded root
2. **Misleidende comment:** "Schrijf naast het origineel" — maar code deed root
3. **Niemand tested vóór 3 juli:** Bug was onzichtbaar totdat script voor het eerst draaide

---

## **Verificatie & Opruiming**

### verify_cache_structure.py
Checkt: staan cache-bestanden (.md met `**Gecachet:**`) in folder-roots?
- **Ja** → fout; iemand draaide convert_to_markdown.py met oude code
- **Nee** → schoon; cache werkt correct

### cleanup_stray_cache.py
Verwijdert cache-bestanden die in folder-roots staan (oude rommel van vóór fix).

---

## **Voor de toekomst**

**Als je convert_to_markdown.py aanraakt:**

1. ✅ Recursieve listing moet blijven (voor alle submappen)
2. ✅ Cache-bestemming moet PER BESTAND bepaald worden (`parent[0]`)
3. ❌ NOOIT hard-coded `folder_id` als cache-doel
4. ✅ Run `verify_cache_structure.py` na wijzigingen
5. ✅ Voeg tests toe (unit tests voor parent-bepaling)

**Commits die voorbij review gaan met "cache opslag fout" — rood vlag:**
- Comment zegt "naast origineel", code doet root → inconsistent
- Recursief zoeken + één schrijf-doel → rommel ingebouwd
