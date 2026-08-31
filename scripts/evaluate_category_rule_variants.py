"""全件データで分類フィールド重みの候補を比較する開発用スクリプト。"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from build_category_pilot_v02 import RULES, THRESHOLDS


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data" / "category_all_source.local.json"
TAXONOMY_PATH = ROOT / "data" / "category_taxonomy.json"

VARIANTS = {
    "v02_current": {
        "default": {"title": 5, "keywords": 6, "session": 2, "summary": 3}
    },
    "summary_direct": {
        "default": {"title": 6, "keywords": 7, "session": 4, "summary": 5}
    },
    "axis_sensitive": {
        "default": {"title": 6, "keywords": 7, "session": 4, "summary": 4},
        "domain": {"title": 6, "keywords": 7, "session": 4, "summary": 5},
        "phase": {"title": 6, "keywords": 7, "session": 5, "summary": 3},
        "method": {"title": 6, "keywords": 7, "session": 5, "summary": 4},
        "material": {"title": 6, "keywords": 7, "session": 3, "summary": 4},
        "issue": {"title": 6, "keywords": 7, "session": 5, "summary": 4},
    },
}


def candidates(
    item: dict[str, object], axis_id: str, weights: dict[str, int]
) -> list[tuple[str, int]]:
    fields = {
        "title": str(item["title"]),
        "keywords": " ".join(str(value) for value in item["keywords"]),
        "session": str(item["session"]),
        "summary": str(item["summary"]),
    }
    scores: Counter[str] = Counter()
    for label_id, patterns in RULES[axis_id].items():
        for field_name, text in fields.items():
            for pattern in patterns:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    scores[label_id] += weights[field_name]
    return sorted(
        (
            (label_id, score)
            for label_id, score in scores.items()
            if score >= THRESHOLDS[axis_id]
        ),
        key=lambda pair: (-pair[1], pair[0]),
    )


def main() -> int:
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))["presentations"]
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    axes = {axis["id"]: axis for axis in taxonomy["axes"]}

    result = {}
    for variant_id, variant in VARIANTS.items():
        metrics: Counter[str] = Counter()
        tag_totals: Counter[str] = Counter()
        for item in source:
            item_fallback = False
            for axis_id, axis in axes.items():
                weights = variant.get(axis_id, variant["default"])
                selected = candidates(item, axis_id, weights)
                if not selected and axis["required"]:
                    metrics[f"{axis_id}:fallback"] += 1
                    item_fallback = True
                if len(selected) > axis["max_items"]:
                    metrics[f"{axis_id}:tag_limit"] += 1
                    boundary = int(axis["max_items"])
                    if selected[boundary - 1][1] == selected[boundary][1]:
                        metrics[f"{axis_id}:tag_limit_tie"] += 1
                tag_totals[axis_id] += min(len(selected), axis["max_items"])
            if item_fallback:
                metrics["presentations:low"] += 1
        result[variant_id] = {
            "metrics": dict(metrics),
            "average_tags": {
                axis_id: round(tag_totals[axis_id] / len(source), 3)
                for axis_id in axes
            },
        }

    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
