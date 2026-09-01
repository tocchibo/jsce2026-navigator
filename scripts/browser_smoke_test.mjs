import assert from "node:assert/strict";

const port = Number(process.argv[2] ?? 9223);

async function waitForTarget() {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    try {
      const targets = await fetch(`http://127.0.0.1:${port}/json/list`).then((response) =>
        response.json(),
      );
      const page = targets.find(
        (target) => target.type === "page" && target.url.startsWith("http://127.0.0.1:"),
      );
      if (page) return page;
    } catch {
      // ブラウザの起動完了まで待つ。
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("ブラウザのデバッグ接続を開始できませんでした");
}

const target = await waitForTarget();
const socket = new WebSocket(target.webSocketDebuggerUrl);
const pending = new Map();
let nextId = 1;

await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});

socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (!message.id || !pending.has(message.id)) return;
  const { resolve, reject } = pending.get(message.id);
  pending.delete(message.id);
  if (message.error) reject(new Error(message.error.message));
  else resolve(message.result);
});

function call(method, params = {}) {
  const id = nextId;
  nextId += 1;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    try {
      const result = await call("Runtime.evaluate", {
        expression,
        awaitPromise: true,
        returnByValue: true,
      });
      if (result.exceptionDetails) {
        throw new Error(result.exceptionDetails.text);
      }
      return result.result.value;
    } catch (error) {
      if (!error.message.includes("context was destroyed") || attempt === 19) throw error;
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  throw new Error("JavaScriptの実行コンテキストを取得できませんでした");
}

await call("Page.reload", { ignoreCache: true });

const initial = await evaluate(`
  new Promise((resolve, reject) => {
    let attempts = 0;
    const timer = setInterval(() => {
      const divisionOptions = document.querySelectorAll('#division-filter input').length;
      const themeOptions = document.querySelectorAll('#theme-filter input').length;
      const referenceValue = document.querySelector('#reference-datetime').value;
      if (divisionOptions === 8 && themeOptions === 19 && referenceValue) {
        clearInterval(timer);
        resolve({
          referenceValue,
          divisionOptions,
          themeOptions,
          activeTab: document.querySelector('.program-tab.is-active').dataset.programTab,
          nowHidden: document.querySelector('#now-view').hidden,
          scheduleHidden: document.querySelector('#schedule-view').hidden,
        });
      } else if (attempts++ > 100) {
        clearInterval(timer);
        reject(new Error('プログラムデータの描画が完了しませんでした'));
      }
    }, 50);
  })
`);

assert.deepEqual(
  {
    divisionOptions: initial.divisionOptions,
    themeOptions: initial.themeOptions,
    activeTab: initial.activeTab,
    nowHidden: initial.nowHidden,
    scheduleHidden: initial.scheduleHidden,
  },
  {
  divisionOptions: 8,
  themeOptions: 19,
  activeTab: "now",
  nowHidden: false,
  scheduleHidden: true,
  },
);
assert.match(initial.referenceValue, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);

const upcoming = await evaluate(`
  new Promise((resolve) => {
    const input = document.querySelector('#reference-datetime');
    input.value = '2026-09-02T10:15';
    input.dispatchEvent(new Event('change', { bubbles: true }));
    setTimeout(() => {
      const liveCard = document.querySelector('#upcoming-sessions .session-card:has(.session-current-talk)');
      liveCard.click();
      setTimeout(() => resolve({
        count: document.querySelector('#session-count').textContent,
        upcomingCards: document.querySelectorAll('#upcoming-sessions .session-card').length,
        liveCards: document.querySelectorAll('#upcoming-sessions .session-current-talk').length,
        dialogOpen: document.querySelector('#session-dialog').open,
        currentTalks: document.querySelectorAll('#session-dialog .talk-item.is-current').length,
        nextTalks: document.querySelectorAll('#session-dialog .talk-item.is-next').length,
        currentLabel: document.querySelector('#session-dialog .talk-item.is-current .talk-time b')?.textContent,
        inlineTalks: document.querySelectorAll('#upcoming-sessions .talk-list').length,
        nowHidden: document.querySelector('#now-view').hidden,
        scheduleHidden: document.querySelector('#schedule-view').hidden,
      }), 100);
    }, 100);
  })
`);

assert.equal(upcoming.count, "88件");
assert.equal(upcoming.upcomingCards, 88);
assert.ok(upcoming.liveCards > 0);
assert.equal(upcoming.dialogOpen, true);
assert.equal(upcoming.currentTalks, 1);
assert.ok(upcoming.nextTalks <= 1);
assert.equal(upcoming.currentLabel, "開催中");
assert.equal(upcoming.inlineTalks, 0);
assert.equal(upcoming.nowHidden, false);
assert.equal(upcoming.scheduleHidden, true);

const grouped = await evaluate(`
  new Promise((resolve) => {
    document.querySelector('#session-dialog-close').click();
    document.querySelector('[data-program-tab="2026-09-02"]').click();
    setTimeout(() => resolve({
      timeGroups: document.querySelectorAll('#schedule-sessions .time-group').length,
      openGroups: document.querySelectorAll('#schedule-sessions .time-group[open]').length,
      firstStart: document.querySelector('#schedule-sessions .time-group-time')?.textContent,
      sessionTotal: document.querySelectorAll('#schedule-sessions .session-card').length,
    }), 100);
  })
`);

assert.deepEqual(grouped, {
  timeGroups: 5,
  openGroups: 1,
  firstStart: "8:50",
  sessionTotal: 126,
});

const filtered = await evaluate(`
  new Promise((resolve) => {
    const input = document.querySelector('#query-filter');
    input.value = '留萌開発事務所';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    setTimeout(() => {
      const card = document.querySelector('#schedule-sessions .session-card');
      card.click();
      setTimeout(() => resolve({
        count: document.querySelector('#session-count').textContent,
        upcomingCards: document.querySelectorAll('#upcoming-sessions .session-card').length,
        dayCards: document.querySelectorAll('#schedule-sessions .session-card').length,
        timeGroups: document.querySelectorAll('#schedule-sessions .time-group').length,
        openGroups: document.querySelectorAll('#schedule-sessions .time-group[open]').length,
        dialogOpen: document.querySelector('#session-dialog').open,
        inlineTalks: document.querySelectorAll('#schedule-sessions .talk-list').length,
        links: [...document.querySelectorAll('#session-dialog .talk-link')].map((link) => link.href),
        authors: [...document.querySelectorAll('#session-dialog .talk-authors')].map((item) => item.textContent),
        affiliations: [...document.querySelectorAll('#session-dialog .talk-affiliations')].map((item) => item.textContent),
        talkTags: [...document.querySelectorAll('#session-dialog .talk-tag')].map((item) => item.textContent),
        nowHidden: document.querySelector('#now-view').hidden,
        scheduleHidden: document.querySelector('#schedule-view').hidden,
        referencePanelVisible: document.querySelector('.reference-panel').checkVisibility(),
      }), 100);
    }, 100);
  })
`);

assert.equal(filtered.count, "0/88件");
assert.equal(filtered.upcomingCards, 0);
assert.equal(filtered.dayCards, 1);
assert.equal(filtered.timeGroups, 1);
assert.equal(filtered.openGroups, 1);
assert.equal(filtered.dialogOpen, true);
assert.equal(filtered.inlineTalks, 0);
assert.equal(filtered.nowHidden, true);
assert.equal(filtered.scheduleHidden, false);
assert.equal(filtered.referencePanelVisible, false);
assert.ok(filtered.links.some((url) => url.endsWith("/CS18-07")));
assert.ok(filtered.authors.some((value) => value.includes("千葉 雄貴")));
assert.ok(filtered.affiliations.some((value) => value.includes("留萌開発事務所")));
assert.ok(filtered.talkTags.length > 0);

const themed = await evaluate(`
  new Promise((resolve) => {
    document.querySelector('#session-dialog-close').click();
    document.querySelector('#clear-filters').click();
    document.querySelector('[data-program-tab="2026-09-04"]').click();
    const checkbox = document.querySelector('#theme-filter input[value="space"]');
    checkbox.checked = true;
    checkbox.dispatchEvent(new Event('change', { bubbles: true }));
    setTimeout(() => resolve({
      dayCards: document.querySelectorAll('#schedule-sessions .session-card').length,
      themeLabels: [...document.querySelectorAll('#schedule-sessions .session-themes')]
        .map((item) => item.textContent),
      filterActive: document.querySelector('#filter-summary').classList.contains('has-filter'),
      themeLabel: document.querySelector('#theme-filter-label').textContent,
    }), 100);
  })
`);

assert.ok(themed.dayCards >= 3);
assert.ok(themed.themeLabels.every((value) => value.includes("宇宙・月面")));
assert.equal(themed.filterActive, true);
assert.equal(themed.themeLabel, "宇宙・月面");

const multiSelected = await evaluate(`
  new Promise((resolve) => {
    const checkbox = document.querySelector('#theme-filter input[value="ai_dx"]');
    checkbox.checked = true;
    checkbox.dispatchEvent(new Event('change', { bubbles: true }));
    setTimeout(() => resolve({
      checkedThemes: document.querySelectorAll('#theme-filter input:checked').length,
      themeLabel: document.querySelector('#theme-filter-label').textContent,
      dayCards: document.querySelectorAll('#schedule-sessions .session-card').length,
    }), 100);
  })
`);

assert.equal(multiSelected.checkedThemes, 2);
assert.equal(multiSelected.themeLabel, "2件選択");
assert.ok(multiSelected.dayCards >= themed.dayCards);

const planUrl = new URL(target.url);
planUrl.search = "?plan=tocchibo";
await call("Page.navigate", { url: planUrl.href });

const personalPlan = await evaluate(`
  new Promise((resolve, reject) => {
    let attempts = 0;
    const timer = setInterval(() => {
      const entries = document.querySelectorAll('#plan-sessions .plan-entry');
      if (entries.length) {
        clearInterval(timer);
        const first = entries[0];
        const merged = document.querySelector('[data-plan-session-id="session-0072"]');
        resolve({
          activeTab: document.querySelector('.program-tab.is-active').dataset.programTab,
          planHidden: document.querySelector('#plan-view').hidden,
          count: document.querySelector('#plan-count').textContent,
          sessions: entries.length,
          talks: document.querySelectorAll('#plan-sessions .plan-talk').length,
          picks: document.querySelectorAll('#plan-sessions .plan-talk.is-personal-pick').length,
          firstTime: first.querySelector('.plan-entry-time strong').textContent,
          firstTitle: first.querySelector('h3').textContent,
          firstTalks: first.querySelectorAll('.plan-talk').length,
          firstPicks: first.querySelectorAll('.plan-talk.is-personal-pick').length,
          firstCodes: [...first.querySelectorAll('.plan-talk-code-row b')]
            .map((item) => item.textContent),
          mergedTalks: merged?.querySelectorAll('.plan-talk').length,
          mergedPicks: merged?.querySelectorAll('.plan-talk.is-personal-pick').length,
          mergedNotes: merged?.querySelectorAll('.plan-entry-note').length,
        });
      } else if (attempts++ > 100) {
        clearInterval(timer);
        reject(new Error('個人スケジュールの描画が完了しませんでした'));
      }
    }, 50);
  })
`);

assert.deepEqual(personalPlan, {
  activeTab: "plan",
  planHidden: false,
  count: "11セッション",
  sessions: 11,
  talks: 78,
  picks: 27,
  firstTime: "8:50",
  firstTitle: "合意形成(1)",
  firstTalks: 6,
  firstPicks: 2,
  firstCodes: ["VI-31", "VI-32", "VI-33", "VI-34", "VI-35", "VI-36"],
  mergedTalks: 8,
  mergedPicks: 4,
  mergedNotes: 2,
});

console.log(
  JSON.stringify({ initial, upcoming, grouped, filtered, themed, multiSelected, personalPlan }, null, 2),
);
await call("Browser.close").catch(() => {});
socket.close();
