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
      const divisionOptions = document.querySelector('#division-filter').options.length;
      const themeOptions = document.querySelector('#theme-filter').options.length;
      const referenceValue = document.querySelector('#reference-datetime').value;
      if (divisionOptions === 9 && themeOptions === 20 && referenceValue) {
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
  divisionOptions: 9,
  themeOptions: 20,
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
    setTimeout(() => resolve({
      count: document.querySelector('#session-count').textContent,
      upcomingCards: document.querySelectorAll('#upcoming-sessions .session-card').length,
      nowHidden: document.querySelector('#now-view').hidden,
      scheduleHidden: document.querySelector('#schedule-view').hidden,
    }), 100);
  })
`);

assert.deepEqual(upcoming, {
  count: "88件",
  upcomingCards: 88,
  nowHidden: false,
  scheduleHidden: true,
});

const filtered = await evaluate(`
  new Promise((resolve) => {
    document.querySelector('[data-program-tab="2026-09-02"]').click();
    const input = document.querySelector('#query-filter');
    input.value = '留萌開発事務所';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    setTimeout(() => {
      const card = document.querySelector('#schedule-sessions .session-card');
      card.open = true;
      setTimeout(() => resolve({
        count: document.querySelector('#session-count').textContent,
        upcomingCards: document.querySelectorAll('#upcoming-sessions .session-card').length,
        dayCards: document.querySelectorAll('#schedule-sessions .session-card').length,
        links: [...card.querySelectorAll('.talk-link')].map((link) => link.href),
        authors: [...card.querySelectorAll('.talk-authors')].map((item) => item.textContent),
        affiliations: [...card.querySelectorAll('.talk-affiliations')].map((item) => item.textContent),
        talkTags: [...card.querySelectorAll('.talk-tag')].map((item) => item.textContent),
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
assert.equal(filtered.nowHidden, true);
assert.equal(filtered.scheduleHidden, false);
assert.equal(filtered.referencePanelVisible, false);
assert.ok(filtered.links.some((url) => url.endsWith("/CS18-07")));
assert.ok(filtered.authors.some((value) => value.includes("千葉 雄貴")));
assert.ok(filtered.affiliations.some((value) => value.includes("留萌開発事務所")));
assert.ok(filtered.talkTags.length > 0);

const themed = await evaluate(`
  new Promise((resolve) => {
    document.querySelector('#clear-filters').click();
    document.querySelector('[data-program-tab="2026-09-04"]').click();
    const select = document.querySelector('#theme-filter');
    select.value = 'space';
    select.dispatchEvent(new Event('change', { bubbles: true }));
    setTimeout(() => resolve({
      dayCards: document.querySelectorAll('#schedule-sessions .session-card').length,
      themeLabels: [...document.querySelectorAll('#schedule-sessions .session-themes')]
        .map((item) => item.textContent),
      filterActive: document.querySelector('#filter-summary').classList.contains('has-filter'),
    }), 100);
  })
`);

assert.ok(themed.dayCards >= 3);
assert.ok(themed.themeLabels.every((value) => value.includes("宇宙・月面")));
assert.equal(themed.filterActive, true);

console.log(JSON.stringify({ initial, upcoming, filtered, themed }, null, 2));
await call("Browser.close").catch(() => {});
socket.close();
