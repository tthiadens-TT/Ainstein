/*
 * What's Your Future? -- scenario content.
 * Signals as of July 2026. Refresh quarterly: regenerate scenarios, update meta.signalsAsOf.
 * Schema is fixed. Do not change key names or nesting without updating app.js.
 */

const SCENARIO_DATA = {
  "meta": {
    "signalsAsOf": "July 2026",
    "version": "1.0"
  },
  "sectors": [
    {
      "id": "financial-services",
      "label": "Financial Services"
    },
    {
      "id": "talent-staffing",
      "label": "Talent & Staffing"
    },
    {
      "id": "infrastructure-public",
      "label": "Infrastructure & Public"
    },
    {
      "id": "retail",
      "label": "Retail"
    }
  ],
  "themes": [
    {
      "id": "ai-automation",
      "label": "AI & Automation"
    },
    {
      "id": "climate-regulation",
      "label": "Climate & Regulation"
    },
    {
      "id": "talent-culture",
      "label": "Talent & Culture"
    },
    {
      "id": "geopolitical-disruption",
      "label": "Geopolitical Disruption"
    }
  ],
  "scenarios": {
    "financial-services": {
      "ai-automation": {
        "probable": {
          "text": "Your underwriting, claims triage and first-line advice run through AI models trained on your own historical decisions, with human review kept for edge cases and audit trails. Your plan assumes that shrinking headcount at the same pace as model rollout is the win, and that customers will accept a machine-first front line as long as escalation to a human stays possible.",
          "question": "Which parts of your current three-year plan quietly assume that headcount reduction, not decision quality, is the metric that proves the AI investment worked?"
        },
        "plausible": {
          "text": "The assumption that breaks is that model outputs stay explainable enough to satisfy a supervisor on demand. A regulator asks for the reasoning behind a batch of declined loans or claims, you cannot reconstruct it at the level required, and remediation costs and a supervisory order land faster than any efficiency gain the model produced.",
          "question": "If your supervisor asked you tomorrow to reconstruct the reasoning behind last month's automated decisions, could you, and what would that answer cost you if you couldn't?"
        },
        "preferable": {
          "text": "You treat explainability as a competitive asset rather than a compliance cost: every automated decision carries a reconstructable rationale by design, and that traceability becomes a selling point to both supervisors and corporate clients who need to defend their own exposure. This is a deliberate architecture choice made before the regulator asks, not a retrofit after an incident.",
          "question": "Are you willing to slow model deployment now to build explainability in from the start, rather than betting you can bolt it on later under supervisory pressure?"
        }
      },
      "climate-regulation": {
        "probable": {
          "text": "You treat climate risk reporting as a disclosure exercise: you collect the data the current taxonomy requires, publish the mandated figures, and file transition plans that describe intent without binding capital allocation. Your plan assumes disclosure requirements plateau at roughly today's level of granularity.",
          "question": "What capital or underwriting decision are you still postponing because you've treated climate disclosure as a reporting deadline rather than a pricing input?"
        },
        "plausible": {
          "text": "The assumption that breaks is that transition risk stays a reporting category rather than becoming a pricing variable supervisors actively test. A stress test or a mandated scenario exercise forces you to show what happens to your loan book or insurance portfolio under a faster decarbonisation path than your own transition plan assumes, exposing concentration you had not priced.",
          "question": "If a supervisor ran a faster decarbonisation scenario against your book than your own transition plan assumes, where would the concentration show up first?"
        },
        "preferable": {
          "text": "You use your own transition data to reprice exposure ahead of the mandate, turning early climate underwriting discipline into a source of trust with both supervisors and corporate clients navigating the same transition. You position yourself as the counterparty that already knows its exposure, not the one still gathering the data when asked.",
          "question": "Where could you choose to reprice a concentrated exposure now, ahead of any mandate, to be the counterparty clients trust when the transition accelerates?"
        }
      },
      "talent-culture": {
        "probable": {
          "text": "You keep competing for the same narrow pool of quant, risk and compliance talent through compensation, while career paths and internal mobility stay largely unchanged from a decade ago. Your plan assumes that paying more for the same profile is a sufficient response to scarcity.",
          "question": "How much of next year's compensation budget is going toward outbidding competitors for the same talent profile, instead of building a path that doesn't yet exist internally?"
        },
        "plausible": {
          "text": "The assumption that breaks is that technical and risk talent will keep accepting your current pace of decision-making and hierarchy in exchange for compensation. A cohort of senior risk or quant staff leaves for a leaner, faster-moving competitor or a non-bank entrant, taking institutional judgment your models can't yet replace with them.",
          "question": "If your three most senior risk officers left within the same quarter, what judgment would leave the building that no model or documentation currently captures?"
        },
        "preferable": {
          "text": "You build internal career paths that let technical talent grow influence without needing to leave for a flatter organisation, and you treat the retention of institutional judgment as a board-level risk metric, not an HR one. It's a deliberate bet that judgment retained is worth more than any single hire.",
          "question": "Would you be willing to put institutional-judgment retention on the board risk dashboard, next to capital and liquidity, rather than leaving it to HR reporting?"
        }
      },
      "geopolitical-disruption": {
        "probable": {
          "text": "Your cross-border operations, correspondent banking relationships and capital flows continue on the assumption that the current sanctions and trade architecture holds roughly steady, with contingency plans limited to the jurisdictions already flagged as high-risk. Your plan assumes the map of restricted counterparties changes slowly enough to react to.",
          "question": "Which counterparty or corridor in your current plan would you struggle to unwind quickly if it were sanctioned with little warning?"
        },
        "plausible": {
          "text": "The assumption that breaks is that sanctions and capital-control regimes change slowly enough to unwind exposure in an orderly way. A new round of restrictions hits a jurisdiction or counterparty class you have meaningful exposure to with days, not quarters, of notice, and the unwind has to happen under stress rather than on a controlled timeline.",
          "question": "Do you have an unwind plan for your largest cross-border exposure that assumes days of notice rather than quarters?"
        },
        "preferable": {
          "text": "You build optionality into your correspondent and counterparty network before you're forced to, deliberately diversifying corridors so that no single geopolitical decision elsewhere can freeze a material part of your operations. You treat geopolitical resilience as a design parameter for the network, not a response plan for when the network fails.",
          "question": "Which single corridor or counterparty relationship, if frozen tomorrow, would force you into crisis mode, and are you willing to invest now in not needing it?"
        }
      }
    },
    "retail": {
      "ai-automation": {
        "probable": {
          "text": "Your demand forecasting, pricing and replenishment run on algorithms trained on your own sales history, with store staff executing what the system recommends rather than overriding it. Your plan assumes that the historical sales patterns feeding the model will keep looking like the future, and that store teams will keep trusting a system they can't easily question.",
          "question": "Which category in your assortment is the forecasting model most likely to get wrong because it's never seen a pattern like what's coming?"
        },
        "plausible": {
          "text": "The assumption that breaks is that the training data still resembles the world it's predicting. A shift in consumer behaviour, a new competitor format, or a supply disruption produces a pattern the model has never seen, and it keeps confidently recommending the old pattern while your stock and pricing drift further from what the market is actually doing.",
          "question": "How would you notice if your forecasting model was confidently wrong for three straight weeks, before the shelves and the P&L told you?"
        },
        "preferable": {
          "text": "You build a standing practice of store staff flagging when the model's recommendation doesn't match what they're seeing on the floor, and you treat that friction as a signal worth acting on rather than noise to override. It's a deliberate choice to keep human pattern-recognition in the loop as a check on the model, not a legacy step to automate away.",
          "question": "Are you willing to slow down automation of the override step, so store-level judgment stays a live check on the model rather than something you eventually eliminate?"
        }
      },
      "climate-regulation": {
        "probable": {
          "text": "You handle supply chain due diligence and packaging changes as compliance projects tied to the current reporting calendar, with sourcing decisions largely unchanged apart from what the law explicitly requires. Your plan assumes that the next round of due diligence or packaging rules will look like an incremental extension of the current one.",
          "question": "Which supplier relationship are you keeping unchanged today purely because the current rules don't yet force you to look at it?"
        },
        "plausible": {
          "text": "The assumption that breaks is that extended producer responsibility and due diligence rules keep expanding at the same incremental pace. A jurisdiction moves faster than expected, holding you directly liable for a supplier's environmental or labour practice several tiers back in the chain, and the cost of that liability lands well before you had planned to remap that part of your sourcing.",
          "question": "If you were held directly liable for your tier-three supplier's practices next year instead of in five years, which part of your sourcing map would you need to redraw first?"
        },
        "preferable": {
          "text": "You map your supply chain deeper than current rules require and use that visibility to shift sourcing on your own terms, turning transparency into a reason customers and regulators trust your shelf over a competitor's. It's a bet that knowing the chain before being forced to is worth more than the cost of finding out.",
          "question": "Where would deeper supply chain visibility let you make a sourcing move now that you'd otherwise be forced into later under worse terms?"
        }
      },
      "talent-culture": {
        "probable": {
          "text": "Your store staffing continues to rely on part-time, high-turnover roles with scheduling optimised for labour cost per hour, and your plan assumes that high turnover is simply the cost of doing retail. Training investment stays proportional to how long the model expects someone to stay.",
          "question": "What is high turnover actually costing you in customer experience and shrink that your labour-cost-per-hour metric doesn't capture?"
        },
        "plausible": {
          "text": "The assumption that breaks is that store-level service quality can stay flat while turnover stays high, because customers won't notice or won't care. A competitor with a materially different staffing model, fewer but better-trained, better-paid store staff, starts pulling share in exactly the categories where advice and service matter, and the gap shows up in conversion before it shows up in surveys.",
          "question": "If a competitor built its store model around fewer, better-paid staff, which of your categories would lose share first?"
        },
        "preferable": {
          "text": "You treat a subset of stores or categories as a deliberate test of a different staffing model, fewer roles, more training, more autonomy, and you measure it against the standard model on service and margin, not just cost per hour. It's a choice to prove the case with evidence before betting the whole estate on it.",
          "question": "Which stores or categories would you be willing to run as a real test of a different staffing model, and what would need to be true for you to scale it?"
        }
      },
      "geopolitical-disruption": {
        "probable": {
          "text": "Your sourcing stays concentrated in the regions and shipping lanes that have worked reliably for years, with contingency planning limited to insurance and buffer stock rather than structural diversification. Your plan assumes that the last disruption was the exception, not a preview of a more frequent pattern.",
          "question": "How many weeks of disruption in your primary sourcing region or shipping lane could you absorb before it shows up as empty shelves?"
        },
        "plausible": {
          "text": "The assumption that breaks is that shipping lanes and sourcing regions disrupt one at a time, giving you room to reroute. Two disruptions land in the same season, a lane closure and a tariff shift on the alternate route, and the buffer stock and insurance built for a single-point failure aren't enough to cover a compound one.",
          "question": "If your primary sourcing route and your backup route were both disrupted in the same quarter, what would you take off the shelf first?"
        },
        "preferable": {
          "text": "You deliberately build redundancy into sourcing before the next disruption, treating a second qualified supplier or route in a different geography as a standing cost of doing business rather than a project triggered by the last crisis. You position yourself as the chain still stocked when a competitor's shelves go bare.",
          "question": "Are you willing to pay a standing premium for sourcing redundancy now, rather than paying a crisis premium the next time a single point of failure breaks?"
        }
      }
    },
    "talent-staffing": {
      "ai-automation": {
        "probable": {
          "text": "Your workforce plan still assumes recruiters source and screen the way they did in 2023, with AI as a faster search box bolted onto the same process. Volume grows, margins per placement keep thinning, and the technical and STEM roles that pay best stay the hardest to fill.",
          "question": "If your placement model still assumes a human recruiter per requisition, what part of this year's growth budget is actually betting on that not changing?"
        },
        "plausible": {
          "text": "The assumption that breaks: that clients will keep paying for access to candidates rather than for verified skill and speed to productivity. Once an AI layer can assess and match technical talent directly, the staffing fee for that layer of work stops being defensible.",
          "question": "Which fee lines in your current book depend on being the only party who can find and vet a candidate, and what happens to them the day a client can do that themselves?"
        },
        "preferable": {
          "text": "A staffing organisation that has repositioned itself as the guarantor of judgment AI cannot yet make: risk, culture fit, and the messy human calls in a placement. It earns margin on accountability, not on access to a candidate database.",
          "question": "What would you have to stop selling this year to credibly start selling judgment instead of access?"
        }
      },
      "climate-regulation": {
        "probable": {
          "text": "Your current staffing model treats sustainability and ESG reporting roles as a niche specialism handled by a small dedicated team. Demand for these profiles keeps outpacing supply because every client-side hiring plan assumed this would stay a side desk.",
          "question": "How much of next year's specialist recruiting capacity is still sized for ESG as a niche rather than a mainstream requirement?"
        },
        "plausible": {
          "text": "The assumption that breaks: that climate and sustainability reporting obligations apply mainly to large listed clients. Once supply-chain reporting duties cascade down to their suppliers, demand for these skills moves from a segment you serve well into a market-wide shortage you're not resourced for.",
          "question": "If reporting obligations cascade to your clients' suppliers within the next few years, does your current bench of specialists scale, or does it break?"
        },
        "preferable": {
          "text": "A staffing firm that has built a standing pipeline of climate-literate technical and compliance talent ahead of the regulatory wave, rather than scrambling once clients call. It treats this shortage as a market position to own, not a fire to put out.",
          "question": "What would it take to start building that pipeline now, before the demand spike makes the same talent three times harder to find?"
        }
      },
      "talent-culture": {
        "probable": {
          "text": "Your retention strategy still assumes permanent employment is the default and flex work is the exception you manage around it. Attrition among your best consultants keeps climbing as the labour market normalises flexible, project-based careers as the primary choice, not the fallback.",
          "question": "What in your current retention budget still assumes permanent placement is the finish line rather than one option among several?"
        },
        "plausible": {
          "text": "The assumption that breaks: that skilled professionals need an employer, staffing firm, or platform to find their next role. As direct peer networks and reputation systems mature, the intermediary function your business is built on becomes optional for the most in-demand candidates first.",
          "question": "If your best candidates could get their next three assignments without going through you, what would you still have to offer them?"
        },
        "preferable": {
          "text": "A staffing organisation that has turned itself into the community top talent chooses to stay close to, not because it controls access to jobs, but because it invests visibly in their development and standing in the market. Loyalty is earned through relevance, not through gatekeeping.",
          "question": "What would you have to invest in this year to become a community candidates want to stay in, rather than a gate they pass through?"
        }
      },
      "geopolitical-disruption": {
        "probable": {
          "text": "Your cross-border staffing plans still assume freedom of movement and mutual recognition of qualifications within Europe will hold roughly as they do today. Every workforce plan for scarce technical talent implicitly bets on being able to source across borders without friction.",
          "question": "How exposed is your technical talent pipeline if cross-border mobility within Europe gets meaningfully harder in the next few years?"
        },
        "plausible": {
          "text": "The assumption that breaks: that political tension stays at the level of trade and tariffs and doesn't reach labour mobility itself. If a member state tightens work permit rules for strategic sectors, the scarce technical profiles you rely on sourcing internationally suddenly concentrate in fewer, harder-to-access markets.",
          "question": "If a key sourcing country tightened work permits for technical roles tomorrow, which client commitments would you not be able to keep?"
        },
        "preferable": {
          "text": "A staffing firm that has deliberately diversified its sourcing geography and built domestic upskilling pathways for scarce technical roles, so no single border closure can stall a client's growth plan. It treats geographic concentration as a risk to manage, not a convenience to exploit.",
          "question": "Which single country or region does your technical sourcing depend on most, and what's the plan if that door narrows?"
        }
      }
    },
    "infrastructure-public": {
      "ai-automation": {
        "probable": {
          "text": "Your maintenance and operations planning still assumes AI-driven predictive tools are a pilot running alongside existing inspection regimes, not yet a replacement for them. Budget and headcount plans for the next asset cycle are built as if that pilot phase continues indefinitely.",
          "question": "Which part of your current asset management budget still assumes predictive AI stays a pilot rather than becoming the primary method within this asset cycle?"
        },
        "plausible": {
          "text": "The assumption that breaks: that public trust in automated decisions about safety-critical infrastructure builds at the same pace as the technology improves. If a single high-profile automation failure elsewhere triggers political demand for human sign-off on every AI-flagged risk, the efficiency case for automation stalls regardless of how good the models are.",
          "question": "If public and political tolerance for AI-driven safety decisions dropped sharply tomorrow, what would you have to reverse in your current rollout plan?"
        },
        "preferable": {
          "text": "An organisation that has built AI-assisted maintenance with a visible, explainable chain of human accountability from the start, so trust grows alongside capability instead of lagging behind it. It treats explainability as core infrastructure, not a compliance afterthought.",
          "question": "Where in your current automation roadmap would you have to slow down now to make the human accountability chain visible before you scale it?"
        }
      },
      "climate-regulation": {
        "probable": {
          "text": "Your long-term asset investment plans still assume the current climate resilience standards for rail, grid, and water infrastructure will only tighten gradually. Capital planning cycles that run 15 to 20 years are being built on today's regulatory baseline, not tomorrow's.",
          "question": "Which multi-decade asset investment already underway assumes today's climate resilience standard holds for its full lifespan?"
        },
        "plausible": {
          "text": "The assumption that breaks: that extreme weather events stay within the design tolerances your infrastructure was built for. Once a single severe event exceeds those tolerances in a way that causes public harm, resilience standards can be rewritten faster than your capital cycle can absorb, turning compliant assets into liabilities overnight.",
          "question": "If resilience standards were rewritten within the next two years following a major weather event, which of your current assets would move from compliant to exposed?"
        },
        "preferable": {
          "text": "An organisation that treats climate resilience as a standing input to every capital decision rather than a compliance threshold to clear, building in margin ahead of regulation instead of scrambling to meet it. It shapes the next standard instead of just absorbing it.",
          "question": "Where could you build resilience margin into a current capital decision now, ahead of the standard that will eventually require it?"
        }
      },
      "talent-culture": {
        "probable": {
          "text": "Your workforce planning still assumes the specialist engineers who keep aging infrastructure running will be replaceable through the same apprenticeship and hiring pipelines that worked a decade ago. Retirement waves in these technical roles are approaching faster than replacement pipelines are being rebuilt.",
          "question": "What is your actual timeline for replacing the specialist knowledge that leaves with your next wave of retiring engineers?"
        },
        "plausible": {
          "text": "The assumption that breaks: that critical technical knowledge about legacy systems stays documented and transferable as people retire. Once enough of that knowledge exists only in the heads of a shrinking group of veteran engineers, a single wave of departures can create an operational gap regulation and budget can't fix quickly.",
          "question": "How much of your critical operational knowledge exists only in a handful of people's heads right now, and what happens the year they all leave?"
        },
        "preferable": {
          "text": "An organisation that has made knowledge transfer from veteran specialists a funded, tracked priority rather than an informal hope, and that has redesigned technical roles to attract people who didn't grow up wanting to work in infrastructure. It builds its future workforce on purpose, not on nostalgia for the last one.",
          "question": "What would it take to fund knowledge transfer from your veteran specialists as seriously as you fund the assets they maintain?"
        }
      },
      "geopolitical-disruption": {
        "probable": {
          "text": "Your supply chain and procurement plans for critical infrastructure components still assume the current mix of international suppliers stays available and affordable. Long procurement cycles for specialised equipment are being locked in as if today's trade relationships are stable for their full duration.",
          "question": "Which critical infrastructure component currently on order assumes a supplier relationship that could become politically unavailable before delivery?"
        },
        "plausible": {
          "text": "The assumption that breaks: that critical infrastructure components remain a purely commercial procurement matter, insulated from geopolitical leverage. Once a supplying country treats access to specialised parts as a point of political pressure, lead times and prices for infrastructure-critical equipment can shift within a single budget cycle.",
          "question": "If a key supplier country restricted export of a critical component next year, which infrastructure project would stall first?"
        },
        "preferable": {
          "text": "An organisation that has mapped its critical dependencies and deliberately built redundancy into sourcing for the components that matter most, treating supply concentration as a strategic risk owned at board level, not a procurement detail. It's ready to make the harder, more expensive sourcing choice before it's forced to.",
          "question": "Which single-source dependency would you fund a redundant supplier for today, if you treated it as a board-level risk rather than a procurement line?"
        }
      }
    }
  },
  "sliders": {
    "probable": "How prepared is your organisation for this future?",
    "plausible": "How prepared is your organisation for this future?",
    "preferable": "How actively are you shaping this future?"
  },
  "signals": [
    {
      "min": 3,
      "max": 7,
      "name": "Observing",
      "stance": "This team tracks what's changing and has real instincts about where pressure is building, but those signals mostly stay in individual heads or side conversations rather than shaping the plan on the table. The current strategy is still built primarily on extrapolating what has worked so far. That's a completely normal place for a serious leadership team to be: most organisations run this way until something forces the future onto the agenda deliberately.",
      "nextStep": "Start by making the futures conversation explicit rather than implicit: a Cone of Possibilities session with the leadership team, mapping the probable future you're currently assuming against the plausible and preferable alternatives, gives the team a shared picture to react to together."
    },
    {
      "min": 8,
      "max": 11,
      "name": "Anticipating",
      "stance": "This team already asks what-if questions and has likely named at least one assumption that could break. What's missing is a repeatable way to turn that awareness into decisions before the pressure becomes urgent. Right now, futures thinking depends on a few people remembering to raise it, rather than being built into how the team plans.",
      "nextStep": "Build the capability into the leadership team itself through the Futures Ready Leadership programme, grounded in Minkowski's 7 Practices, so anticipating weak signals becomes a shared discipline rather than something a few people carry alone."
    },
    {
      "min": 12,
      "max": 15,
      "name": "Futures Ready",
      "stance": "This team doesn't just see the futures coming, it has already started shaping decisions around them. The gap now isn't awareness, it's making sure today's budgets, hires, and commitments actually hold up against the preferable future you've named, rather than quietly drifting back toward the probable one.",
      "nextStep": "Put that alignment to the test: a working session to stress-test your preferable future against your current bets, or activation through SCOPE for Change, turns the future you've chosen into the plan you're actually funding."
    }
  ]
};
