"""独自カテゴリ定義と試行分類の整合性を検証する。"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = ROOT / "data" / "category_taxonomy.json"
PILOT_PATH = ROOT / "data" / "category_pilot.json"
SESSIONS_PATH = ROOT / "data" / "sessions.json"


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    taxonomy = load_json(TAXONOMY_PATH)
    pilot = load_json(PILOT_PATH)
    sessions = load_json(SESSIONS_PATH)
    assert isinstance(taxonomy, dict)
    assert isinstance(pilot, dict)
    assert isinstance(sessions, list)

    axes = taxonomy["axes"]
    axis_by_id = {axis["id"]: axis for axis in axes}
    if len(axis_by_id) != len(axes):
        raise ValueError("分類軸IDが重複しています")

    valid_values: dict[str, set[str]] = {}
    for axis in axes:
        values = [value["id"] for value in axis["values"]]
        if len(values) != len(set(values)):
            raise ValueError(f"{axis['id']}軸の値IDが重複しています")
        valid_values[axis["id"]] = set(values)

    talk_by_code = {
        talk[1]: {"title": talk[2], "division": session["division"]}
        for session in sessions
        for talk in session["talks"]
    }
    examples = pilot["presentations"]
    codes = [example["code"] for example in examples]
    if len(codes) != len(set(codes)):
        raise ValueError("試行分類の講演番号が重複しています")

    confidence_counts: Counter[str] = Counter()
    division_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    allowed_confidence = set(taxonomy["classification_policy"]["confidence_levels"])

    for example in examples:
        code = example["code"]
        if code not in talk_by_code:
            raise ValueError(f"sessions.jsonに存在しない講演番号です: {code}")
        if example["confidence"] not in allowed_confidence:
            raise ValueError(f"不正な信頼度です: {code}")

        labels = example["labels"]
        if set(labels) != set(axis_by_id):
            raise ValueError(f"分類軸が不足または過剰です: {code}")

        for axis_id, selected in labels.items():
            axis = axis_by_id[axis_id]
            if len(selected) != len(set(selected)):
                raise ValueError(f"同じタグが重複しています: {code} / {axis_id}")
            if not axis["min_items"] <= len(selected) <= axis["max_items"]:
                raise ValueError(f"タグ件数が範囲外です: {code} / {axis_id}")
            unknown = set(selected) - valid_values[axis_id]
            if unknown:
                raise ValueError(f"未定義タグです: {code} / {sorted(unknown)}")
            label_counts.update(f"{axis_id}:{value}" for value in selected)

        confidence_counts[example["confidence"]] += 1
        division_counts[talk_by_code[code]["division"]] += 1

    collection_ids = [collection["id"] for collection in taxonomy["browse_collections"]]
    if len(collection_ids) != len(set(collection_ids)):
        raise ValueError("表示用コレクションIDが重複しています")
    all_qualified_values = {
        f"{axis_id}:{value}" for axis_id, values in valid_values.items() for value in values
    }
    for collection in taxonomy["browse_collections"]:
        unknown = set(collection["any"]) - all_qualified_values
        if unknown:
            raise ValueError(f"表示用コレクションに未定義タグがあります: {collection['id']}")

    print(f"検証完了: {len(axes)}軸 / {len(collection_ids)}表示テーマ / {len(examples)}試行講演")
    print("公式分類別:", dict(sorted(division_counts.items())))
    print("信頼度別:", dict(sorted(confidence_counts.items())))
    print(f"試行で使用したタグ: {len(label_counts)}種類")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
