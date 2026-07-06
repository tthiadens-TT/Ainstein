/*
 * What's Your Future? -- facilitator instrument.
 * Vanilla JS. Reads only from SCENARIO_DATA (data.js). No frameworks, no build step.
 */

(function () {
  "use strict";

  var ZONES = ["probable", "plausible", "preferable"];
  var ZONE_LABELS = { probable: "Probable", plausible: "Plausible", preferable: "Preferable" };
  var ZONE_MEANINGS = {
    probable: "The future your current plans assume",
    plausible: "What could happen if one system assumption breaks",
    preferable: "The future worth actively shaping"
  };

  // Session state
  var state = {
    organisation: "",
    sectorId: null,
    themeId: null,
    scenarioIndex: 0, // index into ZONES while stepping through step 2
    sliderValues: { probable: 3, plausible: 3, preferable: 3 },
    combo: null // resolved scenario object for the chosen sector/theme, or null if missing
  };

  // Cached elements
  var el = {};

  document.addEventListener("DOMContentLoaded", init);

  function init() {
    cacheElements();
    renderChoiceGrid(el.sectorGrid, SCENARIO_DATA.sectors, "sectorId");
    renderChoiceGrid(el.themeGrid, SCENARIO_DATA.themes, "themeId");
    renderSliders();

    el.btnBegin.addEventListener("click", onBegin);
    el.btnContinue.addEventListener("click", onContinueScenario);
    el.btnBackFromUnavailable.addEventListener("click", onBackFromUnavailable);
    el.btnSeeSignal.addEventListener("click", onSeeSignal);
    el.btnCopySummary.addEventListener("click", onCopySummary);
    el.btnPrint.addEventListener("click", onPrint);
    el.linkStartAgain.addEventListener("click", onStartAgain);
    el.inputOrganisation.addEventListener("input", function () {
      state.organisation = el.inputOrganisation.value.trim();
    });
  }

  function cacheElements() {
    el.app = document.getElementById("app");

    el.stepContext = document.getElementById("step-context");
    el.stepScenario = document.getElementById("step-scenario");
    el.stepPulse = document.getElementById("step-pulse");
    el.stepSignal = document.getElementById("step-signal");

    el.inputOrganisation = document.getElementById("input-organisation");
    el.sectorGrid = document.getElementById("sector-grid");
    el.themeGrid = document.getElementById("theme-grid");
    el.btnBegin = document.getElementById("btn-begin");

    el.zoneLabel = document.getElementById("zone-label");
    el.zoneMeaning = document.getElementById("zone-meaning");
    el.scenarioText = document.getElementById("scenario-text");
    el.leadershipQuestion = document.getElementById("leadership-question");
    el.btnContinue = document.getElementById("btn-continue");
    el.unavailableCombo = document.getElementById("unavailable-combo");
    el.btnBackFromUnavailable = document.getElementById("btn-back-from-unavailable");
    el.coneIndicator = document.getElementById("cone-indicator");

    el.sliderList = document.getElementById("slider-list");
    el.btnSeeSignal = document.getElementById("btn-see-signal");

    el.signalName = document.getElementById("signal-name");
    el.signalStance = document.getElementById("signal-stance");
    el.signalNextStep = document.getElementById("signal-next-step");
    el.signalMeta = document.getElementById("signal-meta");
    el.signalRecap = document.getElementById("signal-recap");
    el.btnCopySummary = document.getElementById("btn-copy-summary");
    el.btnPrint = document.getElementById("btn-print");
    el.copyConfirmation = document.getElementById("copy-confirmation");
    el.linkStartAgain = document.getElementById("link-start-again");

    el.clipboardFallback = document.getElementById("clipboard-fallback");
    el.printSheet = document.getElementById("print-sheet");
  }

  // ---------- STEP 1: CONTEXT ----------

  function renderChoiceGrid(container, items, stateKey) {
    items.forEach(function (item) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "choice-card";
      btn.textContent = item.label;
      btn.setAttribute("data-id", item.id);
      btn.setAttribute("aria-pressed", "false");
      btn.addEventListener("click", function () {
        var siblings = container.querySelectorAll(".choice-card");
        siblings.forEach(function (s) {
          s.classList.remove("is-selected");
          s.setAttribute("aria-pressed", "false");
        });
        btn.classList.add("is-selected");
        btn.setAttribute("aria-pressed", "true");
        state[stateKey] = item.id;
        updateBeginButton();
      });
      container.appendChild(btn);
    });
  }

  function updateBeginButton() {
    el.btnBegin.disabled = !(state.sectorId && state.themeId);
  }

  function onBegin() {
    state.organisation = el.inputOrganisation.value.trim();
    state.combo = getCombo(state.sectorId, state.themeId);
    state.scenarioIndex = 0;

    goToStep(el.stepContext, el.stepScenario);

    if (!state.combo) {
      showUnavailableCombo();
    } else {
      renderScenarioScreen();
    }
  }

  function getCombo(sectorId, themeId) {
    var bySector = SCENARIO_DATA.scenarios[sectorId];
    if (!bySector) return null;
    var combo = bySector[themeId];
    if (!combo) return null;
    return combo;
  }

  // ---------- STEP 2: SCENARIOS ----------

  function showUnavailableCombo() {
    el.unavailableCombo.hidden = false;
    el.zoneLabel.hidden = true;
    el.zoneMeaning.hidden = true;
    el.scenarioText.hidden = true;
    el.leadershipQuestion.hidden = true;
    el.btnContinue.hidden = true;
    el.coneIndicator.hidden = true;
  }

  function onBackFromUnavailable() {
    el.unavailableCombo.hidden = true;
    el.zoneLabel.hidden = false;
    el.zoneMeaning.hidden = false;
    el.scenarioText.hidden = false;
    el.leadershipQuestion.hidden = false;
    el.btnContinue.hidden = false;
    el.coneIndicator.hidden = false;
    goToStep(el.stepScenario, el.stepContext);
  }

  function renderScenarioScreen() {
    var zone = ZONES[state.scenarioIndex];
    var scenario = state.combo[zone];

    el.zoneLabel.textContent = ZONE_LABELS[zone];
    el.zoneMeaning.textContent = ZONE_MEANINGS[zone];
    el.scenarioText.textContent = scenario.text;
    el.leadershipQuestion.textContent = scenario.question;

    updateConeIndicator(state.scenarioIndex);

    el.btnContinue.textContent = state.scenarioIndex < ZONES.length - 1 ? "Continue" : "Continue to pulse";
  }

  function updateConeIndicator(index) {
    var shapes = el.coneIndicator.querySelectorAll(".cone-shape, .cone-divider");
    el.coneIndicator.setAttribute("data-active-zone", ZONES[index]);
  }

  function onContinueScenario() {
    if (state.scenarioIndex < ZONES.length - 1) {
      state.scenarioIndex += 1;
      renderScenarioScreen();
    } else {
      updateSliderRecaps();
      goToStep(el.stepScenario, el.stepPulse);
    }
  }

  // ---------- STEP 3: PULSE ----------

  function renderSliders() {
    ZONES.forEach(function (zone) {
      var row = document.createElement("div");
      row.className = "slider-row";

      var labelId = "slider-label-" + zone;
      var inputId = "slider-input-" + zone;
      var valueId = "slider-value-" + zone;

      var recapEl = document.createElement("p");
      recapEl.className = "slider-row__recap";
      recapEl.id = "slider-recap-" + zone;

      var questionLabel = document.createElement("label");
      questionLabel.className = "slider-row__question";
      questionLabel.setAttribute("for", inputId);
      questionLabel.id = labelId;
      questionLabel.textContent = SCENARIO_DATA.sliders[zone];

      var zoneTag = document.createElement("span");
      zoneTag.className = "slider-row__zone";
      zoneTag.textContent = ZONE_LABELS[zone];

      var controlWrap = document.createElement("div");
      controlWrap.className = "slider-row__control";

      var input = document.createElement("input");
      input.type = "range";
      input.min = "1";
      input.max = "5";
      input.step = "1";
      input.value = String(state.sliderValues[zone]);
      input.id = inputId;
      input.setAttribute("aria-labelledby", labelId);

      var valueOut = document.createElement("output");
      valueOut.className = "slider-row__value";
      valueOut.id = valueId;
      valueOut.textContent = input.value;

      input.addEventListener("input", function () {
        state.sliderValues[zone] = parseInt(input.value, 10);
        valueOut.textContent = input.value;
      });

      controlWrap.appendChild(input);
      controlWrap.appendChild(valueOut);

      row.appendChild(zoneTag);
      row.appendChild(recapEl);
      row.appendChild(questionLabel);
      row.appendChild(controlWrap);

      el.sliderList.appendChild(row);
    });
  }

  function updateSliderRecaps() {
    if (!state.combo) return;
    ZONES.forEach(function (zone) {
      var recapEl = document.getElementById("slider-recap-" + zone);
      var firstSentence = firstSentenceOf(state.combo[zone].text);
      recapEl.textContent = firstSentence;
    });
  }

  function firstSentenceOf(text) {
    if (!text) return "";
    var match = text.match(/^[^.!?]*[.!?]/);
    var sentence = match ? match[0].trim() : text.trim();
    if (sentence.length > 140) {
      sentence = sentence.slice(0, 137).trim() + "...";
    }
    return sentence;
  }

  // ---------- STEP 4: SIGNAL ----------

  function onSeeSignal() {
    updateSliderRecaps();
    renderSignal();
    goToStep(el.stepPulse, el.stepSignal);
  }

  function computeSignal() {
    var total = state.sliderValues.probable + state.sliderValues.plausible + state.sliderValues.preferable;
    var band = SCENARIO_DATA.signals.find(function (s) {
      return total >= s.min && total <= s.max;
    });
    return { total: total, band: band };
  }

  function renderSignal() {
    var result = computeSignal();

    if (result.band) {
      el.signalName.textContent = result.band.name;
      el.signalStance.textContent = result.band.stance;
      el.signalNextStep.textContent = result.band.nextStep;
    } else {
      el.signalName.textContent = "Signal not defined";
      el.signalStance.textContent = "No signal band covers a total of " + result.total + ". Check data.js signal ranges.";
      el.signalNextStep.textContent = "Ask Minkowski to review the signal bands.";
    }

    var sectorLabel = labelFor(SCENARIO_DATA.sectors, state.sectorId);
    var themeLabel = labelFor(SCENARIO_DATA.themes, state.themeId);

    var metaParts = [];
    if (state.organisation) metaParts.push(state.organisation);
    metaParts.push(sectorLabel + " / " + themeLabel);
    metaParts.push("Signals as of " + SCENARIO_DATA.meta.signalsAsOf);
    el.signalMeta.textContent = metaParts.join(" · ");

    el.signalRecap.innerHTML = "";
    ZONES.forEach(function (zone) {
      var item = document.createElement("span");
      item.className = "recap__item";
      item.textContent = ZONE_LABELS[zone] + ": " + state.sliderValues[zone];
      el.signalRecap.appendChild(item);
    });
  }

  function labelFor(list, id) {
    var found = list.find(function (item) { return item.id === id; });
    return found ? found.label : id;
  }

  // ---------- COPY SESSION SUMMARY ----------

  function buildSummaryText() {
    var lines = [];
    var result = computeSignal();
    var sectorLabel = labelFor(SCENARIO_DATA.sectors, state.sectorId);
    var themeLabel = labelFor(SCENARIO_DATA.themes, state.themeId);
    var dateStr = new Date().toLocaleDateString("en-GB", { year: "numeric", month: "long", day: "numeric" });

    lines.push("What's Your Future?");
    if (state.organisation) lines.push("Organisation: " + state.organisation);
    lines.push("Date: " + dateStr);
    lines.push("Sector: " + sectorLabel);
    lines.push("Theme: " + themeLabel);
    lines.push("");

    if (state.combo) {
      ZONES.forEach(function (zone) {
        var scenario = state.combo[zone];
        lines.push(ZONE_LABELS[zone] + ": " + scenario.question);
      });
      lines.push("");
    }

    ZONES.forEach(function (zone) {
      lines.push(SCENARIO_DATA.sliders[zone] + " (" + ZONE_LABELS[zone] + "): " + state.sliderValues[zone]);
    });
    lines.push("");

    if (result.band) {
      lines.push("Signal: " + result.band.name);
      lines.push("Stance: " + result.band.stance);
      lines.push("Where to start: " + result.band.nextStep);
    }
    lines.push("");
    lines.push("Prepared in conversation with Minkowski · minkowski.org");

    return lines.join("\n");
  }

  function onCopySummary() {
    var text = buildSummaryText();

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(showCopyConfirmation, function () {
        fallbackCopy(text);
      });
    } else {
      fallbackCopy(text);
    }
  }

  function fallbackCopy(text) {
    var ta = el.clipboardFallback;
    ta.value = text;
    ta.hidden = false;
    ta.focus();
    ta.select();
    try {
      document.execCommand("copy");
      showCopyConfirmation();
    } catch (e) {
      // Silently fail; no source of truth for a copy mechanism if this fails too.
    }
    ta.hidden = true;
  }

  function showCopyConfirmation() {
    el.copyConfirmation.hidden = false;
    window.setTimeout(function () {
      el.copyConfirmation.hidden = true;
    }, 2000);
  }

  // ---------- PRINT ----------

  function onPrint() {
    buildPrintSheet();
    window.print();
  }

  function buildPrintSheet() {
    var result = computeSignal();
    var sectorLabel = labelFor(SCENARIO_DATA.sectors, state.sectorId);
    var themeLabel = labelFor(SCENARIO_DATA.themes, state.themeId);
    var dateStr = new Date().toLocaleDateString("en-GB", { year: "numeric", month: "long", day: "numeric" });

    var html = "";
    html += '<p class="print-wordmark">MINKOWSKI</p>';
    html += '<h1 class="print-title">What\'s Your Future?</h1>';

    html += '<div class="print-meta">';
    if (state.organisation) html += "<p>Organisation: " + escapeHtml(state.organisation) + "</p>";
    html += "<p>Date: " + escapeHtml(dateStr) + "</p>";
    html += "<p>Sector: " + escapeHtml(sectorLabel) + " &middot; Theme: " + escapeHtml(themeLabel) + "</p>";
    html += "</div>";

    if (state.combo) {
      ZONES.forEach(function (zone) {
        var scenario = state.combo[zone];
        html += '<div class="print-scenario">';
        html += "<p class='print-zone'>" + ZONE_LABELS[zone] + "</p>";
        html += "<p class='print-scenario-text'>" + escapeHtml(scenario.text) + "</p>";
        html += "<p class='print-question'>" + escapeHtml(scenario.question) + "</p>";
        html += "</div>";
      });
    }

    html += '<div class="print-sliders">';
    ZONES.forEach(function (zone) {
      html += "<p>" + ZONE_LABELS[zone] + ": " + state.sliderValues[zone] + " / 5</p>";
    });
    html += "</div>";

    if (result.band) {
      html += '<div class="print-signal">';
      html += "<p class='print-signal-name'>" + escapeHtml(result.band.name) + "</p>";
      html += "<p>" + escapeHtml(result.band.stance) + "</p>";
      html += "<p><strong>Where to start:</strong> " + escapeHtml(result.band.nextStep) + "</p>";
      html += "</div>";
    }

    html += "<p class='print-footer'>minkowski.org</p>";

    el.printSheet.innerHTML = html;
  }

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ---------- NAVIGATION / RESET ----------

  function goToStep(fromEl, toEl) {
    // Move focus out before hiding, so aria-hidden never hides the focused element.
    if (document.activeElement && fromEl.contains(document.activeElement)) {
      document.activeElement.blur();
    }
    fromEl.classList.remove("is-active");
    fromEl.setAttribute("aria-hidden", "true");
    toEl.classList.add("is-active");
    toEl.setAttribute("aria-hidden", "false");
    window.scrollTo(0, 0);
  }

  function onStartAgain(evt) {
    evt.preventDefault();

    state.organisation = "";
    state.sectorId = null;
    state.themeId = null;
    state.scenarioIndex = 0;
    state.sliderValues = { probable: 3, plausible: 3, preferable: 3 };
    state.combo = null;

    el.inputOrganisation.value = "";

    var allCards = el.app.querySelectorAll(".choice-card");
    allCards.forEach(function (c) {
      c.classList.remove("is-selected");
      c.setAttribute("aria-pressed", "false");
    });
    updateBeginButton();

    ZONES.forEach(function (zone) {
      var input = document.getElementById("slider-input-" + zone);
      var valueOut = document.getElementById("slider-value-" + zone);
      input.value = "3";
      valueOut.textContent = "3";
    });

    [el.stepContext, el.stepScenario, el.stepPulse, el.stepSignal].forEach(function (step) {
      step.classList.remove("is-active");
      step.setAttribute("aria-hidden", "true");
    });
    el.stepContext.classList.add("is-active");
    el.stepContext.setAttribute("aria-hidden", "false");

    onBackFromUnavailable_reset();
    window.scrollTo(0, 0);
  }

  function onBackFromUnavailable_reset() {
    el.unavailableCombo.hidden = true;
    el.zoneLabel.hidden = false;
    el.zoneMeaning.hidden = false;
    el.scenarioText.hidden = false;
    el.leadershipQuestion.hidden = false;
    el.btnContinue.hidden = false;
    el.coneIndicator.hidden = false;
  }

})();
