# Verkenning: de General Intuition-mechaniek toegepast op Minkowski en Ainstein

*Opgesteld: 2 juli 2026. Status: denkdocument, geen bouwplan. Auteur: Claude (sessie met Thomas).*

**Kernvraag:** is de mechaniek van General Intuition (gedrag plus uitkomsten systematisch vastleggen; gedrag testen in een virtuele wereld voordat het de echte wereld raakt; moat = vastgelegde menselijke intuïtie) vertaalbaar naar Minkowski? En kan Ainstein daarvoor de basis zijn, of komt een simulatielaag los van Ainstein te staan?

---

## Leeswijzer en labels

Elke claim in dit document draagt een van drie labels:

- **[feit]** — herleidbaar naar de inventarisatie (repo, kennislaag, Drive) of naar een externe bron
- **[interpretatie]** — mijn duiding van feiten
- **[aanname]** — niet geverifieerd, expliciet als onzeker gemarkeerd

Componenten die nog niet bestaan zijn gemarkeerd als **[vereist nieuwbouw]**.

---

## Fase 1: wat er staat

### Het businessmodel van Minkowski

Minkowski is een agency, geen consultancy: het ontwerpt en faciliteert leerervaringen, het schrijft geen strategierapporten [feit, positioning.md via kennislaag]. Het verkoopt maatwerk leiderschapsprogramma's aan leiderschapsteams (CEO's, directie, BU-leads; expliciet geen bulk-training) [feit]. De kern is experiential learning: "We don't talk about it, we do it", met de Kolb-cyclus als dagstructuur [feit]. Het methodisch fundament is applied futures: backcasting, Cone of Possibilities, Wheel of Reasoning, 7 Practices, scenario-kaarten (80+ trendkaarten, "movie poster"-format, intern nog work in progress) [feit, kennis_laag.md]. De verdienlogica is programmawerk op dagtarief (NN-context: EUR 10k per dag, 2 facilitators, groep van 30) met NN Group als ankerklant (5 parallelle trajecten) en UEFA en Columbia DSL als internationale referenties [feit]. Er bestaat al een interne schaalambitie: repliceerbare modules, AI-trainers (Jörgen bouwde er zelf al één voor decision-making onder onzekerheid), een AI-avatar voor moedige gesprekken als gewenste LEAD3-component, en de Futures Academy als digitale leeromgeving [feit, kennis_laag.md].

Eén vondst verdient nadruk: het simulatie-idee is voor Minkowski geen vreemde import. Jörgen positioneert scenariobouwen publiekelijk als "rehearsal, geen voorspelling", citeert Jane McGonigal's Superstruct (7.000 deelnemers simuleerden in 2008 een pandemie; hun gedrag bleek voorspellend voor echte COVID-reacties) en was in 2011 via Lance Weiler mede-maker van Pandemic 1.0 op Sundance [feit, kennis_laag.md]. De taal en de geloofsbrieven voor een simulatielaag bestaan al; wat ontbreekt is de systematiek en de technologie.

### Ainstein: architectuur en datastromen

Ainstein draait als single-agent systeem op een GCP-VM: Slack-bot (SocketMode), Jamie-webhook-pipeline voor meeting-transcripten, 21 skills als markdown-prompts, en een bronnenlaag in Google Drive via serviceaccount [feit, repo]. Wat wordt vastgelegd: volledige Slack-conversaties per thread (conversations.db), agent-traces per run (decisions.jsonl: skill, tools, tokens), meetingnotes in Drive, een getrianguleerde kennislaag over 9 bronnen met Double Helix-labeling (Zekerheid plus Type), en een feedbackloop (👎-reacties naar gaps.md) [feit].

Wat NIET wordt vastgelegd, en dit is de cruciale lacune: klantbesluiten op voorstellen (ja/nee), expert-match-validatie, de relatie tussen advies en gevolg, en meeting-acties met hun afloop [feit]. De outcome-registratiestructuur bestaat al als template (08_Outcomes, aangemaakt 28 mei 2026, velden voor Outcome, Wat werkte, Lessen) maar is nog nooit ingevuld; geen enkele code vult hem [feit]. Er liggen al twee concrete, niet-geregistreerde uitkomsten te verdampen: NN Inkomen Collectief gewonnen (mei 2026) en een expert-match verloren op tarief [feit, kennis_laag.md]. De methodische kern van Minkowski zit al in Ainstein als challenger-discipline (aannames labelen en toetsen in 6 van 9 kernskills), maar geen enkele skill vergelijkt voorspellingen met realisaties, en niets speelt strategieën door in een doorleefbare omgeving [feit, skills-inventarisatie].

