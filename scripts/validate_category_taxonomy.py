"""独自カテゴリ定義と試行分類の整合性を検証する。"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JSCE_DATA = ROOT / "events" / "jsce2026"
TAXONOMY_PATH = JSCE_DATA / "category_taxonomy.json"
PILOT_PATHS = [
    JSCE_DATA / "category_pilot.json",
    JSCE_DATA / "category_pilot_v02.json",
]
SESSIONS_PATH = JSCE_DATA / "sessions.json"
CATEGORIES_PATH = JSCE_DATA / "categories.json"


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    taxonomy = load_json(TAXONOMY_PATH)
    sessions = load_json(SESSIONS_PATH)
    assert isinstance(taxonomy, dict)
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
    allowed_confidence = set(taxonomy["classification_policy"]["confidence_levels"])

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

    print(f"分類体系: {len(axes)}軸 / {len(collection_ids)}表示テーマ")
    for pilot_path in PILOT_PATHS:
        pilot = load_json(pilot_path)
        assert isinstance(pilot, dict)
        if pilot_path.name == "category_pilot_v02.json":
            if pilot["taxonomy_version"] != taxonomy["schema_version"]:
                raise ValueError("v0.2試行分類と分類体系のバージョンが一致しません")

        examples = pilot["presentations"]
        codes = [example["code"] for example in examples]
        if len(codes) != len(set(codes)):
            raise ValueError(f"試行分類の講演番号が重複しています: {pilot_path.name}")

        confidence_counts: Counter[str] = Counter()
        division_counts: Counter[str] = Counter()
        label_counts: Counter[str] = Counter()
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

            scores = example.get("scores")
            if scores is not None:
                if set(scores) != set(axis_by_id):
                    raise ValueError(f"スコア軸が不足または過剰です: {code}")
                for axis_id, selected in labels.items():
                    if set(scores[axis_id]) != set(selected):
                        raise ValueError(f"タグとスコアが一致しません: {code} / {axis_id}")

            confidence_counts[example["confidence"]] += 1
            division_counts[talk_by_code[code]["division"]] += 1

        print(
            f"{pilot_path.name}: {len(examples)}講演 / "
            f"信頼度 {dict(sorted(confidence_counts.items()))} / "
            f"使用タグ {len(label_counts)}種類"
        )

    categories = load_json(CATEGORIES_PATH)
    assert isinstance(categories, dict)
    if categories["taxonomy_version"] != taxonomy["schema_version"]:
        raise ValueError("全件分類と分類体系のバージョンが一致しません")
    public_items = categories["presentations"]
    if categories["presentation_count"] != len(public_items):
        raise ValueError("全件分類の件数メタデータが実データと一致しません")
    public_codes = [item["code"] for item in public_items]
    if len(public_codes) != len(set(public_codes)):
        raise ValueError("全件分類の講演番号が重複しています")
    if set(public_codes) != set(talk_by_code):
        missing = sorted(set(talk_by_code) - set(public_codes))[:10]
        extra = sorted(set(public_codes) - set(talk_by_code))[:10]
        raise ValueError(f"全件分類の講演番号が不一致です: 欠落={missing}, 余剰={extra}")

    public_confidence: Counter[str] = Counter()
    public_label_counts: Counter[str] = Counter()
    review_count = 0
    forbidden_fields = {"summary", "keywords", "scores", "evidence_fields"}
    for item in public_items:
        code = item["code"]
        leaked = forbidden_fields & set(item)
        if leaked:
            raise ValueError(f"公開用分類に非公開フィールドがあります: {code} / {sorted(leaked)}")
        if item["confidence"] not in allowed_confidence:
            raise ValueError(f"全件分類の信頼度が不正です: {code}")
        if not isinstance(item["review_required"], bool):
            raise ValueError(f"review_requiredが真偽値ではありません: {code}")
        if item["review_required"] != bool(item["review_reasons"]):
            raise ValueError(f"要確認フラグと理由が一致しません: {code}")

        labels = item["labels"]
        if set(labels) != set(axis_by_id):
            raise ValueError(f"全件分類の軸が不足または過剰です: {code}")
        for axis_id, selected in labels.items():
            axis = axis_by_id[axis_id]
            if len(selected) != len(set(selected)):
                raise ValueError(f"全件分類のタグが重複しています: {code} / {axis_id}")
            if not axis["min_items"] <= len(selected) <= axis["max_items"]:
                raise ValueError(f"全件分類のタグ件数が範囲外です: {code} / {axis_id}")
            unknown = set(selected) - valid_values[axis_id]
            if unknown:
                raise ValueError(f"全件分類に未定義タグがあります: {code} / {sorted(unknown)}")
            public_label_counts.update(f"{axis_id}:{value}" for value in selected)

        public_confidence[item["confidence"]] += 1
        review_count += int(item["review_required"])

    low_ratio = public_confidence["low"] / len(public_items)
    if low_ratio > 0.15:
        raise ValueError(f"low判定が品質基準15%を超えています: {low_ratio:.1%}")
    print(
        f"categories.json: {len(public_items)}講演 / "
        f"要確認 {review_count}件 / 信頼度 {dict(sorted(public_confidence.items()))} / "
        f"使用タグ {len(public_label_counts)}種類"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
