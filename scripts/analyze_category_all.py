"""全講演の一次分類結果を集計し、公開可能な評価レポートを生成する。"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data" / "category_all_source.local.json"
CLASSIFIED_PATH = ROOT / "data" / "category_all_classified.local.json"
TAXONOMY_PATH = ROOT / "data" / "category_taxonomy.json"
REPORT_PATH = ROOT / "docs" / "category-all-report.md"
REVIEW_PATH = ROOT / "data" / "category_review_queue.local.json"


def table(rows: list[tuple[str, int, float]]) -> list[str]:
    lines = ["| 区分 | 件数 | 割合 |", "|---|---:|---:|"]
    lines.extend(f"| {label} | {count:,} | {ratio:.1%} |" for label, count, ratio in rows)
    return lines


def main() -> int:
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    classified = json.loads(CLASSIFIED_PATH.read_text(encoding="utf-8"))
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))

    source_by_code = {item["code"]: item for item in source["presentations"]}
    items = classified["presentations"]
    total = len(items)
    if set(source_by_code) != {item["code"] for item in items}:
        raise ValueError("抽出元と分類結果の講演番号が一致しません")

    confidence = Counter(item["confidence"] for item in items)
    review_reasons = Counter(
        reason for item in items for reason in item["review_reasons"]
    )
    reviewed = [item for item in items if item["review_required"]]
    source_quality = Counter(
        source_by_code[item["code"]].get("source_quality", "unknown")
        for item in items
    )

    value_labels = {
        axis["id"]: {value["id"]: value["label"] for value in axis["values"]}
        for axis in taxonomy["axes"]
    }
    axis_counts: dict[str, Counter[str]] = defaultdict(Counter)
    empty_counts: Counter[str] = Counter()
    for item in items:
        for axis_id, labels in item["labels"].items():
            if not labels:
                empty_counts[axis_id] += 1
            axis_counts[axis_id].update(labels)

    review_queue = []
    for item in reviewed:
        source_item = source_by_code[item["code"]]
        review_queue.append(
            {
                "code": item["code"],
                "title": source_item["title"],
                "division": source_item["division"],
                "session": source_item["session"],
                "source_quality": source_item.get("source_quality", "unknown"),
                "labels": item["labels"],
                "scores": item["scores"],
                "review_reasons": item["review_reasons"],
            }
        )
    REVIEW_PATH.write_text(
        json.dumps(review_queue, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# JSCE 2026 全講演カテゴリ一次分類レポート",
        "",
        f"対象は全{total:,}講演。梗概要約と著者キーワードはローカル解析にのみ使用し、公開JSONと本レポートには収録しない。",
        "",
        "## 抽出の完全性",
        "",
    ]
    lines.extend(
        table(
            [
                (quality, count, count / total)
                for quality, count in source_quality.most_common()
            ]
        )
    )
    lines.extend(
        [
            "",
            "講演番号は `sessions.json` と完全一致し、欠落・重複・余剰はいずれも0件。標準の内容梗概ページで得られない講演だけ、本文1ページ目を講演番号で照合して補完した。",
            "",
            "## 一次分類の状態",
            "",
        ]
    )
    lines.extend(
        table(
            [
                (level, confidence[level], confidence[level] / total)
                for level in ("high", "medium", "low")
            ]
        )
    )
    lines.extend(
        [
            "",
            f"要確認は **{len(reviewed):,}件（{len(reviewed) / total:.1%}）**。この値は分類ルールが検出した曖昧さであり、人手評価による誤分類率ではない。",
            "",
            "### 要確認理由",
            "",
        ]
    )
    lines.extend(
        table(
            [
                (reason, count, count / total)
                for reason, count in review_reasons.most_common()
            ]
        )
    )

    lines.extend(["", "## 軸別分布", ""])
    for axis in taxonomy["axes"]:
        axis_id = axis["id"]
        lines.extend([f"### {axis['label']}（`{axis_id}`）", ""])
        rows = [
            (value_labels[axis_id][value_id], count, count / total)
            for value_id, count in axis_counts[axis_id].most_common()
        ]
        if not axis["required"]:
            rows.append(("タグなし", empty_counts[axis_id], empty_counts[axis_id] / total))
        lines.extend(table(rows))
        lines.append("")

    lines.extend(
        [
            "## 解釈上の注意",
            "",
            "- 1講演に複数タグを許すため、軸内の割合は合計100%にならない。",
            "- `high` は規則上の根拠が強いことを表し、正解率を保証する指標ではない。",
            "- `fallback` は必須軸に直接根拠がなく、公式部門等から暫定付与したもの。",
            "- `tag_limit_tie` は軸の上限境界で候補スコアが同点となり、上位候補へ暫定的に切り詰めたもの。",
            "- 要確認用の題名・スコア付きキューは、Git管理対象外のローカルJSONに保存する。",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"対象: {total}講演")
    print(f"信頼度: {dict(confidence)}")
    print(f"要確認: {len(reviewed)}件 / {dict(review_reasons)}")
    print(f"抽出元: {dict(source_quality)}")
    print(f"レポート: {REPORT_PATH}")
    print(f"確認キュー: {REVIEW_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
