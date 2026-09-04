"""全イベントの設定・セッション・カテゴリ参照整合性を検証する。"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.event_schema import presentation_code, validate_sessions


ROOT = Path(__file__).resolve().parents[1]
EVENTS_ROOT = ROOT / "events"


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def event_file(event_dir: Path, relative: str) -> Path:
    path = (event_dir / relative).resolve()
    if event_dir.resolve() not in path.parents:
        raise ValueError(f"イベント外のデータパスは指定できません: {relative}")
    if not path.is_file():
        raise ValueError(f"イベントデータが見つかりません: {path}")
    return path


def validate_categories(
    sessions: list[dict[str, object]], taxonomy: dict[str, object], categories: dict[str, object]
) -> None:
    values_by_axis = {
        axis["id"]: {value["id"] for value in axis["values"]}
        for axis in taxonomy["axes"]  # type: ignore[index]
    }
    collections = taxonomy["browse_collections"]  # type: ignore[index]
    for collection in collections:
        for qualified_id in collection["any"]:
            axis_id, value_id = qualified_id.split(":", 1)
            if value_id not in values_by_axis.get(axis_id, set()):
                raise ValueError(f"未定義のカテゴリ参照です: {qualified_id}")

    session_codes = {
        presentation_code(talk)
        for session in sessions
        for talk in session["talks"]  # type: ignore[index]
    }
    category_items = categories["presentations"]  # type: ignore[index]
    category_codes = {item["code"] for item in category_items}
    if len(category_codes) != len(category_items):
        raise ValueError("カテゴリデータの講演番号が重複しています")
    if category_codes != session_codes:
        missing = sorted(session_codes - category_codes)
        extra = sorted(category_codes - session_codes)
        raise ValueError(f"カテゴリ講演番号が不一致です: missing={missing[:5]}, extra={extra[:5]}")
    for item in category_items:
        for axis_id, value_ids in item["labels"].items():
            if axis_id not in values_by_axis:
                raise ValueError(f"未定義のカテゴリ軸です: {axis_id}")
            invalid = set(value_ids) - values_by_axis[axis_id]
            if invalid:
                raise ValueError(f"未定義のカテゴリ値です: {axis_id}: {sorted(invalid)}")


def validate_event(event_dir: Path) -> tuple[str, int, int]:
    config = load_json(event_dir / "event.json")
    if not isinstance(config, dict) or config.get("schemaVersion") != 1:
        raise ValueError(f"未対応のイベント設定です: {event_dir}")
    if config.get("id") != event_dir.name:
        raise ValueError(f"イベントIDとディレクトリ名が一致しません: {event_dir}")
    dates = set(config["dates"])
    counts = config["expectedCounts"]
    data = config["data"]
    sessions = load_json(event_file(event_dir, data["sessions"]))
    if not isinstance(sessions, list):
        raise ValueError(f"sessions.jsonのルートは配列である必要があります: {event_dir.name}")
    validate_sessions(
        sessions,
        event_dates=dates,
        expected_session_count=counts["sessions"],
        expected_presentation_count=counts["presentations"],
    )
    if config.get("features", {}).get("categories", False):
        taxonomy = load_json(event_file(event_dir, data["taxonomy"]))
        categories = load_json(event_file(event_dir, data["categories"]))
        validate_categories(sessions, taxonomy, categories)
    talk_count = sum(len(session["talks"]) for session in sessions)
    return config["id"], len(sessions), talk_count


def main() -> int:
    event_dirs = sorted(path.parent for path in EVENTS_ROOT.glob("*/event.json"))
    if not event_dirs:
        raise ValueError("イベント設定がありません")
    for event_dir in event_dirs:
        event_id, session_count, talk_count = validate_event(event_dir)
        print(f"{event_id}: {session_count}セッション / {talk_count}講演枠 OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
