# Plan (concept) — Ainstein verrijken met bronnen (het Aslander-fundament)

*Opgesteld 8 juli 2026. Status: ter beoordeling op een later moment. Concept-niveau, bewust weinig implementatiedetails. Dit plan legt vast wat we hebben gebouwd en waarom, en waar de verbetering zit.*

---

## Wat & Waarom (lees dit eerst)

**Wat:** een systeem dat Ainstein voedt met kennis uit veel bronnen (LinkedIn, Substack, Medium, website, Slack, meetings via Jamie, klantvoorstellen). De bronnen worden opgehaald, tot kennis gedistilleerd, en die kennis wordt in Ainsteins antwoorden gebruikt.

**Waarom:** zodat Ainstein slimmer wordt naarmate Minkowski meer doet, en die kennis niet opgesloten blijft in de hoofden van een klein netwerk. Dit is de kern van de Ainstein-ambitie: Einsteins mogelijk maken op schaal. Een voorstel of matching wordt beter omdat Ainstein put uit alles wat Minkowski al zegt, doet en wint.

**Het fundament (Aslander-principe van informatie-autonomie):** alle kennis leeft als **platte tekst** (`.md`), niet in propriëtaire formaten (geen Google Docs, geen tools die je opsluiten). Platte tekst is de universele taal: leesbaar, porteerbaar, toekomstbestendig, en goedkoop voor een AI om te lezen. Dit is geen technische smaak maar een principe: de kennis moet van Minkowski zijn en blijven, niet van een leverancier.

---

## Het concept in vier stappen (de flow)

```
1. OPHALEN        scrapers halen elke bron op → platte-tekst .md "bakje" in Drive
   (per bron een map onder _bronmateriaal/)
        ↓
2. DISTILLEREN    per bron: ruwe tekst → compacte "facetten" (map-stap)
        ↓
3. KRUISEN        alle distillaties samen → kennis_laag.md (reduce-stap)
   verrijken (elke bron voegt toe) + bevestigen (alleen over onafhankelijke stemmen)
        ↓
4. GEBRUIKEN      kennis_laag.md gaat in Ainsteins prompt → elk antwoord is scherper
```

**Twee taken, even belangrijk:**
- **Verrijken** — elke bron voegt facetten toe aan een onderwerp. Oorsprong maakt niet uit.
- **Bevestigen** — telt alleen als twee *onafhankelijke* stemmen hetzelfde zeggen. Alle eigen kanalen samen (LinkedIn/Substack/website) zijn maar twee stemmen: Jörgen en Minkowski. Een klant of expert is een echte derde stem.

**Eén gouden regel:** *promotie is mensenwerk.* De machine mag verzamelen en kruisen, maar of iets "officiële Minkowski-waarheid" wordt, beslist een mens (Jörgen/Charlotte). Dat is bewust, en het is de rem tegen hallucinatie op schaal.

---

## Wat we tot nu toe deden en waarom (het verhaal)

- **18 juni:** de kennislaag opgezet als bewijs-fase. Doel bewust breder dan één toepassing: Ainstein voeden, niet alleen "een gat vinden".
- **21 juni:** scrapers voor alle publieke bronnen + `bronnen.json` als bron-lijst. Auth-walled bronnen (LinkedIn) handmatig via een browser-methode binnengehaald.
- **29-30 juni:** "Double Helix" toegevoegd — elke kennis krijgt twee labels: hoe zeker (onbevestigd/informatie/kennis) en welk type (feit/overtuiging/afleiding). Zo weet Ainstein of het iets mag citeren of moet inleiden met "Minkowski stelt dat".
- **8 juli:** ontdekt dat de flow een **compleetheids-lek** had. De pijplijn las 42 LinkedIn-posts van Jörgen, terwijl een completere set van 120 verweesd en ongelezen in een verkeerde map lag. Oorzaak: het systeem wees naar een *map*, controleerde nooit of daar de rijkste versie in stond, en de scraper kon een rijke bron overschrijven met een armere. Gedicht met een compleetheids-grendel (nooit ontdubbelen naar minder) en een consolidatie-stap.

**De les uit 8 juli:** het systeem had geen enkel moment waarop het zichzelf controleerde op compleetheid of ordelijkheid. Kwaliteit was toeval, geen garantie. Dát is wat dit plan wil oplossen.

---

## Wat er beter kan (de verbeteragenda)

### 1. Van "bestanden overal" naar één bestand per bron
Nu staan er nog losse en dubbele bestanden: verweesde legacy-docs in verkeerde mappen, meerdere versies per bron, een mix van oude Google Docs en nieuwe `.md`. Doel: **precies één canoniek, platte-tekst bestand per bron**, dat na elke scrape wordt aangevuld/vernieuwd/ontdubbeld — nooit een tweede ernaast. Ordelijk, begrijpelijk, geen archeologie meer nodig.

