const gameTitle = document.getElementById("game-title");
const gameIntro = document.getElementById("game-intro");
const gameDisclaimer = document.getElementById("game-disclaimer");
const statusLine = document.getElementById("status-line");
const startButton = document.getElementById("start-button");
const gameArea = document.getElementById("game-area");

const state = {
  content: null,
  caseIndex: 0,
  experience: 0,
  capacity: {},
  caseState: null,
};

function rankForExperience(experience, thresholds) {
  let rank = "Trainee";
  Object.entries(thresholds)
    .sort((a, b) => a[1] - b[1])
    .forEach(([label, minimum]) => {
      if (experience >= minimum) {
        rank = label;
      }
    });
  return rank;
}

function difficultyBonus(difficulty) {
  const bonuses = { easy: 5, intermediate: 10, advanced: 15 };
  return bonuses[String(difficulty || "").toLowerCase()] || 5;
}

function htmlEscape(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderCase() {
  const currentCase = state.content.cases[state.caseIndex];
  const caseState = state.caseState;
  const evidenceLookup = new Map(
    currentCase.evidence.map((evidence) => [evidence.id, evidence])
  );

  const availableActions = currentCase.actions.filter(
    (action) => !caseState.actionsTaken.includes(action.key)
  );

  const discoveredEvidence = caseState.discoveredEvidence
    .map((id) => evidenceLookup.get(id))
    .filter(Boolean)
    .map((evidence) => `<li>${htmlEscape(evidence.description)}</li>`)
    .join("");

  gameArea.innerHTML = `
    <h2>${htmlEscape(currentCase.title)} (${htmlEscape(currentCase.difficulty)})</h2>
    <p>${htmlEscape(currentCase.opening)}</p>
    <p><strong>Characters:</strong> ${htmlEscape(currentCase.characters.join(", "))}</p>
    <p><strong>Entities:</strong> ${htmlEscape(currentCase.entities.join(", "))}</p>
    <p><strong>Resources:</strong> Time ${caseState.resources.time} | Budget ${caseState.resources.budget} | Energy ${caseState.resources.energy}</p>
    <h3>Evidence discovered</h3>
    <ul>${discoveredEvidence || "<li>No evidence discovered yet</li>"}</ul>
    <h3>Actions</h3>
    <div id="actions"></div>
    <div id="conclusions"></div>
  `;

  const actionsContainer = document.getElementById("actions");
  availableActions.forEach((action) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `[${action.key}] ${action.text}`;
    button.addEventListener("click", () => selectAction(action.key));
    actionsContainer.appendChild(button);
  });

  const submitButton = document.createElement("button");
  submitButton.type = "button";
  submitButton.textContent = "Submit final conclusion";
  submitButton.addEventListener("click", renderConclusions);
  actionsContainer.appendChild(submitButton);

  const giveUpButton = document.createElement("button");
  giveUpButton.type = "button";
  giveUpButton.textContent = "Give up case";
  giveUpButton.addEventListener("click", () => finishCase(true, null));
  actionsContainer.appendChild(giveUpButton);
}

function selectAction(actionKey) {
  const currentCase = state.content.cases[state.caseIndex];
  const action = currentCase.actions.find((item) => item.key === actionKey);
  if (!action || state.caseState.actionsTaken.includes(actionKey)) {
    return;
  }

  state.caseState.actionsTaken.push(actionKey);
  Object.entries(action.costs).forEach(([resource, value]) => {
    state.caseState.resources[resource] -= value;
  });
  action.reveals_evidence.forEach((evidenceId) => {
    if (!state.caseState.discoveredEvidence.includes(evidenceId)) {
      state.caseState.discoveredEvidence.push(evidenceId);
    }
  });
  if (
    !state.caseState.riskIndicators.includes(action.risk_indicator) &&
    action.risk_indicator
  ) {
    state.caseState.riskIndicators.push(action.risk_indicator);
  }
  if (Object.values(state.caseState.resources).some((value) => value <= 0)) {
    state.caseState.exhaustedBeforeSubmission = true;
  }

  renderCase();
}

function renderConclusions() {
  const currentCase = state.content.cases[state.caseIndex];
  const conclusionsContainer = document.getElementById("conclusions");
  conclusionsContainer.innerHTML = "<h3>Conclusions</h3>";

  currentCase.conclusions.forEach((conclusion) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `[${conclusion.key}] ${conclusion.label}`;
    button.addEventListener("click", () => finishCase(false, conclusion.key));
    conclusionsContainer.appendChild(button);
  });
}

