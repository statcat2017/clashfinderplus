const state = {
  data: null,
  dayId: null,
  query: "",
  stageId: "all",
  starredOnly: false,
  starred: new Set(JSON.parse(localStorage.getItem("cfplus-starred") || "[]")),
  suggested: new Set(),
  antiSuggested: new Set(),
  genreByName: new Map(),
};

const els = {
  title: document.querySelector("#event-title"),
  source: document.querySelector("#source-link"),
  editDate: document.querySelector("#edit-date"),
  search: document.querySelector("#search"),
  stageFilter: document.querySelector("#stage-filter"),
  starredOnly: document.querySelector("#starred-only"),
  dayTabs: document.querySelector("#day-tabs"),
  timeline: document.querySelector("#timeline"),
  actList: document.querySelector("#act-list"),
  actCount: document.querySelector("#act-count"),
  clashCount: document.querySelector("#clash-count"),
  stageCount: document.querySelector("#stage-count"),
  listHint: document.querySelector("#list-hint"),
  starredCount: document.querySelector("#starred-count"),
  starredList: document.querySelector("#starred-list"),
  recommendationCount: document.querySelector("#recommendation-count"),
};

async function init() {
  const response = await fetch("schedule.json");
  state.data = await response.json();
  await loadGenreData();
  state.dayId = state.data.days[0]?.id;

  els.title.textContent = state.data.title;
  els.source.href = state.data.sourceUrl;
  els.editDate.textContent = state.data.editDate ? `Edited ${state.data.editDate}` : "";

  for (const stage of state.data.stages) {
    const option = document.createElement("option");
    option.value = stage.id;
    option.textContent = stage.name;
    els.stageFilter.append(option);
  }

  bindEvents();
  render();
}

function bindEvents() {
  els.search.addEventListener("input", (event) => {
    state.query = event.target.value.trim().toLowerCase();
    render();
  });

  els.stageFilter.addEventListener("change", (event) => {
    state.stageId = event.target.value;
    render();
  });

  els.starredOnly.addEventListener("change", (event) => {
    state.starredOnly = event.target.checked;
    render();
  });
}

function filteredActs() {
  return state.data.acts.filter((act) => {
    const haystack = `${act.name} ${act.stageName} ${act.dayName} ${act.time}`.toLowerCase();
    return (
      act.dayId === state.dayId &&
      (state.stageId === "all" || act.stageId === state.stageId) &&
      (!state.query || haystack.includes(state.query)) &&
      (!state.starredOnly || state.starred.has(act.id))
    );
  });
}

function render() {
  const acts = filteredActs();
  const starredActs = getStarredActs();
  const recommendations = getRecommendations(starredActs);
  const antiSuggestions = getAntiSuggestions(starredActs, recommendations);
  state.suggested = new Set(recommendations.map((act) => act.id));
  state.antiSuggested = new Set(antiSuggestions.map((act) => act.id));

  renderDayTabs();
  renderTimeline(acts);
  renderActList();
  renderPlanner(starredActs, recommendations);
  renderSummary(acts);
}

function renderDayTabs() {
  els.dayTabs.replaceChildren();
  for (const day of state.data.days) {
    const button = document.createElement("button");
    button.className = "day-tab";
    button.type = "button";
    button.textContent = day.name;
    button.setAttribute("aria-selected", String(day.id === state.dayId));
    button.addEventListener("click", () => {
      state.dayId = day.id;
      render();
    });
    els.dayTabs.append(button);
  }
}

function renderTimeline(acts) {
  els.timeline.replaceChildren();
  const stages = activeStages(acts);
  if (!stages.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No acts match the current filters.";
    els.timeline.append(empty);
    return;
  }

  const rowHeight = 92;
  const stageWidth = Number.parseFloat(
    getComputedStyle(document.documentElement).getPropertyValue("--stage-width")
  );
  const gridWidth = stages.length * stageWidth;

  const selectedDay = state.data.days.find((day) => day.id === state.dayId);
  renderDaySegment(selectedDay, acts, stages, rowHeight, stageWidth, gridWidth);
}