### 1b. De brónlaag zelf ordenen (`01_Clients` als schrijnend voorbeeld)
Het probleem zit niet alleen in `_bronmateriaal` (de scrape-bakjes), maar net zo hard in de **bronlaag zelf**. `01_Clients` is nu een platte stortplaats: tientallen losse `.md`-bestanden (voorstellen, needs-analyses, transcripten, cache-versies, forwards) door elkaar, met daartussen een handvol echte klantmappen (NN Group, Jetske Ultee, Holland & Barrett). Voor een mens onvindbaar, voor Ainstein ruis, en cache-bestanden zijn niet te onderscheiden van echte documenten.

**Ontwerprichting (te beoordelen):**
- **Per entiteit een map, niet plat.** Elke klant zijn eigen submap (zoals NN Group al heeft), met een vaste, herkenbare interne indeling (bv. voorstellen / gespreksnotities / analyses / uitkomst). De top-laag werd op 30 juni al entiteit-gebaseerd gemaakt; die logica moet nú ook *binnen* de mappen doorgetrokken.
- **Cache hoort niet in de root.** De markdown-cache moet naast zijn origineel staan, nooit los in de map-root (dit is deels het bekende cache-opruim-item, maar hoort structureel hier thuis).
- **Eén canoniek document per ding.** Niet vijf forwards en drie versies van dezelfde needs-analysis los naast elkaar; het finale/geaccordeerde document is leidend, de rest is historie of weg.
- **Naamgeving die de structuur draagt** i.p.v. losse datum-prefixen die alleen chronologie geven.

Dit is dezelfde ziekte als het compleetheids-lek: er is geen ordenend principe dat wordt afgedwongen, dus rommel stapelt zich op tot iemand het toevallig ziet.

### 2. De flow perfectioneren (kwaliteit als garantie, niet toeval)
Inbouwen wat op 8 juli ontbrak:
- **Compleetheids-check:** een bron mag nooit stilletjes krimpen. Wat de map hoort te bevatten, staat vast en wordt geverifieerd.
- **Idempotentie:** een scrape opnieuw draaien mag nooit schade doen. "Alles opnieuw" en "alleen het nieuwe" leiden tot dezelfde, ontdubbelde uitkomst.
- **Herkomst zichtbaar:** per bron weten we wanneer, hoe en door wie hij is bijgewerkt (audit-spoor), zodat een wissel nooit meer onopgemerkt gebeurt.

### 3. Kwaliteit van de kennis optimaliseren
- **Echte onafhankelijke stemmen zwaarder** laten wegen (klant/expert > intern-Slack), i.p.v. elke stem gelijk tellen.
- **Meer echte derde stemmen** aansluiten (klant-jaarverslagen, podcast-gasten) zodat "bevestigen" meer betekent.
- **De merge tot één bestand als geverifieerde stap:** samenvoegen zonder ooit een post/artikel te verliezen (dekking van beide bronnen aantoonbaar ~100%), geen blinde plak.

### 4. De bevestigingsroutine goed maken (Thomas' idee)
De huidige routine bewaakt een dode lijst en is op pauze gezet. De juiste routine doet één van twee dingen, of allebei, **mits het goed gaat** (idempotent, geen dataverlies, geen ongewenste autonome schrijfacties):
- **OF een periodieke scrape** — bronnen fris houden, ontdubbeld, met de compleetheids-grendel.
- **OF een levende bevestigingsloop** — kijkt of er *nieuwe* kennisitems zijn die bevestigd moeten worden, én of *oude* kandidaten nog openstaan, en legt precies die voor aan Jörgen/Charlotte. Nooit dezelfde bevroren lijst opnieuw.
- **Randvoorwaarde:** de routine mag pas autonoom schrijven als de guardrails-vraag beantwoord is (dit raakt de open Loop-Charter-beslissing). "Promotie is mensenwerk" blijft: de routine legt voor, de mens beslist.

---

## Wat dit alles betekent (waarom het ertoe doet)
Dit is niet een opruimklus, het is het verschil tussen een Ainstein die toevallig goed antwoordt en een Ainstein die je kunt vertrouwen omdat de kennisstroom eronder ordelijk, compleet en controleerbaar is. Elke verbetering hierboven maakt Ainstein een stap minder afhankelijk van wie op welk moment welke scrape deed, en een stap dichter bij "de kennis is van Minkowski, geborgd en schaalbaar".

## Te beoordelen op een later moment
0. Akkoord op een **ordenend principe voor de hele bronlaag** (per entiteit een map met vaste indeling, cache naast origineel, één canoniek document per ding) — te beginnen bij `01_Clients`.
1. Akkoord op "één canoniek bestand per bron" als harde ontwerpregel.
2. Welke kwaliteitsverbeteringen eerst (stemgewicht, derde stemmen, merge-stap).
3. De routine: scrape, bevestigingsloop, of beide — en onder welke guardrails.
4. Wanneer de bewijs-fase over gaat in "aan" (de evidence-bar concreet maken).

*Naslag: de technische bevindingen en de openstaande acties staan in `plans/ainstein-roadmap.md` (sectie "Kennislaag bron-governance"); het geheugen `memory/kennis_laag_prove_phase.md` bewaart het verhaal.*
