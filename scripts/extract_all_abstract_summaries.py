"""全PDFを1回だけ走査し、全講演の著者キーワードと短い内容要約を抽出する。"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import threading
from collections import deque
from pathlib import Path

from extract_category_sample import (
    ABSTRACT_START_PAGE,
    CODE_RE,
    KEYWORDS_RE,
    ROOT,
    compact,
    extract_range,
    parse_summary,
)


PDF_LAST_PAGE = 18391
EXPECTED_PRESENTATIONS = 5636


def presentation_index(sessions: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    session_page = ABSTRACT_START_PAGE
    for session in sessions:
        talks = session["talks"]
        assert isinstance(talks, list)
        for index, talk in enumerate(talks):
            code = str(talk[1])
            if code in result:
                raise ValueError(f"講演番号が重複しています: {code}")
            result[code] = {
                "code": code,
                "title": talk[2],
                "division": session["division"],
                "session": session["title"],
                "estimated_page": session_page + 1 + 3 * index,
            }
        session_page += 1 + 3 * len(talks)
    return result


def drain_stderr(stream: object, tail: deque[str], count: list[int]) -> None:
    for raw_line in stream:  # type: ignore[union-attr]
        count[0] += 1
        tail.append(raw_line.decode("utf-8", errors="replace").strip())


def fallback_from_fullpaper(
    executable: str,
    pdf_path: Path,
    metadata: dict[str, object],
) -> dict[str, object]:
    """標準要約がない講演のみ、本文1ページ目を分類根拠として取得する。"""
    code = str(metadata["code"])
    estimated_page = int(metadata["estimated_page"])
    first_page = max(ABSTRACT_START_PAGE, estimated_page - 8)
    last_page = min(PDF_LAST_PAGE, estimated_page + 8)
    text = extract_range(executable, pdf_path, first_page, last_page)
    code_header = re.compile(rf"(?m)^\s*{re.escape(code)}(?:\s|$)")
    candidates = [
        (first_page + offset, page_text)
        for offset, page_text in enumerate(text.split("\f"))
        if code_header.search(page_text)
    ]
    if not candidates:
        raise ValueError(
            f"本文フォールバックでも講演を特定できません: {code} / {estimated_page}ページ周辺"
        )

    page, page_text = candidates[0]
    keyword_match = re.search(r"キーワード(?:\s*[：:]\s*|\s+)([^\r\n]+)", page_text)
    keywords = []
    if keyword_match is not None:
        keywords = [
            compact(item)
            for item in re.split(r"[、，,]", compact(keyword_match.group(1)))
            if compact(item)
        ]
    summary = compact(page_text)
    if len(summary) < 100:
        raise ValueError(f"本文フォールバックのテキストが短すぎます: {code} / {page}ページ")
    return {
        **metadata,
        "page": page,
        "source_quality": "fullpaper_first_page",
        "keywords": keywords,
        "summary": summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pdf",
        type=Path,
        default=ROOT / "sources" / "jsce2026" / "program.pdf",
    )
    parser.add_argument(
        "--sessions",
        type=Path,
        default=ROOT / "events" / "jsce2026" / "sessions.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "events" / "jsce2026" / "category_all_source.local.json",
    )
    args = parser.parse_args()

    executable = shutil.which("pdftotext")
    if executable is None:
        parser.error("pdftotextが見つかりません")
    if not args.pdf.is_file():
        parser.error(f"PDFが見つかりません: {args.pdf}")

    sessions = json.loads(args.sessions.read_text(encoding="utf-8"))
    metadata_by_code = presentation_index(sessions)
    if len(metadata_by_code) != EXPECTED_PRESENTATIONS:
        raise ValueError(f"講演数が想定外です: {len(metadata_by_code)}")

    command = [
        executable,
        "-f",
        str(ABSTRACT_START_PAGE),
        "-l",
        str(PDF_LAST_PAGE),
        "-enc",
        "UTF-8",
        "-layout",
        str(args.pdf),
        "-",
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    assert process.stderr is not None
    error_tail: deque[str] = deque(maxlen=20)
    error_count = [0]
    error_thread = threading.Thread(
        target=drain_stderr,
        args=(process.stderr, error_tail, error_count),
        daemon=True,
    )
    error_thread.start()

    extracted: dict[str, dict[str, object]] = {}
    failures: list[str] = []
    standard_parse_failures: dict[str, str] = {}
    buffer = b""
    page = ABSTRACT_START_PAGE

    def process_page(page_bytes: bytes, page_number: int) -> None:
        text = page_bytes.decode("utf-8", errors="replace")
        if KEYWORDS_RE.search(text) is None:
            return
        page_codes = {
            " ".join(match.group(1).split())
            for match in CODE_RE.finditer(text)
            if " ".join(match.group(1).split()) in metadata_by_code
        }
        if not page_codes:
            return
        if len(page_codes) != 1:
            failures.append(
                f"{page_number}ページで複数の講演番号を検出: {sorted(page_codes)}"
            )
            return
        code = next(iter(page_codes))
        if code in extracted:
            failures.append(
                f"講演番号を複数ページで検出: {code} / {extracted[code]['page']} / {page_number}"
            )
            return
        try:
            keywords, summary = parse_summary(text, code, page_number)
        except ValueError as error:
            standard_parse_failures[code] = str(error)
            return
        extracted[code] = {
            **metadata_by_code[code],
            "page": page_number,
            "source_quality": "abstract_summary",
            "keywords": keywords,
            "summary": summary,
        }
        if len(extracted) % 250 == 0:
            print(
                f"抽出中: {len(extracted)}/{EXPECTED_PRESENTATIONS}講演 "
                f"({page_number}/{PDF_LAST_PAGE}ページ)",
                flush=True,
            )

    while True:
        chunk = process.stdout.read(1024 * 1024)
        if not chunk:
            break
        buffer += chunk
        while b"\x0c" in buffer:
            page_bytes, buffer = buffer.split(b"\x0c", 1)
            process_page(page_bytes, page)
            page += 1
    if buffer:
        process_page(buffer, page)
        page += 1

    return_code = process.wait()
    error_thread.join(timeout=5)
    if return_code != 0:
        raise RuntimeError(
            f"pdftotextが終了コード{return_code}で失敗しました: {list(error_tail)}"
        )

    missing_before_fallback = sorted(set(metadata_by_code) - set(extracted))
    for code in missing_before_fallback:
        extracted[code] = fallback_from_fullpaper(
            executable, args.pdf, metadata_by_code[code]
        )
        print(
            f"本文1ページ目で補完: {code} / {extracted[code]['page']}ページ",
            flush=True,
        )

    missing = sorted(set(metadata_by_code) - set(extracted))
    extra = sorted(set(extracted) - set(metadata_by_code))
    if failures or missing or extra:
        details = [
            f"抽出失敗: {len(failures)}件",
            f"未抽出: {len(missing)}件 {missing[:20]}",
            f"不明な講演: {len(extra)}件 {extra[:20]}",
            *failures[:20],
        ]
        raise ValueError("\n".join(details))

    ordered = [extracted[code] for code in metadata_by_code]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "status": "local_copyrighted_source",
                "source_pages": [ABSTRACT_START_PAGE, PDF_LAST_PAGE],
                "pdftotext_warning_lines": error_count[0],
                "standard_parse_failures": standard_parse_failures,
                "presentations": ordered,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    print(
        f"抽出完了: {len(ordered)}講演 / PDF {page - ABSTRACT_START_PAGE}ページ / "
        f"本文補完 {len(missing_before_fallback)}講演 / "
        f"pdftotext警告 {error_count[0]}行 -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
