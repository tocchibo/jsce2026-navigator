"""PDFから層化標本の著者キーワードと短い内容要約をローカル抽出する。"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ABSTRACT_START_PAGE = 738
PAGES_PER_PRESENTATION = 3
SAMPLE_PER_DIVISION = 15
CODE_RE = re.compile(r"\[([^]\r\n]+)\]")
KEYWORDS_RE = re.compile(r"キーワード\s*[：:]\s*(.*)")
COPYRIGHT_RE = re.compile(r"^\s*©\s*(?:2026\s+)?Japan Society of Civil Engineers", re.MULTILINE)


def compact(value: str) -> str:
    return " ".join(value.replace("\u3000", " ").split())


def flattened_talks(sessions: list[dict[str, object]]) -> list[dict[str, object]]:
    """3ページ規則に基づく梗概要約ページ番号を講演へ付与する。"""
    result: list[dict[str, object]] = []
    session_page = ABSTRACT_START_PAGE
    for session in sessions:
        talks = session["talks"]
        assert isinstance(talks, list)
        for index, talk in enumerate(talks):
            result.append(
                {
                    "code": talk[1],
                    "title": talk[2],
                    "division": session["division"],
                    "session": session["title"],
                    "page": session_page + 1 + PAGES_PER_PRESENTATION * index,
                }
            )
        session_page += 1 + PAGES_PER_PRESENTATION * len(talks)
    return result


def stratified_sample(talks: list[dict[str, object]]) -> list[dict[str, object]]:
    by_division: dict[str, list[dict[str, object]]] = defaultdict(list)
    for talk in talks:
        by_division[str(talk["division"])].append(talk)

    selected: list[dict[str, object]] = []
    for division in sorted(by_division):
        group = by_division[division]
        if len(group) < SAMPLE_PER_DIVISION:
            raise ValueError(f"標本数を確保できません: {division} / {len(group)}")
        indexes = [
            round(position * (len(group) - 1) / (SAMPLE_PER_DIVISION - 1))
            for position in range(SAMPLE_PER_DIVISION)
        ]
        if len(indexes) != len(set(indexes)):
            raise ValueError(f"標本位置が重複しました: {division}")
        selected.extend(group[index] for index in indexes)
    return sorted(selected, key=lambda item: int(item["page"]))


def extract_range(executable: str, pdf_path: Path, first_page: int, last_page: int) -> str:
    completed = subprocess.run(
        [
            executable,
            "-f",
            str(first_page),
            "-l",
            str(last_page),
            "-enc",
            "UTF-8",
            "-layout",
            str(pdf_path),
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"PDF {first_page}-{last_page}ページの抽出に失敗しました: {message}"
        )
    return completed.stdout.decode("utf-8", errors="replace")


def locate_summary(
    executable: str, pdf_path: Path, expected_code: str, estimated_page: int
) -> tuple[int, str]:
    exact_text = extract_range(executable, pdf_path, estimated_page, estimated_page)
    if re.search(rf"\[{re.escape(expected_code)}\]", exact_text) and KEYWORDS_RE.search(exact_text):
        return estimated_page, exact_text

    for radius in (8, 24, 64):
        first_page = max(ABSTRACT_START_PAGE, estimated_page - radius)
        last_page = estimated_page + radius
        text = extract_range(executable, pdf_path, first_page, last_page)
        for offset, page_text in enumerate(text.split("\f")):
            page = first_page + offset
            if (
                re.search(rf"\[{re.escape(expected_code)}\]", page_text)
                and KEYWORDS_RE.search(page_text)
            ):
                return page, page_text
    raise ValueError(
        f"推定位置の周辺で梗概要約を特定できません: {expected_code} / {estimated_page}ページ"
    )


def parse_summary(text: str, expected_code: str, page: int) -> tuple[list[str], str]:
    codes = [compact(match.group(1)) for match in CODE_RE.finditer(text)]
    if expected_code not in codes:
        raise ValueError(
            f"推定ページと講演番号が一致しません: {expected_code} / {page}ページ / {codes[:5]}"
        )

    lines = text.splitlines()
    keyword_index = next(
        (index for index, line in enumerate(lines) if KEYWORDS_RE.search(line)), None
    )
    if keyword_index is None:
        raise ValueError(f"著者キーワードが見つかりません: {expected_code} / {page}ページ")
    keyword_match = KEYWORDS_RE.search(lines[keyword_index])
    assert keyword_match is not None
    keyword_parts = [keyword_match.group(1)]
    summary_index = keyword_index + 1
    while summary_index < len(lines) and compact(lines[summary_index]):
        keyword_parts.append(lines[summary_index])
        summary_index += 1
    keyword_text = compact("".join(keyword_parts))
    keywords = [compact(item) for item in re.split(r"[、，,]", keyword_text) if compact(item)]

    while summary_index < len(lines) and not compact(lines[summary_index]):
        summary_index += 1
    summary_lines: list[str] = []
    for line in lines[summary_index:]:
        if COPYRIGHT_RE.match(line):
            break
        summary_lines.append(line)
    if not summary_lines:
        raise ValueError(f"要約末尾が見つかりません: {expected_code} / {page}ページ")
    summary = compact("\n".join(summary_lines))
    if len(summary) < 20:
        raise ValueError(f"内容要約が短すぎます: {expected_code} / {page}ページ")
    return keywords, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pdf",
        type=Path,
        default=ROOT / "2026" / "jsce2026_program_all.pdf",
    )
    parser.add_argument(
        "--sessions",
        type=Path,
        default=ROOT / "data" / "sessions.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "category_sample_source.local.json",
    )
    args = parser.parse_args()

    executable = shutil.which("pdftotext")
    if executable is None:
        parser.error("pdftotextが見つかりません")
    if not args.pdf.is_file():
        parser.error(f"PDFが見つかりません: {args.pdf}")

    sessions = json.loads(args.sessions.read_text(encoding="utf-8"))
    talks = flattened_talks(sessions)
    if len(talks) != 5636:
        raise ValueError(f"講演数が想定外です: {len(talks)}")
    selected = stratified_sample(talks)
    if len(selected) != 120:
        raise ValueError(f"標本数が想定外です: {len(selected)}")

    extracted: list[dict[str, object]] = []
    for position, talk in enumerate(selected, start=1):
        estimated_page = int(talk["page"])
        page, text = locate_summary(
            executable, args.pdf, str(talk["code"]), estimated_page
        )
        keywords, summary = parse_summary(text, str(talk["code"]), page)
        extracted.append(
            {
                **talk,
                "estimated_page": estimated_page,
                "page": page,
                "page_drift": page - estimated_page,
                "keywords": keywords,
                "summary": summary,
            }
        )
        if position % 10 == 0 or position == len(selected):
            print(f"抽出中: {position}/{len(selected)}", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "status": "local_copyrighted_source",
                "sample_method": "15 evenly spaced presentations per official division",
                "presentations": extracted,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"抽出完了: {len(extracted)}講演 -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