**Kernconclusie fase 1 [interpretatie]:** Ainstein toetst aannames vóór executie, maar legt beslissing-plus-gevolg nergens vast als cumulatieve asset, en Minkowski's simulaties (scenario-sessies) blijven handmatig, eenmalig en vluchtig. Dat is exact het gat waar de GI-mechaniek over gaat.

---

## De GI-mechaniek ontleed

Feitencheck vooraf: General Intuition haalde $320M Series A op tegen $2,3 miljard waardering (Khosla Ventures, met Jeff Bezos en Eric Schmidt), totaal $454M inclusief de $134M seed van oktober 2025. De aankondiging was 25 juni 2026, niet januari zoals in de opdrachtomschrijving [feit, TechCrunch/GamesBeat, zie bronnen]. De kern klopt zoals beschreven: getraind op honderden miljoenen uren gameplay van Medal, en het beslissende ingrediënt is niet de beelden maar de actie-labels: exact welke knop een speler wanneer indrukte. Met acht minuten echte robotdata na pre-training op games navigeerde hun robot een onbekend kantoor [feit].

De mechaniek bestaat uit drie bouwstenen, die als toetskader dienen voor elke richting hieronder:

1. **Gedragsdata plus uitkomsten.** Niet content, maar beslissingen onder druk, gelabeld met wat er daarna gebeurde. De dataset is waardevol omdat niemand anders hem kan repliceren.
2. **Simulatie vóór realiteit.** Gedrag wordt getest en geleerd in een virtuele wereld voordat het de echte wereld raakt. De simulatie is geen demonstratie maar een oefenruimte met consequenties.
3. **Moat = vastgelegde menselijke intuïtie.** Het diepste actief is niet het wereldmodel maar de vastgelegde menselijke besluitvorming; die verdampt normaal gesproken.

### Vergelijkbare businessmodellen (verrijking, uit webonderzoek)

- **Gong** (revenue intelligence, 4.800+ klanten): legt elke klantinteractie vast, koppelt die aan win/loss-uitkomsten, en voedt elke uitkomst terug in het systeem: "feeding every outcome back so the system compounds the advantage deal by deal" [feit]. Dit is de GI-loop in B2B-sales: de moat is niet de software maar de interactie-plus-uitkomst-graaf. Les voor Minkowski: het flywheel begint bij registratie van uitkomsten, niet bij AI [interpretatie].
- **Principle** ($2M pre-seed, San Francisco): brengt militaire wargaming-methodes naar corporate strategie als "Strategic Foresight AI platform": scenario's simuleren vóór budgetten en overnames vastgelegd worden [feit]. Les: er ontstaat een categorie "beslissings-repetitie voor executives", maar die is analytisch en platform-gedreven, niet ervaringsgericht [interpretatie].
- **Synthetic personas / synthetic users** (volwassen categorie in marktonderzoek): AI-modellen van klantsegmenten om ideeën en boodschappen op te testen. Bekende zwaktes: bias-versterking, geen emotionele diepte, vertrouwenserosie als deelnemers synthetisch blijken [feit]. Les: persona-simulatie alleen is een commodity; het onderscheid zit in de onderliggende, eigen dataset en in de begeleiding [interpretatie].
- **Militaire wargaming-democratisering** (CSIS, US Army War College): generatieve AI vervangt menselijke rollenspelers en maakt wargaming goedkoop en herhaalbaar; het wordt een "repeatable operating rhythm": signalen opnemen, scenario's draaien, beslissingen testen, aannames bijstellen, uitkomsten volgen [feit]. Les: precies dat ritme is wat een futures-bureau kan verkopen als dienst in plaats van als eenmalige sessie [interpretatie].