function finishCase(gaveUp, selectedConclusion) {
  const currentCase = state.content.cases[state.caseIndex];
  const evidenceLookup = new Map(
    currentCase.evidence.map((evidence) => [evidence.id, evidence])
  );

  const isCorrect = !gaveUp && selectedConclusion === currentCase.correct_conclusion;
  const discoveredEvidence = state.caseState.discoveredEvidence
    .map((id) => evidenceLookup.get(id))
    .filter(Boolean);
  const redFlagsIdentified = discoveredEvidence.filter(
    (evidence) => evidence.is_red_flag_easy
  ).length;
  const resourceLeft =
    Math.max(state.caseState.resources.time, 0) +
    Math.max(state.caseState.resources.budget, 0) +
    Math.max(state.caseState.resources.energy, 0);
  const baseScore = isCorrect ? 60 : 20;
  let score =
    baseScore +
    state.caseState.discoveredEvidence.length * 3 +
    redFlagsIdentified * 5;
  if (isCorrect) {
    score += Math.floor(resourceLeft / 8);
  }

  let xpGained = 0;
  if (isCorrect && !state.caseState.exhaustedBeforeSubmission) {
    xpGained = difficultyBonus(currentCase.difficulty);
    state.experience += xpGained;
    Object.keys(state.capacity).forEach((resource) => {
      state.capacity[resource] += xpGained;
    });
  }

  const selected = currentCase.conclusions.find(
    (conclusion) => conclusion.key === selectedConclusion
  );

  gameArea.innerHTML = `
    <h2>Case result</h2>
    <p><strong>Outcome:</strong> ${
      gaveUp ? "Case abandoned" : htmlEscape(selected ? selected.label : "No conclusion selected")
    }</p>
    <p><strong>Actual activity:</strong> ${htmlEscape(currentCase.actual_activity)}</p>
    <p><strong>Key red flags:</strong> ${htmlEscape(currentCase.key_red_flags.join("; "))}</p>
    <p><strong>Recommended approach:</strong> ${htmlEscape(currentCase.recommended_approach)}</p>
    <p><strong>Case score:</strong> ${score} | <strong>Experience gained:</strong> ${xpGained}</p>
  `;

  const nextButton = document.createElement("button");
  nextButton.type = "button";
  nextButton.textContent =
    state.caseIndex < state.content.cases.length - 1 ? "Next case" : "Finish game";
  nextButton.addEventListener("click", () => {
    state.caseIndex += 1;
    if (state.caseIndex >= state.content.cases.length) {
      renderGameComplete();
      return;
    }
    state.caseState = {
      resources: { ...state.capacity },
      exhaustedBeforeSubmission: false,
      discoveredEvidence: [],
      actionsTaken: [],
      riskIndicators: [],
    };
    renderCase();
  });
  gameArea.appendChild(nextButton);
}

function renderGameComplete() {
  const rank = rankForExperience(state.experience, state.content.rank_thresholds);
  gameArea.innerHTML = `
    <h2>Game complete</h2>
    <p>You completed all available cases.</p>
    <p><strong>Final experience:</strong> ${state.experience}</p>
    <p><strong>Rank:</strong> ${htmlEscape(rank)}</p>
  `;
}

function startGame() {
  state.caseIndex = 0;
  state.experience = 0;
  state.capacity = { ...state.content.starting_resources };
  state.caseState = {
    resources: { ...state.capacity },
    exhaustedBeforeSubmission: false,
    discoveredEvidence: [],
    actionsTaken: [],
    riskIndicators: [],
  };
  renderCase();
}

fetch("game_content.json")
  .then((response) => {
    if (!response.ok) {
      throw new Error("Unable to load game content");
    }
    return response.json();
  })
  .then((content) => {
    state.content = content;
    gameTitle.textContent = content.title || "AML Detective";
    gameIntro.textContent = content.intro || "";
    gameDisclaimer.textContent = `Disclaimer: ${content.disclaimer || ""}`;
    statusLine.textContent = "Game ready.";
    startButton.disabled = false;
    startButton.addEventListener("click", startGame);
  })
  .catch((error) => {
    statusLine.textContent = `Failed to load game content: ${error.message}`;
  });