function renderDaySegment(day, acts, stages, rowHeight, stageWidth, gridWidth) {
  const segment = document.createElement("section");
  segment.className = "day-segment";
  segment.id = `segment-${day.id}`;

  const heading = document.createElement("h2");
  heading.className = "day-heading";
  heading.textContent = day.name;
  segment.append(heading);

  if (!acts.length) {
    const empty = document.createElement("div");
    empty.className = "empty day-empty";
    empty.textContent = "No acts match the current filters for this day.";
    segment.append(empty);
    els.timeline.append(segment);
    return;
  }

  const minStart = floorHour(Math.min(...acts.map((act) => act.startMs)));
  const maxEnd = ceilHour(Math.max(...acts.map((act) => act.endMs)));
  const span = maxEnd - minStart;
  const timelineHeight = Math.max(((span / (60 * 60 * 1000)) * rowHeight), 260);

  const dayGrid = document.createElement("div");
  dayGrid.className = "day-grid";

  const axis = document.createElement("div");
  axis.className = "time-axis";
  axis.style.height = `${timelineHeight}px`;
  for (let tick = minStart; tick <= maxEnd; tick += 60 * 60 * 1000) {
    const tickEl = document.createElement("span");
    tickEl.className = "tick";
    tickEl.style.top = `${((tick - minStart) / span) * 100}%`;
    tickEl.textContent = formatTime(tick);
    axis.append(tickEl);
  }
  dayGrid.append(axis);

  const grid = document.createElement("div");
  grid.className = "stage-grid";
  grid.style.height = `${timelineHeight}px`;
  grid.style.width = `${gridWidth}px`;

  stages.forEach((stage, index) => {
    const column = document.createElement("div");
    column.className = "stage-column";
    column.style.width = `${stageWidth}px`;
    column.style.left = `${index * stageWidth}px`;

    const label = document.createElement("div");
    label.className = "stage-label";
    label.textContent = stage.name;
    column.append(label);

    acts
      .filter((act) => act.stageId === stage.id)
      .sort((a, b) => a.startMs - b.startMs)
      .forEach((act) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = `act-card ${getActStatusClass(act)}`.trim();
        card.style.top = `${((act.startMs - minStart) / span) * 100}%`;
        card.style.height = `${((act.endMs - act.startMs) / span) * 100}%`;
        card.title = `${act.name} · ${act.stageName} · ${act.time}`;
        card.innerHTML = `<span class="act-name"></span><span class="act-time"></span>`;
        card.querySelector(".act-name").textContent = act.name;
        card.querySelector(".act-time").textContent = act.time;
        card.addEventListener("click", () => toggleStar(act.id));
        column.append(card);
      });

    grid.append(column);
  });
  dayGrid.append(grid);
  segment.append(dayGrid);
  els.timeline.append(segment);
}

function renderActList() {
  els.actList.replaceChildren();
  const listedActs = state.data.acts
    .filter((act) => act.name.toLowerCase() !== "tbc")
    .sort((a, b) => a.name.localeCompare(b.name) || a.startMs - b.startMs);

  els.listHint.textContent = listedActs.length ? "Click a star to mark must-sees" : "";

  for (const act of listedActs) {
    const item = document.createElement("article");
    item.className = `act-list-item ${getActStatusClass(act)}`.trim();

    const details = document.createElement("div");
    const name = document.createElement("strong");
    const meta = document.createElement("span");
    const badge = document.createElement("em");
    name.textContent = act.name;
    meta.textContent = actMeta(act);
    badge.textContent = state.starred.has(act.id) ? "Starred" : "Suggested";
    details.append(name, meta, badge);

    const button = document.createElement("button");
    button.className = "star-button";
    button.type = "button";
    button.textContent = state.starred.has(act.id) ? "★" : "☆";
    button.setAttribute("aria-label", `Star ${act.name}`);
    button.addEventListener("click", () => toggleStar(act.id));

    item.append(details, button);
    els.actList.append(item);
  }
}

function renderPlanner(starredActs, recommendations) {
  const runningOrder = [...starredActs, ...recommendations].sort(
    (a, b) => a.startMs - b.startMs || a.name.localeCompare(b.name)
  );

  els.starredCount.textContent = starredActs.length;
  els.recommendationCount.textContent = recommendations.length;

  if (starredActs.length < 3) {
    const remaining = 3 - starredActs.length;
    renderRailList(els.starredList, starredActs, "Star acts from the timetable or index to build your plan.");
    appendRailMessage(
      els.starredList,
      `Star ${remaining} more ${remaining === 1 ? "act" : "acts"} to unlock suggested slots.`
    );
  } else {
    renderRailList(els.starredList, runningOrder, "No route yet.");
  }
}

function renderRailList(container, acts, emptyText) {
  container.replaceChildren();
  if (!acts.length) {
    renderRailMessage(container, emptyText);
    return;
  }

  for (const act of acts) {
    const item = document.createElement("article");
    item.className = `rail-item ${getActStatusClass(act)}`.trim();

    const details = document.createElement("div");
    const name = document.createElement("strong");
    const meta = document.createElement("span");
    name.textContent = act.name;
    meta.textContent = actMeta(act);
    details.append(name, meta);

    const button = document.createElement("button");
    button.className = "star-button";
    button.type = "button";
    button.textContent = state.starred.has(act.id) ? "★" : "☆";
    button.setAttribute("aria-label", `${state.starred.has(act.id) ? "Unstar" : "Star"} ${act.name}`);
    button.addEventListener("click", () => toggleStar(act.id));

    item.append(details, button);
    container.append(item);
  }
}

function renderRailMessage(container, text) {
  container.replaceChildren();
  appendRailMessage(container, text);
}