**Weging voor de onderscheidendheidstoets [interpretatie]:** het veld beweegt aantoonbaar, maar concentreert zich op drie plekken: FP&A-scenariotools (Pigment, Workday, Drivetrain), interne AI-productiviteit bij consultancies (McKinsey's Lilli), en analytische wargaming-platforms (Principle). Niemand in het onderzoek combineert experiential leiderschapsontwikkeling met AI-gedreven, bewoonbare scenario's én een eigen oordeel-dataset. Dat venster bestaat, maar de aanname dat het lang open blijft is niet te verifiëren [aanname].

---

## Divergentie: vier richtingen

*Noot over DVV: de opdracht definieert DVV als Duidelijk, Verifieerbaar, Verkoopbaar. Ainstein's eigen dvv_check-skill definieert DVV anders (Duidelijk, Volledig, Verleidelijk, een schrijfkwaliteitstoets). Hieronder geldt de opdracht-definitie; de naamsbotsing is het signaleren waard om interne spraakverwarring te voorkomen.*

### Richting A: het beslis- en uitkomstenregister ("de kleine Gong")

**Wat:** elke commerciële en programmatische beslissing systematisch vastleggen met voorspelling en latere uitkomst: voorstel ingediend (met prijslogica en aannames) → gewonnen/verloren plus reden; expert voorgesteld → ingezet en bevallen; programma-ontwerpkeuze → deelnemersfeedback. Append-only, klein, meedogenloos consequent.

**Wat er al ligt [feit]:** de 08_Outcomes-template met exact de juiste velden; decisions.jsonl en conversations.db die de beslis-kant al loggen; meeting_reviewer die transcripten al analyseert; twee registreerbare uitkomsten die nu verdampen. **[Vereist nieuwbouw]:** de outcome-kant: een registratiemoment (Slack-commando of maandelijkse prompt) en een skill-uitbreiding die voorspelling en realisatie naast elkaar legt.

**DVV:** Duidelijk: hoog, iedereen snapt een win/loss-register. Verifieerbaar: hoog, het register zelf is de verificatie. Verkoopbaar: laag op korte termijn (interne asset), oplopend: "wij leren aantoonbaar van elke opdracht" is op termijn een propositie-element [interpretatie].

**Versterkt of kannibaliseert:** versterkt puur; raakt niets aan de bestaande propositie. **Ainstein als basis:** volledig; dit is een uitbreiding van bestaande pipelines, geen nieuw systeem. **Flywheel op Minkowski-schaal:** traag maar reëel; bij tientallen beslissingen per jaar ontstaat na 2 tot 3 jaar een dataset die geen concurrent heeft, omdat niemand anders bij deze gesprekken zat [interpretatie]. De onderscheidendheidstoets is hier gunstig: Gong bewijst het model, maar Gong bestaat niet voor boutique-advieswerk.

### Richting B: adversariale simulatie ("de voorstel-windtunnel")

**Wat:** voorstellen en strategieën testen tegen gesimuleerde stakeholders (CFO, CHRO, inkoop, sceptische deelnemer) voordat ze de klant raken. Meerdere rondes: Ainstein bouwt, klant-agents schieten, Ainstein versterkt.

**Wat er al ligt [feit]:** het roadmap-item "Klant-Agent" beschrijft precies dit voor voorstellen; de skills-architectuur maakt een persona-prompt triviaal om toe te voegen; de kennislaag levert klantcontext (NN-cultuurpatronen zoals de "daar gaan we weer"-reactie staan er al in). **[Vereist nieuwbouw]:** de persona-skills zelf en een orkestratie van meerdere rondes.

**DVV:** Duidelijk: middel, vergt uitleg maar de windtunnel-metafoor helpt. Verifieerbaar: zwak zolang richting A niet bestaat: zonder outcome-register kun je niet aantonen dat windtunnel-voorstellen vaker winnen [interpretatie]. Verkoopbaar: indirect; het verkoopt betere voorstellen, niet zichzelf.

**Versterkt of kannibaliseert:** versterkt de interne kwaliteit; risico is gering. **Ainstein als basis:** volledig. **Flywheel:** zwak als losstaande richting; de persona's worden pas beter dan generiek LLM-toneel als ze gevoed worden door A (echte bezwaren, echte verliesredenen) [interpretatie]. Onderscheidendheid: laag; synthetic personas zijn een commodity-categorie, dit wint alleen op de eigen data.

### Richting C: bewoonbare scenario's ("de vluchtsimulator voor strategie")

**Wat:** Minkowski's scenario-kaarten en Futures Cone-scenario's omzetten van statische verhalen naar omgevingen die deelnemers kunnen bewonen: AI-agents spelen stakeholders in het scenario, deelnemers nemen beslissingen, het scenario reageert, en de gevolgen worden zichtbaar en bespreekbaar. Van "praten over 2035" naar "handelen in 2035". Klanten doorleven strategieën voordat ze kiezen.

**Wat er al ligt [feit]:** de methodische basis is compleet (scenario-kaarten, Wheel als backcasting-structuur, experiential learning als designfilosofie); de taal bestaat al (rehearsal, Superstruct, Pandemic 1.0); de klantvraag bestaat al (LEAD3 wil expliciet een AI-laag, inclusief avatar voor moedige gesprekken); Jörgen bouwde al een eerste AI-trainer. **[Vereist nieuwbouw]:** vrijwel de hele technische laag: scenario-agents, een interactievorm (in de sessie via facilitator, of een eigen interface), en de koppeling van deelnemersbeslissingen aan scenario-dynamiek. In de volle variant (klanten gebruiken het zelfstandig) ook een frontend buiten Slack.

**DVV:** Duidelijk: middel; de vluchtsimulator-metafoor is sterk maar het product vergt demonstratie. Verifieerbaar: laag tot middel; het effect op klantbeslissingen is moeilijk te isoleren, maar de deelnemerservaring en herhaalinzet zijn meetbaar. Verkoopbaar: hoog; dit is de enige richting die direct als klantpropositie verkoopbaar is, past naadloos op experiential learning ("we don't talk about it, we do it" toegepast op de toekomst zelf) en de vraag is er al [interpretatie]. Onderscheidendheidstoets: gunstig; Principle en de FP&A-tools blijven analytisch en zitten in een andere koopcontext, synthetic-persona-tools missen de methodiek en de facilitering. De combinatie ervaringsgericht plus futures-methodiek plus AI-agents kwam in het onderzoek nergens voor [feit, binnen de grenzen van 6 zoekacties].

**Versterkt of kannibaliseert:** dit is de scherpste vraag van het document. Versterking: het verdiept precies wat Minkowski al claimt (rehearsal in plaats van voorspelling) en maakt het schaalbaarder en herhaalbaar. Kannibalisatie-risico [interpretatie]: als de simulatie het gesprek vervangt in plaats van voedt, ondermijnt het de kern van de facilitatie-filosofie ("curator van collectieve intelligentie"; de waarde zit in wat mensen sámen doormaken). Een tool die deelnemers individueel achter een scherm zet is anti-Minkowski. De grens: de simulatie moet een ervaringslaag ín de sessie zijn, zoals Lego Serious Play dat is, geen vervanging van de sessie. Tweede risico: een technologisch speeltje zonder de dataset eronder is kopieerbaar door elk bureau met een LLM-abonnement; het onderscheid verdampt dan in een jaar [aanname, maar consistent met de commodity-les uit synthetic personas].

**Ainstein als basis:** gedeeltelijk. De kennislaag en skills-architectuur zijn de juiste voedingsbodem (scenario-agents zonder Minkowski-kennis zijn generiek), maar de interactievorm groeit uit Slack. De juiste lezing [interpretatie]: Ainstein blijft het brein (kennis, personas, methodiek), de simulatie wordt een tweede gezicht op datzelfde brein. Volledig los bouwen zou een tweede waarheid creëren en de Ainstein-ambitie (één schaalbaar kennissysteem) ondermijnen.

**Flywheel:** potentieel het sterkst, maar alleen mét richting A en D: elke gespeelde simulatie produceert precies het soort beslisdata-onder-druk waar GI's mechaniek om draait (wat kozen deelnemers, wat werkte). Zonder registratie is elke sessie opnieuw eenmalig [interpretatie].

### Richting D: expert-intuïtie vangen ("Jörgens oordeel als dataset")

**Wat:** het oordeel-onder-onzekerheid dat nu in sessies en scenariowerk ontstaat en verdampt, structureel vastleggen: situatie → expert-oordeel → verwachting → (later) uitkomst. Niet de content (die vangt de kennislaag al), maar de beslismomenten: waarom koos Jörgen in dít ontwerp voor saboteurs in module 1, waarom greep een facilitator in bij díe groepsdynamiek, wat verwachtte hij dat er zou gebeuren.

**Wat er al ligt [feit]:** de Jamie-pipeline vangt transcripten van precies de gesprekken waar dit oordeel valt; meeting_reviewer analyseert ze al; het entiteiten-register borgt wie wie is; de kennislaag heeft al een Double Helix-structuur (feit/overtuiging/afleiding) waar "oordeel" logisch op aansluit. **[Vereist nieuwbouw]:** een extractie-stap in meeting_reviewer (oordelen en verwachtingen herkennen en registreren) en de outcome-koppeling uit richting A.

**DVV:** Duidelijk: middel tot hoog; "we leggen vast wat nu alleen in Jörgens hoofd zit" is intern direct begrijpelijk. Verifieerbaar: middel; of een vastgelegd oordeel het echte oordeel wás is toetsbaar (Jörgen kan het lezen en corrigeren), of het "intuïtie" vangt blijft interpretatie. Verkoopbaar: intern zeer hoog: dit ís letterlijk de Ainstein-missie (methodologie en expertise vastleggen zodat Minkowski onafhankelijk wordt van één persoon) en het is de directe voorwaarde voor de repliceerbare-modules-ambitie die intern al leeft [feit dat die ambitie bestaat; interpretatie dat dit de voorwaarde is]. Extern indirect.

**Versterkt of kannibaliseert:** versterkt; het enige risico is menselijk, niet commercieel: experts moeten willen dat hun oordeel vastgelegd en herbruikbaar wordt [aanname; nooit met Jörgen besproken voor zover de bronnen tonen]. **Ainstein als basis:** volledig. **Flywheel:** dit is Minkowski's eerlijke equivalent van GI's moat. Niet miljarden actie-gelabelde clips, maar honderden gecureerde oordeel-momenten van bewezen experts in echte klantcontexten. Klein, maar letterlijk onrepliceerbaar: een concurrent kan de methode kopiëren, niet de vastgelegde beslisgeschiedenis [interpretatie].

---

## Weging en conclusie

### De sterkste richting

**D plus A, als één beweging: het oordeel- en uitkomstenregister.** Niet C, hoe verleidelijk de vluchtsimulator ook is. De redenering:

1. **De moat zit in de data, niet in de simulatie [interpretatie].** GI's eigen les: de gameplay-beelden waren niet het goud, de actie-labels waren het goud. Voor Minkowski geldt hetzelfde: scenario-agents kan elk bureau bouwen; de vastgelegde beslisgeschiedenis van Minkowski's experts en klanten kan niemand repliceren. Wie C bouwt zonder D en A, bouwt het kopieerbare deel eerst.
2. **Elke maand wachten is verdampte data [feit dat er nu al twee uitkomsten onregistreerd verdampten].** De dataset kan alleen cumulatief groeien; de kost van vandaag beginnen is minimaal, de kost van uitstel is onomkeerbaar.
3. **Het is de kleinste stap met de grootste optionaliteit [interpretatie].** A en D maken B beter (echte bezwaren voeden de personas) en maken C verdedigbaar (simulaties gegrond in echte beslisdata in plaats van LLM-toneel). Omgekeerd geldt dat niet.
4. **Het ís de Ainstein-ambitie.** Expertise vastleggen zodat het bedrijf onafhankelijk wordt van één persoon staat al in de missie; dit geeft er een concreet, GI-geïnspireerd mechanisme aan.

C blijft de commerciële horizon: het is de enige richting die klanten direct kunnen kopen, en de klantvraag (LEAD3's AI-laag) bestaat al. Maar C hoort ná de fundering, en kan klein beginnen als ervaringslaag ín bestaande sessies (één scenario-agent in één LEAD3-werkvorm) in plaats van als platform [interpretatie]. B lift mee zodra het Klant-Agent-roadmapitem gebouwd wordt.

### Ainstein: basis of los?

Basis, ondubbelzinnig, voor A, B en D: dit zijn uitbreidingen van bestaande pipelines en skills. Voor C geldt: het brein blijft Ainstein (kennislaag, personas, methodiek), alleen de interactievorm kan op termijn een eigen gezicht krijgen. Een simulatielaag los van Ainstein bouwen zou de kennislaag splitsen en is strategisch af te raden [interpretatie].

### De kleinst mogelijke eerste stap

Concreet aan Ainstein toe te voegen, in volgorde:

1. **Registreer de twee bekende uitkomsten** (NN IC gewonnen; expert-match verloren op tarief) handmatig in de bestaande 08_Outcomes-template. Kost: een half uur. Dit test of het format werkt vóór er iets gebouwd wordt.
2. **Breid `meeting_reviewer` uit met één sectie:** "Oordelen en verwachtingen": welke expliciete keuzes en voorspellingen deden Minkowski-deelnemers in deze meeting (situatie → oordeel → verwachting). Weggeschreven naar een append-only register in Drive naast de kennislaag. Kost: een skill-tekstwijziging plus een schrijfactie; geen nieuwe architectuur.
3. **Voeg een maandelijks terugkijk-moment toe** (cron of Slack-prompt in #ainstein-status, passend bij het bestaande feedback-designprincipe dat Thomas als PO handelt): welke open voorspellingen en voorstellen hebben inmiddels een uitkomst? Vul het register.

Pas als dit drie maanden loopt en het register vult, is de vraag aan de orde of één LEAD3-werkvorm een bewoonbaar scenario-experiment (C-licht) verdient.

### Waar de analogie met General Intuition ophoudt

Eerlijk benoemd, want geforceerde parallellen zijn hier het grootste risico:

- **Schaal.** GI leert statistisch uit miljarden clips; Minkowski verzamelt hooguit honderden beslismomenten per jaar. Er valt geen model te trainen; er valt een gecureerde casusbank op te bouwen. Dat is kennismanagement met een GI-blik, geen machine learning [interpretatie].
- **Actie-labeling.** Gameplay heeft exacte, ondubbelzinnige acties (welke knop, wanneer). Advieswerk heeft ambigue acties, uitkomsten met maanden vertraging en talloze verstorende factoren. "Voorstel verloren" bewijst niet dat de prijslogica fout was [interpretatie].
- **De gesloten lus.** Een game geeft directe, objectieve uitkomsten. Strategiewerk geeft trage, multi-causale, betwistbare uitkomsten. Het register wordt daarom nooit een waarheidsmachine, wel een geheugen dat patronen zichtbaar maakt die nu volledig verdampen.
- **Het product.** GI verkoopt uiteindelijk autonome agents (robots, search and rescue). Minkowski verkoopt menselijke transformatie; de mens blijft in de lus, en dat is geen beperking maar de propositie zelf. De GI-mechaniek is hier een leerstrategie voor het bedrijf, geen productstrategie richting autonomie.

---

## Bronnen

**Intern:** repo-inventarisatie 2 juli 2026 (agent.py, tools.py, memory.py, feedback.py, log_setup.py, transcript_processor.py, skills/, scripts/setup_outcomes.py, plans/ainstein-roadmap.md, brain.md); kennis_laag.md en kansen.md (Shared Drive, gelezen via serviceaccount 2 juli 2026).

**Extern (webonderzoek, 6 zoekacties, 2 juli 2026):**
- [TechCrunch: General Intuition's $2.3B bet](https://techcrunch.com/2026/06/25/general-intuitions-2-3b-bet-that-video-games-can-train-ai-agents-for-the-real-world/) en [GamesBeat-interview](https://gamesbeat.com/general-intuition-raises-320m-at-2-3b-valuation-for-ai-frontier-models-based-on-gameplay-exclusive-interview/): funding, actie-labels, robot-demo
- [Gong Revenue Harness](https://www.gong.io/blog/gong-revenue-harness) en [Revenue AI OS](https://www.gong.io/blog/new-product-announcements-gong-revenue-ai-operating-system): outcome-flywheel als moat
- [Principle raises $2M for AI strategy wargaming](https://theaiworld.org/news/principle-raises-2m-for-ai-strategy-wargaming): adjacente nieuwkomer
- [CSIS: It Is Time to Democratize Wargaming Using Generative AI](https://www.csis.org/analysis/it-time-democratize-wargaming-using-generative-ai) en [Sedulo: business wargaming](https://sedulogroup.com/blog-post/what-is-wargaming-competitive-strategy/): wargaming-als-ritme
- [Market Logic: synthetic personas](https://marketlogicsoftware.com/blog/consumer-insights-synthetic-personas-agentic-ai/) en [Indeemo: when they work and when they don't](https://indeemo.com/blog/synthetic-personas): commodity-categorie plus zwaktes
- [BCG: The Corporate Strategy Function in an AI-First World](https://www.bcg.com/publications/2026/the-corporate-strategy-function-in-an-ai-first-world) en [Future of Consulting: 2026 update](https://futureofconsulting.ai/ai-leadership/2026-consultings-ai-revolution-update/): consultancies richten AI op interne productiviteit
- Scenariotools-landschap: [Pigment](https://www.pigment.com/blog/ai-for-scenario-planning), [Workday](https://blog.workday.com/en-us/how-generative-ai-is-reinventing-scenario-planning.html), [SigmaQu](https://www.sigmaqu.ai/scenario-planning): FP&A-hoek, niet ervaringsgericht
