"""Chrome DevTools ProtocolでJSCE/JSME両画面を検証する。"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

from websockets.sync.client import connect


CHROME_CANDIDATES = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
)


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def find_chrome() -> Path:
    path = next((candidate for candidate in CHROME_CANDIDATES if candidate.is_file()), None)
    if path is None:
        raise RuntimeError("ChromeまたはEdgeが見つかりません")
    return path


def wait_for_target(port: int) -> dict[str, Any]:
    url = f"http://127.0.0.1:{port}/json/list"
    for _ in range(100):
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                targets = json.load(response)
            target = next((item for item in targets if item.get("type") == "page"), None)
            if target:
                return target
        except (OSError, ValueError):
            time.sleep(0.05)
    raise RuntimeError("ブラウザのデバッグ接続を開始できませんでした")


class Cdp:
    def __init__(self, websocket_url: str) -> None:
        self.socket = connect(websocket_url, origin="http://127.0.0.1")
        self.next_id = 1

    def close(self) -> None:
        self.socket.close()

    def call(self, method: str, params: dict[str, object] | None = None) -> dict[str, Any]:
        call_id = self.next_id
        self.next_id += 1
        self.socket.send(json.dumps({"id": call_id, "method": method, "params": params or {}}))
        while True:
            message = json.loads(self.socket.recv())
            if message.get("id") != call_id:
                continue
            if "error" in message:
                raise RuntimeError(f"CDP {method}: {message['error']}")
            return message.get("result", {})

    def evaluate(self, expression: str) -> Any:
        for attempt in range(30):
            try:
                result = self.call(
                    "Runtime.evaluate",
                    {
                        "expression": expression,
                        "awaitPromise": True,
                        "returnByValue": True,
                    },
                )
            except RuntimeError as error:
                if "Execution context was destroyed" in str(error) and attempt < 29:
                    time.sleep(0.05)
                    continue
                raise
            if "exceptionDetails" not in result:
                return result["result"].get("value")
            description = (
                result["exceptionDetails"].get("exception", {}).get("description")
                or result["exceptionDetails"].get("text", "JavaScript evaluation failed")
            )
            if "context" in description.lower() and attempt < 29:
                time.sleep(0.05)
                continue
            raise RuntimeError(description)
        raise RuntimeError("JavaScript実行コンテキストを取得できませんでした")


def wait_expression(condition: str, value: str) -> str:
    return f"""
      new Promise((resolve, reject) => {{
        let attempts = 0;
        const timer = setInterval(() => {{
          if ({condition}) {{
            clearInterval(timer);
            resolve({value});
          }} else if (attempts++ > 200) {{
            clearInterval(timer);
            reject(new Error('画面の描画が完了しませんでした'));
          }}
        }}, 50);
      }})
    """


def verify_jsce(cdp: Cdp) -> dict[str, Any]:
    initial = cdp.evaluate(
        wait_expression(
            "document.querySelectorAll('#division-filter input').length === 8",
            "({"
            "title: document.title,"
            "brand: document.querySelector('#brand-name').textContent,"
            "tabs: document.querySelectorAll('[data-program-tab]').length,"
            "sessions: sessions.length,"
            "talks: sessions.reduce((sum, session) => sum + session.talks.length, 0),"
            "themes: document.querySelectorAll('#theme-filter input').length,"
            "campuses: document.querySelectorAll('#campus-filter input').length"
            "})",
        )
    )
    assert initial == {
        "title": "JSCE 2026 Navigator",
        "brand": "JSCE 2026",
        "tabs": 5,
        "sessions": 748,
        "talks": 5636,
        "themes": 19,
        "campuses": 2,
    }, initial
    upcoming = cdp.evaluate(
        """
        new Promise((resolve) => {
          const input = document.querySelector('#reference-datetime');
          input.value = '2026-09-02T10:15';
          input.dispatchEvent(new Event('change', { bubbles: true }));
          setTimeout(() => {
            document.querySelector('#upcoming-sessions .session-card:has(.session-current-talk)').click();
            setTimeout(() => resolve({
              count: document.querySelector('#session-count').textContent,
              cards: document.querySelectorAll('#upcoming-sessions .session-card').length,
              dialogOpen: document.querySelector('#session-dialog').open,
              currentTalks: document.querySelectorAll('#session-dialog .talk-item.is-current').length
            }), 50);
          }, 50);
        })
        """
    )
    assert upcoming == {
        "count": "88件",
        "cards": 88,
        "dialogOpen": True,
        "currentTalks": 1,
    }, upcoming
    return {"initial": initial, "upcoming": upcoming}


def verify_jsme(cdp: Cdp, base_url: str) -> dict[str, Any]:
    cdp.call("Page.navigate", {"url": f"{base_url}/jsme2026/"})
    initial = cdp.evaluate(
        wait_expression(
            "document.title === 'JSME 2026 Navigator' && sessions.length === 250 && document.querySelectorAll('#division-filter input').length === 17",
            "({"
            "title: document.title,"
            "brand: document.querySelector('#brand-name').textContent,"
            "tabs: document.querySelectorAll('[data-program-tab]').length,"
            "sessions: sessions.length,"
            "talks: sessions.reduce((sum, session) => sum + session.talks.length, 0),"
            "groups: new Set(sessions.map((session) => session.group)).size,"
            "organizedSessions: new Set(sessions.filter((session) => /^[JS]\\d{3}p?$/.test(session.code)).map((session) => session.code.replace(/p$/, ''))).size,"
            "themes: document.querySelectorAll('#theme-filter input').length,"
            "divisions: document.querySelectorAll('#division-filter input').length,"
            "campuses: document.querySelectorAll('#campus-filter input').length"
            "})",
        )
    )
    assert initial == {
        "title": "JSME 2026 Navigator",
        "brand": "JSME 2026",
        "tabs": 6,
        "sessions": 250,
        "talks": 1096,
        "groups": 7,
        "organizedSessions": 61,
        "themes": 46,
        "divisions": 17,
        "campuses": 6,
    }, initial

    session = cdp.evaluate(
        """
        new Promise((resolve) => {
          document.querySelector('[data-program-tab="2026-09-07"]').click();
          const query = document.querySelector('#query-filter');
          query.value = 'S171-01';
          query.dispatchEvent(new Event('input', { bubbles: true }));
          setTimeout(() => {
            document.querySelector('#schedule-sessions .session-card').click();
            setTimeout(() => resolve({
              cards: document.querySelectorAll('#schedule-sessions .session-card').length,
              dialogOpen: document.querySelector('#session-dialog').open,
              code: document.querySelector('#session-dialog .talk-code').textContent,
              title: document.querySelector('#session-dialog .talk-title').textContent,
              author: document.querySelector('#session-dialog .talk-authors').textContent,
              href: document.querySelector('#session-dialog .talk-link').href
            }), 50);
          }, 50);
        })
        """
    )
    assert session["cards"] == 1, session
    assert session["dialogOpen"] is True, session
    assert session["code"] == "S171-01", session
    assert "PDCA" in session["title"], session
    assert "中村 瑞穂" in session["author"], session
    assert session["href"].endswith("/S171-01"), session
    untimed = cdp.evaluate(
        """
        new Promise((resolve) => {
          document.querySelector('#session-dialog-close').click();
          document.querySelector('#clear-filters').click();
          document.querySelector('[data-program-tab="2026-09-06"]').click();
          const query = document.querySelector('#query-filter');
          query.value = 'C253-1';
          query.dispatchEvent(new Event('input', { bubbles: true }));
          setTimeout(() => {
            document.querySelector('#schedule-sessions .session-card').click();
            setTimeout(() => resolve({
              cards: document.querySelectorAll('#schedule-sessions .session-card').length,
              code: document.querySelector('#session-dialog .talk-code').textContent,
              time: document.querySelector('#session-dialog .talk-time span').textContent,
              currentTalks: document.querySelectorAll('#session-dialog .talk-item.is-current').length
            }), 50);
          }, 50);
        })
        """
    )
    assert untimed == {
        "cards": 1,
        "code": "C253-1",
        "time": "時刻記載なし",
        "currentTalks": 0,
    }, untimed
    return {"initial": initial, "session": session, "untimed": untimed}


def verify_personal_plan(cdp: Cdp, base_url: str) -> dict[str, Any]:
    cdp.call("Page.navigate", {"url": f"{base_url}/?plan=tocchibo"})
    result = cdp.evaluate(
        wait_expression(
            "document.querySelectorAll('#plan-sessions .plan-entry').length === 12",
            "({"
            "activeTab: document.querySelector('.program-tab.is-active').dataset.programTab,"
            "count: document.querySelector('#plan-count').textContent,"
            "sessions: document.querySelectorAll('#plan-sessions .plan-entry').length,"
            "talks: document.querySelectorAll('#plan-sessions .plan-talk').length"
            "})",
        )
    )
    assert result == {
        "activeTab": "plan",
        "count": "11予定・1参考",
        "sessions": 12,
        "talks": 86,
    }, result
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--event",
        choices=("all", "jsce", "jsme"),
        default="all",
        help="検証対象（既定値: all）",
    )
    args = parser.parse_args()
    debug_port = free_port()
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with tempfile.TemporaryDirectory(
        prefix="conference-navigator-chrome-", ignore_cleanup_errors=True
    ) as profile:
        browser = subprocess.Popen(
            [
                str(find_chrome()),
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--remote-allow-origins=*",
                f"--remote-debugging-port={debug_port}",
                f"--user-data-dir={profile}",
                f"{args.base_url}/",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        cdp: Cdp | None = None
        try:
            target = wait_for_target(debug_port)
            cdp = Cdp(target["webSocketDebuggerUrl"])
            result = {}
            if args.event in {"all", "jsce"}:
                result["jsce"] = verify_jsce(cdp)
                result["plan"] = verify_personal_plan(cdp, args.base_url)
            if args.event in {"all", "jsme"}:
                result["jsme"] = verify_jsme(cdp, args.base_url)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        finally:
            if cdp is not None:
                try:
                    cdp.call("Browser.close")
                except Exception:
                    pass
                cdp.close()
            browser.wait(timeout=10)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
