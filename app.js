const EVENT_DATES = ["2026-09-02", "2026-09-03", "2026-09-04"];
const DEFAULT_DATE = "2026-09-02";
const DEFAULT_TIME = "10:15";
const PRESENTATION_URL = "https://pub.confit.atlas.jp/ja/event/jsce2026/presentation/";

let sessions = [];
const sessionsById = new Map();
const searchTextById = new Map();

const state = {
  selectedDate: DEFAULT_DATE,
  selectedTime: DEFAULT_TIME,
  division: "",
  campus: "",
  query: "",
  view: "now",
  live: false,
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
  const now = minutes(state.selectedTime);
  if (now >= minutes(session.start) && now < minutes(session.end)) {
    return { label: "開催中", className: "is-live" };
  }
  if (minutes(session.start) > now) {
    return { label: `${session.start}開始`, className: "" };
  }
  return { label: "終了", className: "is-ended" };
}

function talkMarkup(talk) {
  const [time, code, title, , authors] = talk;
  const affiliationStart = authors.search(/\s+\(\d+\.\s*/);
  const names = affiliationStart >= 0 ? authors.slice(0, affiliationStart) : authors;
  const affiliations = affiliationStart >= 0 ? authors.slice(affiliationStart).trim() : "";
  return `
    <li>
      <a class="talk-link" href="${PRESENTATION_URL}${encodeURIComponent(code)}" target="_blank" rel="noopener noreferrer">
        <span class="talk-time">${escapeHtml(time)}</span>
        <span>
          <span class="talk-code">${escapeHtml(code)}</span>
          <span class="talk-title">${escapeHtml(title)}</span>
          <span class="talk-authors"><b>著者</b>${escapeHtml(names)}</span>
          ${affiliations ? `<span class="talk-affiliations"><b>所属</b>${escapeHtml(affiliations)}</span>` : ""}
        </span>
        <span class="external-icon" aria-hidden="true">↗</span>
      </a>
    </li>`;
}

function sessionMarkup(session, showStatus = true) {
  const status = sessionStatus(session);
  return `
    <details class="session-card" data-session-id="${escapeHtml(session.id)}">
      <summary class="session-summary">
        <div class="session-topline">
          ${showStatus ? `<span class="status-pill ${status.className}">${status.label}</span>` : ""}
          <span>${escapeHtml(session.start)}–${escapeHtml(session.end)}</span>
          <span>・</span>
          <span>${escapeHtml(session.division)}</span>
        </div>
        <h3>${escapeHtml(session.title)}</h3>
        <div class="meta-row">
          <span aria-label="会場"><span aria-hidden="true">●</span> ${escapeHtml(session.campus)}</span>
          <span aria-label="教室"><b>${escapeHtml(session.room)}</b></span>
        </div>
      </summary>
      <div class="talks" data-talks></div>
    </details>`;
}

function talksMarkup(session) {
  return `
    <div class="talks-heading">
      <span>講演一覧（${session.talks.length}件）・* は発表者</span>
      <span>座長：${escapeHtml(session.chair)}</span>
    </div>
    <ol class="talk-list">${session.talks.map(talkMarkup).join("")}</ol>`;
}

function emptyMarkup(message = "この時間帯に該当するセッションはありません") {
  return `
    <div class="empty-state">
      <strong>${escapeHtml(message)}</strong>
      <p>時刻または絞り込み条件を変更してください。</p>
    </div>`;
}

function matchesFilters(session) {
  if (state.division && session.division !== state.division) return false;
  if (state.campus && session.campus !== state.campus) return false;

  const words = state.query
    .toLocaleLowerCase("ja")
    .split(/\s+/)
    .filter(Boolean);
  if (!words.length) return true;

  const haystack = searchTextById.get(session.id) ?? "";
  return words.every((word) => haystack.includes(word));
}

function hasActiveFilters() {
  return Boolean(state.division || state.campus || state.query);
}

function renderView() {
  document.querySelector("#now-view").hidden = state.view !== "now";
  document.querySelector("#schedule-view").hidden = state.view !== "schedule";
  document.querySelectorAll("[data-view]").forEach((button) => {
    const isCurrent = button.dataset.view === state.view;
    button.classList.toggle("is-current", isCurrent);
    button.setAttribute("aria-pressed", String(isCurrent));
  });
}

function render() {
  const allDaySessions = sessions
    .filter((session) => session.date === state.selectedDate)
    .sort(
      (a, b) =>
        minutes(a.start) - minutes(b.start) ||
        a.campus.localeCompare(b.campus, "ja") ||
        a.room.localeCompare(b.room, "ja"),
    );
  const daySessions = allDaySessions.filter(matchesFilters);
  const now = minutes(state.selectedTime);
  const horizon = now + 60;
  const allUpcoming = allDaySessions.filter(
    (session) => minutes(session.end) > now && minutes(session.start) <= horizon,
  );
  const upcoming = allUpcoming.filter(matchesFilters);

  document.querySelector("#current-date").textContent = dateFormatter.format(
    new Date(`${state.selectedDate}T12:00:00+09:00`),
  );
  document.querySelector("#current-time").textContent = state.selectedTime;
  document.querySelector("#time-input").value = state.selectedTime;
  document.querySelector("#session-count").textContent = hasActiveFilters()
    ? `${upcoming.length}/${allUpcoming.length}件`
    : `${upcoming.length}件`;
  document.querySelector("#upcoming-sessions").innerHTML = upcoming.length
    ? upcoming.map((session) => sessionMarkup(session)).join("")
    : emptyMarkup();
  document.querySelector("#schedule-sessions").innerHTML = daySessions.length
    ? daySessions.map((session) => sessionMarkup(session, false)).join("")
    : emptyMarkup("この日の該当セッションはありません");

  document.querySelector("#schedule-heading").textContent = `この日のセッション（${daySessions.length}件）`;
  document.querySelector("#filter-summary").classList.toggle("has-filter", hasActiveFilters());
  document.querySelector("#clear-filters").disabled = !hasActiveFilters();

  document.querySelectorAll(".date-tab").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.date === state.selectedDate);
  });

  const notice = document.querySelector("#demo-notice");
  notice.classList.toggle("is-live", state.live);
  notice.innerHTML = state.live
    ? "<span>LIVE</span>日本時間の現在日時を表示しています"
    : "<span>DEMO</span>大会期間外のため、確認用日時を表示しています";
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
  return [
    session.title,
    session.division,
    session.campus,
    session.room,
    session.chair,
    ...session.talks.flatMap((talk) => talk.slice(1)),
  ]
    .join(" ")
    .toLocaleLowerCase("ja");
}

