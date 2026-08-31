"""全講演をv0.2分類体系で一次分類し、公開用カテゴリJSONを生成する。"""

from __future__ import annotations

import json
from pathlib import Path

from build_category_pilot_v02 import classify


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data" / "category_all_source.local.json"
TAXONOMY_PATH = ROOT / "data" / "category_taxonomy.json"
PUBLIC_OUTPUT_PATH = ROOT / "data" / "categories.json"
LOCAL_OUTPUT_PATH = ROOT / "data" / "category_all_classified.local.json"
EXPECTED_PRESENTATIONS = 5636


def main() -> int:
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    axis_by_id = {axis["id"]: axis for axis in taxonomy["axes"]}
    source_items = source["presentations"]
    if len(source_items) != EXPECTED_PRESENTATIONS:
        raise ValueError(f"抽出講演数が想定外です: {len(source_items)}")

    classified = [classify(item, axis_by_id) for item in source_items]
    if len({item["code"] for item in classified}) != EXPECTED_PRESENTATIONS:
        raise ValueError("分類後の講演番号が重複しています")

    local_output = {
        "taxonomy_version": taxonomy["schema_version"],
        "status": "machine_first_pass_with_scores",
        "classification_method": "axis-sensitive explicit evidence rules v0.3",
        "presentations": classified,
    }
    LOCAL_OUTPUT_PATH.write_text(
        json.dumps(local_output, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    public_items = [
        {
            "code": item["code"],
            "labels": item["labels"],
            "confidence": item["confidence"],
            "review_required": item["review_required"],
            "review_reasons": item["review_reasons"],
        }
        for item in classified
    ]
    public_output = {
        "taxonomy_version": taxonomy["schema_version"],
        "status": "machine_first_pass",
        "classification_method": "axis-sensitive explicit evidence rules v0.3",
        "presentation_count": len(public_items),
        "presentations": public_items,
    }
    PUBLIC_OUTPUT_PATH.write_text(
        json.dumps(public_output, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    reviews = sum(bool(item["review_required"]) for item in classified)
    print(
        f"全件分類完了: {len(classified)}講演 / 要確認 {reviews}件 -> "
        f"{PUBLIC_OUTPUT_PATH}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
