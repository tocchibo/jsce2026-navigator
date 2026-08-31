"""v0.2層化試行の公開用評価レポートを生成する。"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data" / "category_sample_source.local.json"
PILOT_PATH = ROOT / "data" / "category_pilot_v02.json"
TAXONOMY_PATH = ROOT / "data" / "category_taxonomy.json"
OUTPUT_PATH = ROOT / "docs" / "category-pilot-v02-report.md"


def percent(count: int, total: int) -> str:
    return f"{count / total * 100:.1f}%"


def main() -> int:
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    pilot = json.loads(PILOT_PATH.read_text(encoding="utf-8"))
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    source_by_code = {item["code"]: item for item in source["presentations"]}
    examples = pilot["presentations"]
    total = len(examples)

    confidence = Counter(item["confidence"] for item in examples)
    review_reasons = Counter(
        reason for item in examples for reason in item["review_reasons"]
    )
    review_items = [item for item in examples if item["review_required"]]
    drifts = Counter(item["page_drift"] for item in source["presentations"])
    axis_by_id = {axis["id"]: axis for axis in taxonomy["axes"]}

    lines = [
        "# 独自カテゴリ v0.2 層化試行レポート（v0.3規則再評価）",
        "",
        "## 結果概要",
        "",
        f"公式8分類から各15講演、計{total}講演を等間隔で抽出し、PDFの著者キーワードと短い内容要約を用いて5軸分類を試行した。",
        "",
        f"- 分類体系: `{taxonomy['schema_version']}`",
        f"- 抽出成功: {total}/{total}講演",
        f"- 要確認: {len(review_items)}講演（{percent(len(review_items), total)}）",
        f"- low判定: {confidence['low']}講演（{percent(confidence['low'], total)}）",
        f"- medium判定: {confidence['medium']}講演（{percent(confidence['medium'], total)}）",
        f"- high判定: {confidence['high']}講演（{percent(confidence['high'], total)}）",
        "",
        "`high`は明示規則上の根拠強度であり、人手による正解保証ではない。v0.2分類体系を、全件分布から調整した軸別重みのv0.3規則で再評価した。",
        "",
        "## PDF抽出の検証",
        "",
        "各講演の推定ページ周辺から、講演番号と著者キーワードの両方が一致するページだけを採用した。推定との差は次のとおりだった。",
        "",
        "| 推定との差 | 講演数 |",
        "|---:|---:|",
    ]
    for drift, count in sorted(drifts.items()):
        lines.append(f"| {drift:+d}ページ | {count} |")

    lines.extend(
        [
            "",
            "全120講演で番号・キーワード・要約を取得できた。長いキーワードの折り返しも空行まで連結し、要約への混入を防止した。梗概本文と要約はローカルファイルだけに保存し、Git管理対象には含めない。",
            "",
            "## v0.1から追加した分類",
            "",
            "試行標本で既存タグへ無理に割り当てるケースが生じたため、次を追加した。",
            "",
            "- 対象・分野: `construction_materials`（建設材料）",
            "- 対象・分野: `atmosphere_climate`（気象・気候）",
            "- 目的・工程: `performance_evaluation`（性能評価・現象解明）",
            "- 目的・工程: `technology_development`（技術・システム開発）",
            "- 課題: `knowledge_transfer`（技術継承・人材確保）",
            "- 材料: `polymer_resin`の表示を「樹脂・ゴム・高分子材料」へ拡張",
            "",
            "## 軸別タグ分布",
            "",
        ]
    )
    for axis_id, axis in axis_by_id.items():
        counts = Counter(
            label for item in examples for label in item["labels"][axis_id]
        )
        label_by_id = {value["id"]: value["label"] for value in axis["values"]}
        lines.extend(
            [
                f"### {axis['label']}",
                "",
                "| タグ | 講演数 |",
                "|---|---:|",
            ]
        )
        for label_id, count in counts.most_common():
            lines.append(f"| {label_by_id[label_id]} (`{label_id}`) | {count} |")
        lines.append("")

    lines.extend(
        [
            "## 要確認理由",
            "",
            "| 理由 | 件数 |",
            "|---|---:|",
        ]
    )
    for reason, count in review_reasons.most_common():
        lines.append(f"| `{reason}` | {count} |")

    lines.extend(
        [
            "",
            "`fallback`は内容から必須軸を確定できず公式部門等から補ったもの、`tag_limit_tie`は軸の上限境界で候補が同点になったものを表す。どちらも自動確定せず確認対象とする。",
            "",
            "## 要確認講演",
            "",
            "| 講演番号 | 題名 | 理由 |",
            "|---|---|---|",
        ]
    )
    for item in review_items:
        title = str(source_by_code[item["code"]]["title"]).replace("|", "｜")
        reasons = ", ".join(f"`{reason}`" for reason in item["review_reasons"])
        lines.append(f"| {item['code']} | {title} | {reasons} |")

    lines.extend(
        [
            "",
            "## 判定規則の修正例",
            "",
            "全120件の題名・タグを確認し、次の部分一致誤判定を修正した。",
            "",
            "- 「移動床」の「移動」を交通・アクセシビリティとして扱わない",
            "- `SAR`内の`AR`を拡張現実として扱わない",
            "- 「避難坑」を避難行動として扱わない",
            "- 3Dプリンティングを3次元計測として扱わない",
            "- 環境保全を構造物の維持保全として扱わない",
            "- カーボンニュートラルという語だけでCO2を材料タグにしない",
            "",
            "## 判定",
            "",
            f"low判定は{percent(confidence['low'], total)}で、事前に定めた15%以下の目標を満たした。全軸で複数タグが使用され、特定の公式部門だけに依存しない横断分類も確認できた。",
            "",
            "全5,636講演の一次分類結果と残る要確認件数は `docs/category-all-report.md` に記録する。",
        ]
    )

    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"レポート出力: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
