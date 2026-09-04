const EVENT_CONFIG_PATH = document.documentElement.dataset.eventConfig;
const planSlug = new URLSearchParams(window.location.search).get("plan");

let eventConfig = null;
let eventConfigUrl = null;
let sessions = [];
let personalPlan = null;
const sessionsById = new Map();
const searchTextById = new Map();
const categoriesByCode = new Map();
const categoryLabelByQualifiedId = new Map();
const plannedTalks = new Map();
let browseCollections = [];
const initialNow = japanNow();
let displayClock = initialNow;

const state = {
  activeTab: "now",
  referenceDate: initialNow.date,
  referenceTime: initialNow.time,
  divisions: new Set(),
  campuses: new Set(),
  themes: new Set(),
  query: "",
  followRealTime: true,
  timeGroupOpen: new Map(),
  activeSessionId: null,
};

let dateFormatter = new Intl.DateTimeFormat("ja-JP", {
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

function normalizeTalk(rawTalk) {
  if (Array.isArray(rawTalk)) {
    return {
      start: rawTalk[0] ?? "",
      end: "",
      code: rawTalk[1] ?? "",
      title: rawTalk[2] ?? "",
      presenter: rawTalk[3] ?? "",
      authors: rawTalk[4] ?? "",
      status: "scheduled",
    };
  }
  return {
    start: rawTalk.start ?? "",
    end: rawTalk.end ?? "",
    code: rawTalk.code ?? rawTalk.id ?? "",
    title: rawTalk.title ?? "",
    presenter: rawTalk.presenter ?? "",
    authors: rawTalk.authors ?? rawTalk.authorsText ?? "",
    contributors: rawTalk.contributors ?? null,
    status: rawTalk.status ?? "scheduled",
    url: rawTalk.url ?? "",
  };
}

function normalizeSession(rawSession) {
  return {
    ...rawSession,
    talks: (rawSession.talks ?? rawSession.presentations ?? []).map(normalizeTalk),
  };
}

function eventResourceUrl(relativePath) {
  if (!relativePath) return null;
  return new URL(relativePath, eventConfigUrl).href;
}

function talkUrl(talk) {
  if (talk.status === "missing" || talk.status === "session") return null;
  if (talk.url) return talk.url;
  const template = eventConfig?.links?.presentationTemplate;
  return template ? template.replace("{code}", encodeURIComponent(talk.code)) : null;
}

function planStatus(entry) {
  return entry?.status ?? "planned";
}

function planTalkBadgeMarkup(entry) {
  switch (planStatus(entry)) {
    case "must":
      return '<span class="plan-must-badge">最優先</span>';
    case "fixed":
      return '<span class="plan-fixed-badge">固定</span>';
    case "reference":
      return '<span class="plan-reference-badge">あとで確認</span>';
    default:
      return '<span class="plan-talk-badge">本命</span>';
  }
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
  const talk = session.talks[talkIndex];
  if (!talk.start || talk.status === "missing") return null;
  const now = minutes(displayClock.time);
  const talkStart = minutes(talk.start);
  const nextTimedTalk = session.talks.slice(talkIndex + 1).find((item) => item.start);
  const talkEnd = minutes(talk.end || nextTimedTalk?.start || session.end);
  if (now >= talkStart && now < talkEnd) {
    return { label: "開催中", className: "is-current" };
  }
  if (now >= talkEnd) {
    return { label: "終了", className: "is-ended" };
  }
  const nextIndex = session.talks.findIndex(
    (item) => item.start && item.status !== "missing" && minutes(item.start) > now,
  );
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
      <b>${escapeHtml(talk.start)}</b>
      <span>${escapeHtml(talk.code)} ${escapeHtml(talk.title)}</span>
    </div>`;
}

function affiliationEntries(rawAffiliations) {
  if (!rawAffiliations) return [];
  const source = rawAffiliations.replace(/^\(/, "").replace(/\)\s*$/, "");
  const markerPattern = /(?:^|[、,]\s*)(\d+)\.\s*/g;
  const markers = [...source.matchAll(markerPattern)];
  return markers.map((marker, index) => ({
    id: marker[1],
    name: source
      .slice(marker.index + marker[0].length, markers[index + 1]?.index ?? source.length)
      .trim()
      .replace(/[、,]\s*$/, ""),
  }));
}

function uniqueAffiliations(ids, affiliationById) {
  return [...new Set(ids.map((id) => affiliationById.get(id)).filter(Boolean))];
}

function talkContributorDetails(talk) {
  if (talk.contributors) {
    return {
      names: talk.contributors.names ?? talk.authors,
      presenter: talk.contributors.presenter ?? talk.presenter,
      presenterAffiliations: talk.contributors.presenterAffiliations ?? [],
      coauthorAffiliations: talk.contributors.coauthorAffiliations ?? [],
      hasCoauthors: talk.contributors.hasCoauthors ?? false,
    };
  }
  const rawPresenter = talk.presenter;
  const authors = talk.authors;
  const affiliationStart = authors.search(/\s+\(\d+\.\s*/);
  const names = affiliationStart >= 0 ? authors.slice(0, affiliationStart) : authors;
  const rawAffiliations = affiliationStart >= 0 ? authors.slice(affiliationStart).trim() : "";
  const entries = affiliationEntries(rawAffiliations);
  const affiliationById = new Map(entries.map((entry) => [entry.id, entry.name]));
  const presenter = String(rawPresenter)
    .replace(/\s*\d+(?:\s*[,，・/]\s*\d+)*\s*$/, "")
    .trim();

  let presenterAffiliationIds = [];
  let otherAuthors = names;
  const presenterMarker = names.indexOf("*");
  if (presenterMarker >= 0) {
    const afterMarker = names.slice(presenterMarker + 1);
    const presenterLength = afterMarker.startsWith(presenter) ? presenter.length : 0;
    const affiliationMatch = afterMarker
      .slice(presenterLength)
      .match(/^\s*(\d+(?:\s*,\s*\d+)*)/);
    presenterAffiliationIds = affiliationMatch
      ? affiliationMatch[1].split(",").map((id) => id.trim())
      : [];
    const presenterTokenLength = 1 + presenterLength + (affiliationMatch?.[0].length ?? 0);
    otherAuthors = `${names.slice(0, presenterMarker)}${names.slice(
      presenterMarker + presenterTokenLength,
    )}`;
  }

  if (!presenterAffiliationIds.length && affiliationById.has("1")) {
    presenterAffiliationIds = ["1"];
  }

  const hasCoauthors = otherAuthors.replace(/[\s、,，*\d]/g, "").length > 0;
  const coauthorAffiliationIds = [...otherAuthors.matchAll(/\d+/g)].map((match) => match[0]);
  let coauthorAffiliations = uniqueAffiliations(coauthorAffiliationIds, affiliationById);
  if (hasCoauthors && !coauthorAffiliations.length && entries.length === 1) {
    coauthorAffiliations = [entries[0].name];
  }

  return {
    names,
    presenter,
    presenterAffiliations: uniqueAffiliations(presenterAffiliationIds, affiliationById),
    coauthorAffiliations,
    hasCoauthors,
  };
}

function affiliationText(affiliations) {
  return affiliations.length ? affiliations.map(escapeHtml).join("／") : "記載なし";
}

function talkCategoryMarkup(code) {
  const category = categoriesByCode.get(code);
  if (!category) return "";
  const priorities = eventConfig.categoryAxisPriority ?? [
    "domain",
    "phase",
    "method",
    "issue",
    "material",
  ];
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
  const temporalStatus = talkStatus(session, talkIndex);
  const planEntry = plannedTalks.get(talk.code);
  const isReferencePick = planStatus(planEntry) === "reference";
  const isPersonalPick = Boolean(planEntry) && !isReferencePick;
  const contributors = talkContributorDetails(talk);
  const link = talkUrl(talk);
  const showAffiliations = eventConfig.features?.showAffiliations !== false;
  return `
    <li class="talk-item ${temporalStatus?.className ?? ""} ${isPersonalPick ? "is-personal-pick" : ""} ${isReferencePick ? "is-reference-pick" : ""}">
      <a class="talk-link ${link ? "" : "is-disabled"}" ${link ? `href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer"` : "aria-disabled=\"true\""}>
        <span class="talk-time">
          <span>${escapeHtml(talk.start || "時刻記載なし")}</span>
          ${temporalStatus && temporalStatus.className !== "is-ended" ? `<b>${temporalStatus.label}</b>` : ""}
        </span>
        <span>
          <span class="talk-code">${escapeHtml(talk.code)}</span>
          ${planEntry ? planTalkBadgeMarkup(planEntry) : ""}
          <span class="talk-title">${escapeHtml(talk.title)}</span>
          ${talkCategoryMarkup(talk.code)}
          ${contributors.names ? `<span class="talk-authors"><b>${escapeHtml(eventConfig.labels?.authors ?? "著者")}</b>${escapeHtml(contributors.names)}</span>` : ""}
          ${showAffiliations ? `<span class="talk-presenter-affiliation"><b>発表者所属</b>${affiliationText(
            contributors.presenterAffiliations,
          )}</span>` : ""}
          ${
            showAffiliations && contributors.hasCoauthors
              ? `<span class="talk-coauthor-affiliations"><b>共同報告者所属</b>${affiliationText(
                  contributors.coauthorAffiliations,
                )}</span>`
              : ""
          }
        </span>
        ${link ? '<span class="external-icon" aria-hidden="true">↗</span>' : ""}
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
      count: session.talks.filter((talk) => collectionMatchesCode(collection, talk.code)).length,
    }))
    .filter((collection) => collection.count > 0)
    .sort((a, b) => {
      if (state.themes.size) {
        const aSelected = state.themes.has(a.id);
        const bSelected = state.themes.has(b.id);
        if (aSelected !== bSelected) return aSelected ? -1 : 1;
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
  const planCounts = { planned: 0, must: 0, fixed: 0, reference: 0 };
  for (const talk of session.talks) {
    const entry = plannedTalks.get(talk.code);
    if (entry) planCounts[planStatus(entry)] += 1;
  }
  const attendedCount = planCounts.planned + planCounts.must + planCounts.fixed;
  return `
    <article class="session-card ${attendedCount ? "is-personal-session" : ""} ${planCounts.reference && !attendedCount ? "is-plan-reference-session" : ""}" data-session-id="${escapeHtml(session.id)}" role="button" tabindex="0" aria-haspopup="dialog" aria-label="${escapeHtml(session.title)}の詳細を開く">
      <div class="session-summary">
        <div class="session-topline">
          ${status ? `<span class="status-pill ${status.className}">${status.label}</span>` : ""}
          ${planCounts.must ? `<span class="session-must-badge">最優先 ${planCounts.must}件</span>` : ""}
          ${planCounts.fixed ? `<span class="session-fixed-badge">固定 ${planCounts.fixed}件</span>` : ""}
          ${planCounts.planned ? `<span class="session-plan-badge">本命 ${planCounts.planned}件</span>` : ""}
          ${planCounts.reference ? `<span class="session-reference-badge">あとで確認 ${planCounts.reference}件</span>` : ""}
          <span>${escapeHtml(session.start)}–${escapeHtml(session.end)}</span>
          <span>・</span>
          <span>${escapeHtml(session.division)}</span>
        </div>
        <h3>${escapeHtml(session.title)}</h3>
        ${currentTalkMarkup(session)}
        ${sessionThemeMarkup(session)}
        <div class="meta-row">
          <span aria-label="${escapeHtml(eventConfig.labels?.venue ?? "会場")}"><span aria-hidden="true">●</span> ${escapeHtml(session.campus)}</span>
          <span aria-label="${escapeHtml(eventConfig.labels?.room ?? "教室")}"><b>${escapeHtml(session.room)}</b></span>
        </div>
      </div>
    </article>`;
}

function talksMarkup(session) {
  return `
    <div class="talks-heading">
      <span>講演一覧（${session.talks.length}件）・${escapeHtml(eventConfig.labels?.presenterNote ?? "")}</span>
      ${session.chair ? `<span>座長：${escapeHtml(session.chair)}</span>` : ""}
    </div>
    <ol class="talk-list">${session.talks
      .map((talk, index) => talkMarkup(talk, session, index))
      .join("")}</ol>`;
}

function sessionDialogMarkup(session) {
  const status = sessionStatus(session);
  return `
    <section class="session-dialog-summary">
      <div class="session-topline">
        ${status ? `<span class="status-pill ${status.className}">${status.label}</span>` : ""}
        <span>${escapeHtml(session.start)}–${escapeHtml(session.end)}</span>
        <span>・</span>
        <span>${escapeHtml(session.division)}</span>
      </div>
      <h2 id="session-dialog-title">${escapeHtml(session.title)}</h2>
      ${currentTalkMarkup(session)}
      ${sessionThemeMarkup(session)}
      <div class="meta-row">
        <span aria-label="${escapeHtml(eventConfig.labels?.venue ?? "会場")}"><span aria-hidden="true">●</span> ${escapeHtml(session.campus)}</span>
        <span aria-label="${escapeHtml(eventConfig.labels?.room ?? "教室")}"><b>${escapeHtml(session.room)}</b></span>
      </div>
    </section>
    <div class="talks session-dialog-talks">${talksMarkup(session)}</div>`;
}

function openSessionDialog(session) {
  const dialog = document.querySelector("#session-dialog");
  state.activeSessionId = session.id;
  document.querySelector("#session-dialog-content").innerHTML = sessionDialogMarkup(session);
  if (!dialog.open) dialog.showModal();
  document.body.classList.add("modal-open");
  document.querySelector("#session-dialog-content").scrollTop = 0;
  document.querySelector("#session-dialog-close").focus();
}

function closeSessionDialog() {
  document.querySelector("#session-dialog").close();
}

function emptyMarkup(message = "この時間帯に該当するセッションはありません") {
  return `
    <div class="empty-state">
      <strong>${escapeHtml(message)}</strong>
      <p>時刻または絞り込み条件を変更してください。</p>
    </div>`;
}

function resolveTalk(code) {
  for (const session of sessions) {
    const talkIndex = session.talks.findIndex((talk) => talk.code === code);
    if (talkIndex >= 0) {
      return { session, talk: session.talks[talkIndex], talkIndex };
    }
  }
  return null;
}

function planSessionTemporalStatus(session) {
  if (session.date < displayClock.date) return { label: "終了", className: "is-ended" };
  if (session.date > displayClock.date) return null;
  return sessionStatus(session);
}

function planTalkTemporalStatus(session, talkIndex) {
  if (session.date < displayClock.date) return { label: "終了", className: "is-ended" };
  if (session.date > displayClock.date) return null;
  const status = talkStatus(session, talkIndex);
  if (status?.className === "is-next" && sessionStatus(session)?.className !== "is-live") {
    return null;
  }
  return status;
}

function planTalkMarkup(talk, talkEntries, session, talkIndex) {
  const planEntry = talkEntries.get(talk.code);
  const isReferencePick = planStatus(planEntry) === "reference";
  const isPersonalPick = Boolean(planEntry) && !isReferencePick;
  const temporalStatus = planTalkTemporalStatus(session, talkIndex);
  const contributors = talkContributorDetails(talk);
  const link = talkUrl(talk);
  const showAffiliations = eventConfig.features?.showAffiliations !== false;
  return `
    <li class="plan-talk ${temporalStatus?.className ?? ""} ${isPersonalPick ? "is-personal-pick" : ""} ${isReferencePick ? "is-reference-pick" : ""}">
      <a ${link ? `href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer"` : "aria-disabled=\"true\""}>
        <span class="plan-talk-time">
          <span>${escapeHtml(talk.start || "時刻記載なし")}</span>
          ${temporalStatus && temporalStatus.className !== "is-ended" ? `<b>${temporalStatus.label}</b>` : ""}
        </span>
        <span>
          <span class="plan-talk-code-row">
            <b>${escapeHtml(talk.code)}</b>
            ${planEntry ? planTalkBadgeMarkup(planEntry) : ""}
          </span>
          <strong>${escapeHtml(talk.title)}</strong>
          <small class="plan-talk-presenter">発表者：${escapeHtml(contributors.presenter)}</small>
          ${showAffiliations ? `<small class="plan-talk-affiliation"><b>発表者所属</b>${affiliationText(
            contributors.presenterAffiliations,
          )}</small>` : ""}
          ${
            showAffiliations && contributors.hasCoauthors
              ? `<small class="plan-talk-affiliation"><b>共同報告者所属</b>${affiliationText(
                  contributors.coauthorAffiliations,
                )}</small>`
              : ""
          }
        </span>
        ${link ? '<span aria-hidden="true">↗</span>' : ""}
      </a>
    </li>`;
}

function groupPersonalPlanBySession() {
  const grouped = new Map();
  for (const entry of personalPlan.items) {
    for (const code of entry.talkCodes) {
      const resolved = resolveTalk(code);
      if (!resolved) throw new Error(`個人プランの講演番号が見つかりません: ${code}`);
      if (resolved.session.date !== entry.date) {
        throw new Error(`個人プランの日付とセッションの日付が一致しません: ${code}`);
      }
      let group = grouped.get(resolved.session.id);
      if (!group) {
        group = {
          session: resolved.session,
          talkEntries: new Map(),
          entries: [],
        };
        grouped.set(resolved.session.id, group);
      }
      group.talkEntries.set(code, entry);
      if (!group.entries.includes(entry)) group.entries.push(entry);
    }
  }
  return [...grouped.values()].sort(
    (a, b) =>
      a.session.date.localeCompare(b.session.date) ||
      minutes(a.session.start) - minutes(b.session.start) ||
      a.session.campus.localeCompare(b.session.campus, "ja") ||
      a.session.room.localeCompare(b.session.room, "ja"),
  );
}

function planSessionStatus(entries) {
  if (entries.every((entry) => planStatus(entry) === "reference")) return "reference";
  if (entries.some((entry) => planStatus(entry) === "fixed")) return "fixed";
  if (entries.some((entry) => planStatus(entry) === "must")) return "must";
  return "planned";
}

function planEntryMarkup({ session, talkEntries, entries }) {
  const status = planSessionStatus(entries);
  const temporalStatus = planSessionTemporalStatus(session);
  const priority = Math.max(...entries.map((entry) => entry.priority ?? 3));
  const selectedCount = [...talkEntries.values()].filter(
    (entry) => planStatus(entry) !== "reference",
  ).length;
  const referenceCount = talkEntries.size - selectedCount;
  const statusBadge =
    status === "reference"
      ? `<span class="session-reference-badge">あとで確認 ${referenceCount}件</span>`
      : status === "must"
        ? `<span class="session-must-badge">最優先 ${selectedCount}件</span>`
        : status === "fixed"
          ? `<span class="session-fixed-badge">固定 ${selectedCount}件</span>`
          : `<span class="session-plan-badge">本命 ${selectedCount}件</span>`;
  const afterActions = entries.filter((entry) => entry.after);
  return `
    <article class="plan-entry is-${status} ${temporalStatus?.className ?? ""}" data-plan-session-id="${escapeHtml(session.id)}">
      <div class="plan-entry-time">
        <strong>${escapeHtml(session.start)}</strong>
        <span>–${escapeHtml(session.end)}</span>
      </div>
      <div class="plan-entry-body">
        <div class="plan-entry-badges">
          ${temporalStatus ? `<span class="status-pill ${temporalStatus.className}">${temporalStatus.label}</span>` : ""}
          ${status !== "reference" ? `<span class="plan-priority" aria-label="優先度 星${priority}">${"★".repeat(priority)}</span>` : ""}
          ${statusBadge}
        </div>
        <h3>${escapeHtml(session.title)}</h3>
        <p class="plan-entry-venue">
          <span aria-label="会場"><span aria-hidden="true">●</span> ${escapeHtml(session.campus)} ${escapeHtml(session.room)}</span>
          <span>${escapeHtml(session.division)}</span>
        </p>
        <div class="plan-session-heading">
          <span>講演一覧（${session.talks.length}件）</span>
          <span>座長：${escapeHtml(session.chair)}</span>
        </div>
        <ol class="plan-talks">${session.talks
          .map((talk, talkIndex) => planTalkMarkup(talk, talkEntries, session, talkIndex))
          .join("")}</ol>
        ${afterActions.length ? `<div class="plan-after-actions">${afterActions
          .map(
            (entry) => `
              <p class="plan-after-action">
                <b>終了後</b>
                <span>${escapeHtml(entry.after)}</span>
              </p>`,
          )
          .join("")}</div>` : ""}
        <div class="plan-entry-notes">${entries
          .map(
            (entry) => `
              <p class="plan-entry-note">
                <b>${escapeHtml(entry.title)}</b>
                <span>${escapeHtml(entry.note)}</span>
              </p>`,
          )
          .join("")}</div>
      </div>
    </article>`;
}

function planReferenceSectionMarkup(referenceSessions) {
  if (!referenceSessions.length) return "";
  return `
    <section class="plan-reference-section" aria-label="見送り・あとで確認">
      <header class="plan-reference-heading">
        <div>
          <span>REFERENCE</span>
          <h3>見送り・あとで確認</h3>
        </div>
        <b>${referenceSessions.length}セッション</b>
        <p>当日は聴講せず、資料や講演情報をあとで確認する候補です。</p>
      </header>
      <div class="plan-reference-list">${referenceSessions
        .map(planEntryMarkup)
        .join("")}</div>
    </section>`;
}

function planDayMarkup([date, daySessions], dayIndex) {
  const scheduledSessions = daySessions.filter(
    (planSession) => planSessionStatus(planSession.entries) !== "reference",
  );
  const referenceSessions = daySessions.filter(
    (planSession) => planSessionStatus(planSession.entries) === "reference",
  );
  const dayClass =
    date === displayClock.date
      ? "is-today"
      : date < displayClock.date
        ? "is-past"
        : "is-future";
  return `
    <section class="plan-day ${dayClass}" data-plan-date="${escapeHtml(date)}">
      <header class="plan-day-heading">
        <span>DAY ${dayIndex + 1}</span>
        <h2>${escapeHtml(dateFormatter.format(new Date(`${date}T12:00:00+09:00`)))}</h2>
        ${date === displayClock.date ? `<span class="plan-now-marker">現在 ${escapeHtml(displayClock.time)}</span>` : ""}
        <b>${scheduledSessions.length}予定${referenceSessions.length ? `・${referenceSessions.length}参考` : ""}</b>
      </header>
      <div class="plan-timeline">${scheduledSessions
        .map(planEntryMarkup)
        .join("")}</div>
      ${planReferenceSectionMarkup(referenceSessions)}
    </section>`;
}

function renderPersonalPlan() {
  if (!personalPlan) return;
  const planSessions = groupPersonalPlanBySession();
  const groups = new Map();
  for (const planSession of planSessions) {
    const date = planSession.session.date;
    if (!groups.has(date)) groups.set(date, []);
    groups.get(date).push(planSession);
  }
  const markup = [...groups.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(planDayMarkup)
    .join("");
  const scheduledCount = planSessions.filter(
    (planSession) => planSessionStatus(planSession.entries) !== "reference",
  ).length;
  const referenceCount = planSessions.length - scheduledCount;
  document.querySelector("#plan-heading").textContent = personalPlan.title;
  document.querySelector("#plan-description").textContent = personalPlan.description ?? "";
  document.querySelector("#plan-count").textContent = `${scheduledCount}予定${referenceCount ? `・${referenceCount}参考` : ""}`;
  document.querySelector("#plan-sessions").innerHTML = markup || emptyMarkup("予定が登録されていません");
}

async function loadPersonalPlan() {
  if (!planSlug || !/^[a-z0-9_-]+$/i.test(planSlug)) return;
  if (eventConfig.features?.personalPlans === false || !eventConfig.data?.plans) return;
  const response = await fetch(
    eventResourceUrl(`${eventConfig.data.plans}${encodeURIComponent(planSlug)}.json`),
  );
  if (!response.ok) {
    console.warn(`個人プランを読み込めませんでした: HTTP ${response.status}`);
    return;
  }
  const loadedPlan = await response.json();
  if (!Array.isArray(loadedPlan.items)) throw new Error("個人プランのitemsが不正です");
  personalPlan = loadedPlan;
  const allowedStatuses = new Set(["planned", "must", "fixed", "reference"]);
  for (const entry of personalPlan.items) {
    if (!Array.isArray(entry.talkCodes)) throw new Error("個人プランのtalkCodesが不正です");
    if (!allowedStatuses.has(planStatus(entry))) {
      throw new Error(`個人プランのstatusが不正です: ${entry.status}`);
    }
    for (const code of entry.talkCodes) {
      if (plannedTalks.has(code)) throw new Error(`個人プランの講演番号が重複しています: ${code}`);
      plannedTalks.set(code, entry);
    }
  }
  document.querySelector(".program-tab-plan").hidden = false;
  document.body.classList.add("has-personal-plan");
  document.title = `${personalPlan.title} | ${eventConfig.pageTitle}`;
  document.documentElement.style.setProperty(
    "--program-tab-count",
    String(eventConfig.dates.length + 2),
  );
  state.activeTab = "plan";
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
  if (state.divisions.size && !state.divisions.has(session.division)) return false;
  if (state.campuses.size && !state.campuses.has(session.campus)) return false;
  if (state.themes.size) {
    const selectedCollections = browseCollections.filter((item) => state.themes.has(item.id));
    if (
      !selectedCollections.some((collection) =>
        session.talks.some((talk) => collectionMatchesCode(collection, talk.code)),
      )
    ) {
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
  return Boolean(
    state.divisions.size || state.campuses.size || state.themes.size || state.query,
  );
}

function selectedFilterLabel(values, labelForValue) {
  if (!values.size) return "すべて";
  if (values.size === 1) return labelForValue([...values][0]);
  return `${values.size}件選択`;
}

function updateMultiFilterLabels() {
  document.querySelector("#theme-filter-label").textContent = selectedFilterLabel(
    state.themes,
    (value) => browseCollections.find((item) => item.id === value)?.label ?? value,
  );
  document.querySelector("#division-filter-label").textContent = selectedFilterLabel(
    state.divisions,
    (value) => value,
  );
  document.querySelector("#campus-filter-label").textContent = selectedFilterLabel(
    state.campuses,
    (value) => value,
  );
}

function renderView() {
  const isNow = state.activeTab === "now";
  const isPlan = state.activeTab === "plan";
  document.querySelector("#plan-view").hidden = !isPlan;
  document.querySelector("#now-view").hidden = !isNow;
  document.querySelector("#schedule-view").hidden = isNow || isPlan;
  document.querySelector(".shared-filter").hidden = isPlan;
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
  if (state.activeTab === "plan") {
    renderPersonalPlan();
    renderView();
    return;
  }
  const isNow = state.activeTab === "now";
  const referenceSessions = sessions
    .filter((session) => session.date === state.referenceDate)
    .sort(
      (a, b) =>
        minutes(a.start) - minutes(b.start) ||
        a.campus.localeCompare(b.campus, "ja") ||
        a.room.localeCompare(b.room, "ja"),
    );
  const scheduleDate = state.activeTab === "now" ? eventConfig.dates[0] : state.activeTab;
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
  updateMultiFilterLabels();

  const dialog = document.querySelector("#session-dialog");
  if (dialog.open && state.activeSessionId) {
    const activeSession = sessionsById.get(state.activeSessionId);
    if (activeSession) {
      const content = document.querySelector("#session-dialog-content");
      const scrollTop = content.scrollTop;
      content.innerHTML = sessionDialogMarkup(activeSession);
      content.scrollTop = scrollTop;
    }
  }

  renderView();
}

function multiSelectOptionsMarkup(groupId, values) {
  return values
    .map(
      ({ value, label }, index) => `
        <label class="multi-select-option" for="${groupId}-option-${index}">
          <input id="${groupId}-option-${index}" type="checkbox" value="${escapeHtml(value)}" />
          <span>${escapeHtml(label)}</span>
        </label>`,
    )
    .join("");
}

function populateFilterOptions() {
  const divisionOrder = eventConfig.divisionOrder ?? [];
  const divisionRank = (value) => {
    const index = divisionOrder.indexOf(value);
    return index >= 0 ? index : divisionOrder.length;
  };
  const divisions = [...new Set(sessions.map((session) => session.division))].sort(
    (a, b) => divisionRank(a) - divisionRank(b) || a.localeCompare(b, "ja"),
  );
  const campuses = [...new Set(sessions.map((session) => session.campus))].sort((a, b) =>
    a.localeCompare(b, "ja"),
  );

  document.querySelector("#division-filter").innerHTML = multiSelectOptionsMarkup(
    "division-filter",
    divisions.map((value) => ({ value, label: value })),
  );
  document.querySelector("#campus-filter").innerHTML = multiSelectOptionsMarkup(
    "campus-filter",
    campuses.map((value) => ({ value, label: value })),
  );
  document.querySelector("#theme-filter").innerHTML = multiSelectOptionsMarkup(
    "theme-filter",
    browseCollections.map((collection) => ({
      value: collection.id,
      label: collection.label,
    })),
  );
}

function japanNow() {
  const parts = new Intl.DateTimeFormat("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: eventConfig?.timeZone ?? "Asia/Tokyo",
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return {
    date: `${values.year}-${values.month}-${values.day}`,
    time: `${values.hour}:${values.minute}`,
  };
}

function buildSearchIndex(session) {
  const categoryLabels = session.talks.flatMap((talk) => {
    const category = categoriesByCode.get(talk.code);
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
    ...session.talks.flatMap((talk) => [
      talk.code,
      talk.title,
      talk.presenter,
      talk.authors,
    ]),
    ...categoryLabels,
  ]
    .join(" ")
    .toLocaleLowerCase("ja");
}

async function loadSessions() {
  try {
    const categoriesEnabled = eventConfig.features?.categories !== false;
    const requests = [fetch(eventResourceUrl(eventConfig.data.sessions))];
    if (categoriesEnabled) {
      requests.push(fetch(eventResourceUrl(eventConfig.data.taxonomy)));
      requests.push(fetch(eventResourceUrl(eventConfig.data.categories)));
    }
    const [sessionsResponse, taxonomyResponse, categoriesResponse] = await Promise.all(requests);
    for (const response of [sessionsResponse, taxonomyResponse, categoriesResponse].filter(Boolean)) {
      if (!response.ok) throw new Error(`${response.url}: HTTP ${response.status}`);
    }
    const loadedSessions = await sessionsResponse.json();
    sessions = loadedSessions.map(normalizeSession);
    if (categoriesEnabled) {
      const [taxonomy, categoryData] = await Promise.all([
        taxonomyResponse.json(),
        categoriesResponse.json(),
      ]);
      browseCollections = taxonomy.browse_collections;
      for (const axis of taxonomy.axes) {
        for (const value of axis.values) {
          categoryLabelByQualifiedId.set(`${axis.id}:${value.id}`, value.label);
        }
      }
      for (const category of categoryData.presentations) {
        categoriesByCode.set(category.code, category);
      }
    }
    for (const session of sessions) {
      sessionsById.set(session.id, session);
      searchTextById.set(session.id, buildSearchIndex(session));
    }
    await loadPersonalPlan();
    populateFilterOptions();
    render();
  } catch (error) {
    console.error(error);
    const message = "プログラムデータを読み込めませんでした";
    document.querySelector("#upcoming-sessions").innerHTML = emptyMarkup(message);
    document.querySelector("#schedule-sessions").innerHTML = emptyMarkup(message);
  }
}

function bindMultiFilter(selector, selectedValues) {
  document.querySelector(selector).addEventListener("change", (event) => {
    if (event.target.type !== "checkbox") return;
    if (event.target.checked) selectedValues.add(event.target.value);
    else selectedValues.delete(event.target.value);
    render();
  });
}

function configureEventPage() {
  document.title = eventConfig.pageTitle;
  document.querySelector("#page-description").content = eventConfig.description;
  document.querySelector("#theme-color").content = eventConfig.theme.primary;
  document.querySelector("#brand-mark").textContent = eventConfig.brandMark;
  document.querySelector("#brand-name").textContent = eventConfig.shortName;
  document.querySelector("#brand-subtitle").textContent = eventConfig.subtitle;
  document.querySelector("#theme-filter-name").textContent = eventConfig.labels.themeFilter;
  document.querySelector("#division-filter-name").textContent = eventConfig.labels.divisionFilter;
  document.querySelector("#campus-filter-name").textContent = eventConfig.labels.campusFilter;
  document.querySelector("#filter-summary-note").textContent = eventConfig.labels.filterSummary;
  document.querySelector("#program-note-heading").textContent = eventConfig.programNote.heading;
  document.querySelector("#program-note-body").textContent = eventConfig.programNote.body;

  const rootStyle = document.documentElement.style;
  rootStyle.setProperty("--navy", eventConfig.theme.primary);
  rootStyle.setProperty("--navy-soft", eventConfig.theme.primarySoft);
  rootStyle.setProperty("--orange", eventConfig.theme.accent);
  rootStyle.setProperty("--orange-soft", eventConfig.theme.accentSoft);
  rootStyle.setProperty("--yellow", eventConfig.theme.highlight);
  rootStyle.setProperty("--program-tab-count", String(eventConfig.dates.length + 1));
  document.body.dataset.event = eventConfig.id;

  const icon = document.querySelector('link[rel="icon"]');
  const iconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="${eventConfig.theme.highlight}"/><text x="32" y="43" text-anchor="middle" font-size="34">${eventConfig.brandMark}</text></svg>`;
  icon.href = `data:image/svg+xml,${encodeURIComponent(iconSvg)}`;

  const officialLink = document.querySelector("#official-link");
  if (eventConfig.links?.official) {
    officialLink.href = eventConfig.links.official;
    document.querySelector("#official-link-label").textContent =
      eventConfig.links.officialLabel ?? "公式プログラム";
  } else {
    officialLink.hidden = true;
  }

  const weekdayFormatter = new Intl.DateTimeFormat("ja-JP", {
    weekday: "short",
    timeZone: eventConfig.timeZone,
  });
  const dateButtons = eventConfig.dates
    .map((date, index) => {
      const [, month, day] = date.split("-");
      const weekday = weekdayFormatter.format(new Date(`${date}T12:00:00+09:00`));
      return `
        <button class="program-tab" type="button" data-program-tab="${escapeHtml(date)}">
          <span>DAY ${index + 1}</span>
          <strong>${Number(month)}/${Number(day)}</strong>
          <small>${escapeHtml(weekday)}</small>
        </button>`;
    })
    .join("");
  document.querySelector("#program-tabs").innerHTML = `
    <button class="program-tab program-tab-plan" type="button" data-program-tab="plan" hidden>
      <span>MY PLAN</span>
      <strong>本命</strong>
    </button>
    <button class="program-tab program-tab-now is-active" type="button" data-program-tab="now">
      <span>NOW</span>
      <strong>今から1時間</strong>
    </button>
    ${dateButtons}`;

  dateFormatter = new Intl.DateTimeFormat("ja-JP", {
    month: "long",
    day: "numeric",
    weekday: "short",
    timeZone: eventConfig.timeZone,
  });
}

function bindEventHandlers() {
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

  bindMultiFilter("#division-filter", state.divisions);
  bindMultiFilter("#campus-filter", state.campuses);
  bindMultiFilter("#theme-filter", state.themes);

  document.querySelector("#clear-filters").addEventListener("click", () => {
    state.query = "";
    state.divisions.clear();
    state.campuses.clear();
    state.themes.clear();
    document.querySelector("#query-filter").value = "";
    document
      .querySelectorAll(".multi-select-options input[type='checkbox']")
      .forEach((input) => {
        input.checked = false;
      });
    render();
  });

  document.addEventListener("click", (event) => {
    const summary = event.target.closest?.(".time-group-summary");
    if (!summary) return;
    const timeGroup = summary.parentElement;
    state.timeGroupOpen.set(timeGroup.dataset.timeGroupKey, !timeGroup.open);
  });

  document.addEventListener("click", (event) => {
    const card = event.target.closest?.(".session-card");
    if (!card) return;
    const session = sessionsById.get(card.dataset.sessionId);
    if (session) openSessionDialog(session);
  });

  document.addEventListener("keydown", (event) => {
    const card = event.target.closest?.(".session-card");
    if (!card || !["Enter", " "].includes(event.key)) return;
    event.preventDefault();
    const session = sessionsById.get(card.dataset.sessionId);
    if (session) openSessionDialog(session);
  });

  document.querySelector("#session-dialog-close").addEventListener("click", closeSessionDialog);
  document.querySelector("#session-dialog").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) closeSessionDialog();
  });
  document.querySelector("#session-dialog").addEventListener("close", () => {
    const closedSessionId = state.activeSessionId;
    state.activeSessionId = null;
    document.body.classList.remove("modal-open");
    document.querySelector(`[data-session-id="${closedSessionId}"]`)?.focus();
  });

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
}

async function initialize() {
  try {
    if (!EVENT_CONFIG_PATH) throw new Error("data-event-config が指定されていません");
    eventConfigUrl = new URL(EVENT_CONFIG_PATH, document.baseURI);
    const response = await fetch(eventConfigUrl);
    if (!response.ok) throw new Error(`${response.url}: HTTP ${response.status}`);
    eventConfig = await response.json();
    if (eventConfig.schemaVersion !== 1 || !eventConfig.dates?.length) {
      throw new Error("未対応または不正なイベント設定です");
    }
    configureEventPage();
    bindEventHandlers();
    document.querySelector("#upcoming-sessions").innerHTML = emptyMarkup(
      "プログラムを読み込んでいます",
    );
    document.querySelector("#schedule-sessions").innerHTML = emptyMarkup(
      "プログラムを読み込んでいます",
    );
    await loadSessions();
  } catch (error) {
    console.error(error);
    const message = "イベント設定を読み込めませんでした";
    document.querySelector("#upcoming-sessions").innerHTML = emptyMarkup(message);
    document.querySelector("#schedule-sessions").innerHTML = emptyMarkup(message);
  }
}

initialize();