function appendRailMessage(container, text) {
  const empty = document.createElement("div");
  empty.className = "rail-empty";
  empty.textContent = text;
  container.append(empty);
}

function renderSummary(acts) {
  const stageIds = new Set(acts.map((act) => act.stageId));
  els.actCount.textContent = acts.length;
  els.stageCount.textContent = stageIds.size;
  els.clashCount.textContent = countStarredClashes();
}

function activeStages(acts) {
  const stageIds = new Set(acts.map((act) => act.stageId));
  return state.data.stages.filter((stage) => stageIds.has(stage.id));
}

function getStarredActs() {
  return state.data.acts
    .filter((act) => state.starred.has(act.id))
    .sort((a, b) => a.startMs - b.startMs || a.name.localeCompare(b.name));
}

function getRecommendations(starredActs) {
  return getScoredCandidates(starredActs)
    .filter((act) => act.recommendationScore > 0)
    .sort((a, b) => b.recommendationScore - a.recommendationScore || a.startMs - b.startMs)
    .slice(0, 8);
}

function getAntiSuggestions(starredActs, recommendations) {
  if (starredActs.length < 3) return [];
  const recommendationIds = new Set(recommendations.map((act) => act.id));

  return getScoredCandidates(starredActs)
    .filter((act) => !recommendationIds.has(act.id))
    .sort(
      (a, b) =>
        a.recommendationScore - b.recommendationScore ||
        b.distanceFromStars - a.distanceFromStars ||
        a.startMs - b.startMs
    )
    .slice(0, 8);
}

function getScoredCandidates(starredActs) {
  if (starredActs.length < 3) return [];

  const genreScores = new Map();
  for (const act of starredActs) {
    for (const genre of getActGenres(act)) {
      genreScores.set(genre, (genreScores.get(genre) || 0) + 1);
    }
  }

  return state.data.acts
    .filter((act) => act.name.toLowerCase() !== "tbc")
    .filter((act) => !state.starred.has(act.id))
    .filter((act) => !starredActs.some((starred) => actsOverlap(act, starred)))
    .map((act) => ({
      ...act,
      recommendationScore: genreMatchScore(act, genreScores),
      distanceFromStars: distanceFromStars(act, starredActs),
    }))
}

function getActStatusClass(act) {
  if (state.starred.has(act.id)) return "is-starred";
  if (state.suggested.has(act.id)) return "is-suggested";
  if (state.antiSuggested.has(act.id)) return "is-anti-suggested";
  return "";
}

async function loadGenreData() {
  try {
    const response = await fetch("artist_genres.json", { cache: "no-store" });
    if (!response.ok) return;
    const data = await response.json();
    state.genreByName = new Map(
      data.artists.map((artist) => [artist.name.toLowerCase(), artist.genres || []])
    );
  } catch {
    state.genreByName = new Map();
  }
}

function getActGenres(act) {
  return state.genreByName.get(act.name.toLowerCase()) || [];
}

function genreMatchScore(act, genreScores) {
  return getActGenres(act).reduce((score, genre) => score + (genreScores.get(genre) || 0), 0);
}

function actMeta(act) {
  const genres = getActGenres(act).slice(0, 3);
  return [`${act.dayName} · ${act.time} · ${act.stageName}`, genres.join(", ")].filter(Boolean).join(" · ");
}

function distanceFromStars(act, starredActs) {
  return Math.min(...starredActs.map((starred) => Math.abs(act.startMs - starred.startMs) / 60000));
}

function actsOverlap(first, second) {
  return first.dayId === second.dayId && first.startMs < second.endMs && second.startMs < first.endMs;
}

function countStarredClashes() {
  const starredActs = state.data.acts
    .filter((act) => state.starred.has(act.id))
    .sort((a, b) => a.startMs - b.startMs);
  let clashes = 0;

  for (let index = 0; index < starredActs.length; index += 1) {
    for (let next = index + 1; next < starredActs.length; next += 1) {
      if (starredActs[next].startMs >= starredActs[index].endMs) break;
      clashes += 1;
    }
  }

  return clashes;
}

function toggleStar(actId) {
  if (state.starred.has(actId)) {
    state.starred.delete(actId);
  } else {
    state.starred.add(actId);
  }
  localStorage.setItem("cfplus-starred", JSON.stringify([...state.starred]));
  render();
}

function floorHour(value) {
  const date = new Date(value);
  date.setMinutes(0, 0, 0);
  return date.getTime();
}

function ceilHour(value) {
  const date = new Date(value);
  date.setMinutes(0, 0, 0);
  if (date.getTime() < value) date.setHours(date.getHours() + 1);
  return date.getTime();
}

function formatTime(value) {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Europe/London",
  }).format(new Date(value));
}

init().catch((error) => {
  els.title.textContent = "Could not load schedule";
  els.timeline.innerHTML = `<div class="empty">${error.message}</div>`;
});
