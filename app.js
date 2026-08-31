const EVENT_DATES = ["2026-09-02", "2026-09-03", "2026-09-04"];
const PRESENTATION_URL = "https://pub.confit.atlas.jp/ja/event/jsce2026/presentation/";

let sessions = [];
const sessionsById = new Map();
const searchTextById = new Map();
const categoriesByCode = new Map();
const categoryLabelByQualifiedId = new Map();
let browseCollections = [];
const initialNow = japanNow();
let displayClock = initialNow;

const state = {
  activeTab: "now",
  referenceDate: initialNow.date,
  referenceTime: initialNow.time,
  division: "",
  campus: "",
  theme: "",
  query: "",
  followRealTime: true,
  openSessionIds: new Set(),
  timeGroupOpen: new Map(),
};

const dateFormatter = new Intl.DateTimeFormat("ja-JP", {
  month: "long",
  day: "numeric",
  weekday: "short",
  timeZone: "Asia/Tokyo",
});

function minutes(value) {
  const [hour, minute] = value.split(":").map(Number);
  return hour * 60 + minute;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function sessionStatus(session) {
  if (displayClock.date !== session.date) return null;
  const now = minutes(displayClock.time);
  if (now >= minutes(session.start) && now < minutes(session.end)) {
    return { label: "開催中", className: "is-live" };
  }
  if (minutes(session.start) > now) {
    return { label: `${session.start}開始`, className: "" };
  }
  return { label: "終了", className: "is-ended" };
}

function talkStatus(session, talkIndex) {
  if (displayClock.date !== session.date) return null;
  const now = minutes(displayClock.time);
  const talkStart = minutes(session.talks[talkIndex][0]);
  const talkEnd =
    talkIndex + 1 < session.talks.length
      ? minutes(session.talks[talkIndex + 1][0])
      : minutes(session.end);
  if (now >= talkStart && now < talkEnd) {
    return { label: "開催中", className: "is-current" };
  }
  if (now >= talkEnd) {
    return { label: "終了", className: "is-ended" };
  }
  const nextIndex = session.talks.findIndex((talk) => minutes(talk[0]) > now);
  if (talkIndex === nextIndex) {
    return { label: "次", className: "is-next" };
  }
  return null;
}

function currentTalk(session) {
  const talkIndex = session.talks.findIndex(
    (_, index) => talkStatus(session, index)?.className === "is-current",
  );
  return talkIndex >= 0 ? session.talks[talkIndex] : null;
}

function currentTalkMarkup(session) {
  const talk = currentTalk(session);
  if (!talk) return "";
  return `
    <div class="session-current-talk">
      <span>講演中</span>
      <b>${escapeHtml(talk[0])}</b>
      <span>${escapeHtml(talk[1])} ${escapeHtml(talk[2])}</span>
    </div>`;
}

function talkCategoryMarkup(code) {
  const category = categoriesByCode.get(code);
  if (!category) return "";
  const priorities = ["domain", "phase", "method", "issue", "material"];
  const selected = [];
  for (const axisId of priorities) {
    const labelId = category.labels[axisId]?.[0];
    if (!labelId) continue;
    const label = categoryLabelByQualifiedId.get(`${axisId}:${labelId}`);
    if (label) selected.push({ axisId, label });
    if (selected.length === 3) break;
  }
  if (!selected.length) return "";
  return `<span class="talk-tags">${selected
    .map(
      ({ axisId, label }) =>
        `<span class="talk-tag talk-tag-${escapeHtml(axisId)}">${escapeHtml(label)}</span>`,
    )
    .join("")}</span>`;
}

function talkMarkup(talk, session, talkIndex) {
  const [time, code, title, , authors] = talk;
  const temporalStatus = talkStatus(session, talkIndex);
  const affiliationStart = authors.search(/\s+\(\d+\.\s*/);
  const names = affiliationStart >= 0 ? authors.slice(0, affiliationStart) : authors;
  const affiliations = affiliationStart >= 0 ? authors.slice(affiliationStart).trim() : "";
  return `
    <li class="talk-item ${temporalStatus?.className ?? ""}">
      <a class="talk-link" href="${PRESENTATION_URL}${encodeURIComponent(code)}" target="_blank" rel="noopener noreferrer">
        <span class="talk-time">
          <span>${escapeHtml(time)}</span>
          ${temporalStatus && temporalStatus.className !== "is-ended" ? `<b>${temporalStatus.label}</b>` : ""}
        </span>
        <span>
          <span class="talk-code">${escapeHtml(code)}</span>
          <span class="talk-title">${escapeHtml(title)}</span>
          ${talkCategoryMarkup(code)}
          <span class="talk-authors"><b>著者</b>${escapeHtml(names)}</span>
          ${affiliations ? `<span class="talk-affiliations"><b>所属</b>${escapeHtml(affiliations)}</span>` : ""}
        </span>
        <span class="external-icon" aria-hidden="true">↗</span>
      </a>
    </li>`;
}

function collectionMatchesCode(collection, code) {
  const category = categoriesByCode.get(code);
  if (!category) return false;
  return collection.any.some((qualifiedId) => {
    const [axisId, labelId] = qualifiedId.split(":");
    return category.labels[axisId]?.includes(labelId);
  });
}

function sessionCollectionCounts(session) {
  return browseCollections
    .map((collection, order) => ({
      ...collection,
      order,
      count: session.talks.filter((talk) => collectionMatchesCode(collection, talk[1])).length,
    }))
    .filter((collection) => collection.count > 0)
    .sort((a, b) => {
      if (state.theme) {
        if (a.id === state.theme) return -1;
        if (b.id === state.theme) return 1;
      }
      return b.count - a.count || a.order - b.order;
    });
}

function sessionThemeMarkup(session) {
  const themes = sessionCollectionCounts(session).slice(0, 3);
  if (!themes.length) return "";
  return `<div class="session-themes" aria-label="代表テーマ">${themes
    .map(
      (theme) =>
        `<span>${escapeHtml(theme.label)} ${theme.count}/${session.talks.length}</span>`,
    )
    .join("")}</div>`;
}

function sessionMarkup(session) {
  const status = sessionStatus(session);
  const isOpen = state.openSessionIds.has(session.id);
  return `
    <details class="session-card" data-session-id="${escapeHtml(session.id)}" ${isOpen ? "open" : ""}>
      <summary class="session-summary">
        <div class="session-topline">
          ${status ? `<span class="status-pill ${status.className}">${status.label}</span>` : ""}
          <span>${escapeHtml(session.start)}–${escapeHtml(session.end)}</span>
          <span>・</span>
          <span>${escapeHtml(session.division)}</span>
        </div>
        <h3>${escapeHtml(session.title)}</h3>
        ${currentTalkMarkup(session)}
        ${sessionThemeMarkup(session)}
        <div class="meta-row">
          <span aria-label="会場"><span aria-hidden="true">●</span> ${escapeHtml(session.campus)}</span>
          <span aria-label="教室"><b>${escapeHtml(session.room)}</b></span>
        </div>
      </summary>
      <div class="talks" data-talks ${isOpen ? 'data-loaded="true"' : ""}>${isOpen ? talksMarkup(session) : ""}</div>
    </details>`;
}

function talksMarkup(session) {
  return `
    <div class="talks-heading">
      <span>講演一覧（${session.talks.length}件）・* は発表者</span>
      <span>座長：${escapeHtml(session.chair)}</span>
    </div>
    <ol class="talk-list">${session.talks
      .map((talk, index) => talkMarkup(talk, session, index))
      .join("")}</ol>`;
}

function emptyMarkup(message = "この時間帯に該当するセッションはありません") {
  return `
    <div class="empty-state">
      <strong>${escapeHtml(message)}</strong>
      <p>時刻または絞り込み条件を変更してください。</p>
    </div>`;
}

function groupSessionsByStart(daySessions) {
  const groups = new Map();
  for (const session of daySessions) {
    if (!groups.has(session.start)) groups.set(session.start, []);
    groups.get(session.start).push(session);
  }
  return [...groups.entries()]
    .sort(([left], [right]) => minutes(left) - minutes(right))
    .map(([start, groupedSessions]) => ({ start, sessions: groupedSessions }));
}

function defaultOpenTimeGroups(groups, scheduleDate) {
  if (!groups.length) return new Set();
  if (displayClock.date !== scheduleDate) return new Set([groups[0].start]);

  const now = minutes(displayClock.time);
  const liveGroups = groups.filter((group) =>
    group.sessions.some(
      (session) => now >= minutes(session.start) && now < minutes(session.end),
    ),
  );
  if (liveGroups.length) return new Set(liveGroups.map((group) => group.start));

  const nextGroup = groups.find((group) => minutes(group.start) > now);
  return new Set([nextGroup?.start ?? groups.at(-1).start]);
}

function timeGroupStatus(group, scheduleDate) {
  if (displayClock.date !== scheduleDate) return null;
  const now = minutes(displayClock.time);
  if (
    group.sessions.some(
      (session) => now >= minutes(session.start) && now < minutes(session.end),
    )
  ) {
    return { label: "開催中", className: "is-live" };
  }
  if (group.sessions.every((session) => now >= minutes(session.end))) {
    return { label: "終了", className: "is-ended" };
  }
  return null;
}

function scheduleGroupsMarkup(daySessions, scheduleDate) {
  const groups = groupSessionsByStart(daySessions);
  const defaultOpen = defaultOpenTimeGroups(groups, scheduleDate);
  const openAllMatches = hasActiveFilters();
  return groups
    .map((group) => {
      const groupKey = `${scheduleDate}/${group.start}`;
      const storedOpen = state.timeGroupOpen.get(groupKey);
      const isOpen = storedOpen ?? (openAllMatches || defaultOpen.has(group.start));
      const status = timeGroupStatus(group, scheduleDate);
      return `
        <details class="time-group ${status?.className ?? ""}" data-time-group-key="${escapeHtml(groupKey)}" ${isOpen ? "open" : ""}>
          <summary class="time-group-summary">
            <span class="time-group-time">${escapeHtml(group.start)}</span>
            <span>開始</span>
            ${status ? `<b class="time-group-status">${status.label}</b>` : ""}
            <span class="time-group-count">${group.sessions.length}セッション</span>
          </summary>
          <div class="schedule-list">
            ${group.sessions.map((session) => sessionMarkup(session)).join("")}
          </div>
        </details>`;
    })
    .join("");
}

function matchesFilters(session) {
  if (state.division && session.division !== state.division) return false;
  if (state.campus && session.campus !== state.campus) return false;
  if (state.theme) {
    const collection = browseCollections.find((item) => item.id === state.theme);
    if (!collection || !session.talks.some((talk) => collectionMatchesCode(collection, talk[1]))) {
      return false;
    }
  }

  const words = state.query
    .toLocaleLowerCase("ja")
    .split(/\s+/)
    .filter(Boolean);
  if (!words.length) return true;

  const haystack = searchTextById.get(session.id) ?? "";
  return words.every((word) => haystack.includes(word));
}

function hasActiveFilters() {
  return Boolean(state.division || state.campus || state.theme || state.query);
}

function renderView() {
  const isNow = state.activeTab === "now";
  document.querySelector("#now-view").hidden = !isNow;
  document.querySelector("#schedule-view").hidden = isNow;
  document.querySelectorAll("[data-program-tab]").forEach((button) => {
    const isCurrent = button.dataset.programTab === state.activeTab;
    button.classList.toggle("is-active", isCurrent);
    button.setAttribute("aria-selected", String(isCurrent));
  });
}

function render() {
  if (state.activeTab === "now" && state.followRealTime) {
    const now = japanNow();
    state.referenceDate = now.date;
    state.referenceTime = now.time;
  }
  displayClock =
    state.activeTab === "now"
      ? { date: state.referenceDate, time: state.referenceTime }
      : japanNow();
  const isNow = state.activeTab === "now";
  const referenceSessions = sessions
    .filter((session) => session.date === state.referenceDate)
    .sort(
      (a, b) =>
        minutes(a.start) - minutes(b.start) ||
        a.campus.localeCompare(b.campus, "ja") ||
        a.room.localeCompare(b.room, "ja"),
    );
  const scheduleDate = state.activeTab === "now" ? EVENT_DATES[0] : state.activeTab;
  const allDaySessions = sessions
    .filter((session) => session.date === scheduleDate)
    .sort(
      (a, b) =>
        minutes(a.start) - minutes(b.start) ||
        a.campus.localeCompare(b.campus, "ja") ||
        a.room.localeCompare(b.room, "ja"),
    );
  const daySessions = allDaySessions.filter(matchesFilters);
  const now = minutes(state.referenceTime);
  const horizon = now + 60;
  const allUpcoming = referenceSessions.filter(
    (session) => minutes(session.end) > now && minutes(session.start) <= horizon,
  );
  const upcoming = allUpcoming.filter(matchesFilters);

  document.querySelector("#reference-datetime").value = `${state.referenceDate}T${state.referenceTime}`;
  document.querySelector("#session-count").textContent = hasActiveFilters()
    ? `${upcoming.length}/${allUpcoming.length}件`
    : `${upcoming.length}件`;
  document.querySelector("#upcoming-sessions").innerHTML = upcoming.length
    ? upcoming.map((session) => sessionMarkup(session)).join("")
    : emptyMarkup();
  if (!isNow) {
    document.querySelector("#schedule-sessions").innerHTML = daySessions.length
      ? scheduleGroupsMarkup(daySessions, scheduleDate)
      : emptyMarkup("この日の該当セッションはありません");
  }

  const scheduleDateLabel = dateFormatter.format(new Date(`${scheduleDate}T12:00:00+09:00`));
  document.querySelector("#schedule-heading").textContent = `${scheduleDateLabel}のセッション（${daySessions.length}件）`;
  document.querySelector("#filter-summary").classList.toggle("has-filter", hasActiveFilters());
  document.querySelector("#clear-filters").disabled = !hasActiveFilters();

  renderView();
}

function populateFilterOptions() {
  const divisionOrder = [
    "第I部門",
    "第II部門",
    "第III部門",
    "第IV部門",
    "第V部門",
    "第VI部門",
    "第VII部門",
    "共通セッション",
  ];
  const divisions = [...new Set(sessions.map((session) => session.division))].sort(
    (a, b) => divisionOrder.indexOf(a) - divisionOrder.indexOf(b),
  );
  const campuses = [...new Set(sessions.map((session) => session.campus))].sort((a, b) =>
    a.localeCompare(b, "ja"),
  );

  document.querySelector("#division-filter").innerHTML = [
    '<option value="">すべての部門</option>',
    ...divisions.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`),
  ].join("");
  document.querySelector("#campus-filter").innerHTML = [
    '<option value="">すべてのキャンパス</option>',
    ...campuses.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`),
  ].join("");
  document.querySelector("#theme-filter").innerHTML = [
    '<option value="">すべてのテーマ</option>',
    ...browseCollections.map(
      (collection) =>
        `<option value="${escapeHtml(collection.id)}">${escapeHtml(collection.label)}</option>`,
    ),
  ].join("");
}

function japanNow() {
  const parts = new Intl.DateTimeFormat("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "Asia/Tokyo",
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return {
    date: `${values.year}-${values.month}-${values.day}`,
    time: `${values.hour}:${values.minute}`,
  };
}

function buildSearchIndex(session) {
  const categoryLabels = session.talks.flatMap((talk) => {
    const category = categoriesByCode.get(talk[1]);
    if (!category) return [];
    return Object.entries(category.labels).flatMap(([axisId, labelIds]) =>
      labelIds.map((labelId) => categoryLabelByQualifiedId.get(`${axisId}:${labelId}`) ?? ""),
    );
  });
  return [
    session.title,
    session.division,
    session.campus,
    session.room,
    session.chair,
    ...session.talks.flatMap((talk) => talk.slice(1)),
    ...categoryLabels,
  ]
    .join(" ")
    .toLocaleLowerCase("ja");
}

async function loadSessions() {
  try {
    const [sessionsResponse, taxonomyResponse, categoriesResponse] = await Promise.all([
      fetch("data/sessions.json"),
      fetch("data/category_taxonomy.json"),
      fetch("data/categories.json"),
    ]);
    for (const response of [sessionsResponse, taxonomyResponse, categoriesResponse]) {
      if (!response.ok) throw new Error(`${response.url}: HTTP ${response.status}`);
    }
    const [loadedSessions, taxonomy, categoryData] = await Promise.all([
      sessionsResponse.json(),
      taxonomyResponse.json(),
      categoriesResponse.json(),
    ]);
    sessions = loadedSessions;
    browseCollections = taxonomy.browse_collections;
    for (const axis of taxonomy.axes) {
      for (const value of axis.values) {
        categoryLabelByQualifiedId.set(`${axis.id}:${value.id}`, value.label);
      }
    }
    for (const category of categoryData.presentations) {
      categoriesByCode.set(category.code, category);
    }
    for (const session of sessions) {
      sessionsById.set(session.id, session);
      searchTextById.set(session.id, buildSearchIndex(session));
    }
    populateFilterOptions();
    render();
  } catch (error) {
    console.error(error);
    const message = "プログラムデータを読み込めませんでした";
    document.querySelector("#upcoming-sessions").innerHTML = emptyMarkup(message);
    document.querySelector("#schedule-sessions").innerHTML = emptyMarkup(message);
  }
}

document.querySelectorAll("[data-program-tab]").forEach((button) => {
  button.addEventListener("click", () => {
    state.activeTab = button.dataset.programTab;
    render();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
});

document.querySelector("#reference-datetime").addEventListener("change", (event) => {
  const [date, time] = event.target.value.split("T");
  if (!date || !time) return;
  state.referenceDate = date;
  state.referenceTime = time;
  state.followRealTime = false;
  render();
});

document.querySelector("#use-real-time").addEventListener("click", () => {
  const now = japanNow();
  state.referenceDate = now.date;
  state.referenceTime = now.time;
  state.followRealTime = true;
  render();
});

document.querySelector("#query-filter").addEventListener("input", (event) => {
  state.query = event.target.value.trim();
  render();
});

document.querySelector("#division-filter").addEventListener("change", (event) => {
  state.division = event.target.value;
  render();
});

document.querySelector("#campus-filter").addEventListener("change", (event) => {
  state.campus = event.target.value;
  render();
});

document.querySelector("#theme-filter").addEventListener("change", (event) => {
  state.theme = event.target.value;
  render();
});

document.querySelector("#clear-filters").addEventListener("click", () => {
  state.query = "";
  state.division = "";
  state.campus = "";
  state.theme = "";
  document.querySelector("#query-filter").value = "";
  document.querySelector("#division-filter").value = "";
  document.querySelector("#campus-filter").value = "";
  document.querySelector("#theme-filter").value = "";
  render();
});

document.addEventListener("click", (event) => {
  const summary = event.target.closest?.(".time-group-summary");
  if (!summary) return;
  const timeGroup = summary.parentElement;
  state.timeGroupOpen.set(timeGroup.dataset.timeGroupKey, !timeGroup.open);
});

document.addEventListener(
  "toggle",
  (event) => {
    const details = event.target.closest?.(".session-card");
    if (!details || event.target !== details) return;
    if (!details.open) {
      state.openSessionIds.delete(details.dataset.sessionId);
      return;
    }
    state.openSessionIds.add(details.dataset.sessionId);
    const container = details.querySelector("[data-talks]");
    if (container.dataset.loaded) return;
    const session = sessionsById.get(details.dataset.sessionId);
    if (!session) return;
    container.innerHTML = talksMarkup(session);
    container.dataset.loaded = "true";
  },
  true,
);

setInterval(() => {
  const now = japanNow();
  if (state.activeTab === "now") {
    if (!state.followRealTime) return;
    if (state.referenceDate === now.date && state.referenceTime === now.time) return;
    state.referenceDate = now.date;
    state.referenceTime = now.time;
  } else if (displayClock.date === now.date && displayClock.time === now.time) {
    return;
  }
  render();
}, 30_000);

document.querySelector("#upcoming-sessions").innerHTML = emptyMarkup("プログラムを読み込んでいます");
document.querySelector("#schedule-sessions").innerHTML = emptyMarkup("プログラムを読み込んでいます");
loadSessions();