async function loadSessions() {
  try {
    const response = await fetch("data/sessions.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    sessions = await response.json();
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

document.querySelectorAll(".date-tab").forEach((button) => {
  button.addEventListener("click", () => {
    state.selectedDate = button.dataset.date;
    state.live = false;
    render();
  });
});

document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", () => {
    state.view = button.dataset.view;
    renderView();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
});

document.querySelector("#time-input").addEventListener("change", (event) => {
  state.selectedTime = event.target.value || DEFAULT_TIME;
  state.live = false;
  render();
});

document.querySelector("#use-real-time").addEventListener("click", () => {
  const now = japanNow();
  state.selectedDate = EVENT_DATES.includes(now.date) ? now.date : DEFAULT_DATE;
  state.selectedTime = now.time;
  state.live = EVENT_DATES.includes(now.date);
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

document.querySelector("#clear-filters").addEventListener("click", () => {
  state.query = "";
  state.division = "";
  state.campus = "";
  document.querySelector("#query-filter").value = "";
  document.querySelector("#division-filter").value = "";
  document.querySelector("#campus-filter").value = "";
  render();
});

document.addEventListener(
  "toggle",
  (event) => {
    const details = event.target.closest?.(".session-card");
    if (!details?.open) return;
    const container = details.querySelector("[data-talks]");
    if (container.dataset.loaded) return;
    const session = sessionsById.get(details.dataset.sessionId);
    if (!session) return;
    container.innerHTML = talksMarkup(session);
    container.dataset.loaded = "true";
  },
  true,
);

document.querySelector("#upcoming-sessions").innerHTML = emptyMarkup("プログラムを読み込んでいます");
document.querySelector("#schedule-sessions").innerHTML = emptyMarkup("プログラムを読み込んでいます");
loadSessions();
