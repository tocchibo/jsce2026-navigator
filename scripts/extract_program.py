"""令和8年度土木学会全国大会のプログラム部を静的JSONへ変換する。"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


PROGRAM_LAST_PAGE = 737
EXPECTED_SESSION_COUNT = 748
EXPECTED_PRESENTATION_COUNT = 5636
TARGET_DATES = {"2026-09-02", "2026-09-03", "2026-09-04"}

DATE_RE = re.compile(r"2026年9月([234])日")
SESSION_HEADER_RE = re.compile(
    r"^\s*(\d{1,2}:\d{2})\s*~\s*(\d{1,2}:\d{2})\s*\|\s*(.+?)\s*$"
)
TALK_TIME_RE = re.compile(r"^\s*(\d{1,2}:\d{2})\s*~\s*(\d{1,2}:\d{2})\s*$")
PRESENTATION_RE = re.compile(r"^\s*\[([^]\r\n]+)\]\s*(.*)$")
DIVISION_RE = re.compile(r"^\s*第([IVX]+)部門\s*$")
GROUP_RE = re.compile(r"^\s*\[([^]]+セッション)\]")
CHAIR_PREFIX = "座長："
PRESENTER_LINE_RE = re.compile(r"(?:^|[、,])\s*\*[^*]+?\d")


def compact_line(value: str) -> str:
    return " ".join(value.strip().split())


def join_wrapped(lines: list[str]) -> str:
    result = ""
    for raw_line in lines:
        line = compact_line(raw_line)
        if not line:
            continue
        if not result:
            result = line
            continue
        needs_space = result[-1].isascii() and line[0].isascii()
        result += (" " if needs_space else "") + line
    return result


def presenter_from(authors: str) -> str:
    if "*" not in authors:
        return ""
    presenter = authors.split("*", 1)[1]
    presenter = re.split(r"[、,（(]", presenter, maxsplit=1)[0]
    return re.sub(r"\d+(?:\s*\d+)*$", "", presenter).strip()


def split_location(value: str) -> tuple[str, str]:
    normalized = compact_line(value)
    room, separator, campus = normalized.rpartition("（")
    if not separator or not campus.endswith("）"):
        raise ValueError(f"会場を分割できません: {value!r}")
    return room.strip(), campus[:-1].strip()


def extract_text(pdf_path: Path) -> str:
    executable = shutil.which("pdftotext")
    if executable is None:
        raise RuntimeError("pdftotext が見つかりません。TeX Live等の導入を確認してください。")

    command = [
        executable,
        "-f",
        "1",
        "-l",
        str(PROGRAM_LAST_PAGE),
        "-enc",
        "UTF-8",
        "-layout",
        str(pdf_path),
        "-",
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"pdftotext が終了コード {completed.returncode} で失敗しました:\n{stderr}")
    return completed.stdout.decode("utf-8")


def parse_talks(lines: list[str]) -> list[list[str]]:
    starts = [index for index, line in enumerate(lines) if TALK_TIME_RE.match(line)]
    talks: list[list[str]] = []

    for position, start_index in enumerate(starts):
        end_index = starts[position + 1] if position + 1 < len(starts) else len(lines)
        block = lines[start_index:end_index]
        time_match = TALK_TIME_RE.match(block[0])
        assert time_match is not None

        code_index = next(
            (index for index, line in enumerate(block[1:], start=1) if PRESENTATION_RE.match(line)),
            None,
        )
        if code_index is None:
            continue

        code_match = PRESENTATION_RE.match(block[code_index])
        assert code_match is not None
        code, first_title_line = code_match.groups()

        content = [first_title_line, *block[code_index + 1 :]]
        author_index = next(
            (
                index
                for index, line in enumerate(content)
                if line.lstrip().startswith("*") or PRESENTER_LINE_RE.search(line)
            ),
            None,
        )
        if author_index is None:
            raise ValueError(f"発表者行が見つかりません: [{code}]")

        title = join_wrapped(content[:author_index])
        author_lines: list[str] = []
        for line in content[author_index:]:
            normalized = compact_line(line)
            if (
                normalized.startswith("© 2026 Japan Society of Civil Engineers")
                or normalized.startswith("プログラム ")
                or normalized == "プログラム"
                or GROUP_RE.match(line)
                or DIVISION_RE.match(line)
                or DATE_RE.search(line)
            ):
                break
            author_lines.append(line)

        authors = join_wrapped(author_lines)
        presenter = presenter_from(authors)
        if not title or not presenter or not authors:
            raise ValueError(f"題名、発表者または著者情報を抽出できません: [{code}]")

        talks.append([time_match.group(1), code.strip(), title, presenter, authors])

    return talks


def parse_program(text: str) -> list[dict[str, object]]:
    lines = text.splitlines()
    header_indexes = [
        index for index, line in enumerate(lines) if SESSION_HEADER_RE.match(line)
    ]

    sessions: list[dict[str, object]] = []
    current_date = ""
    current_division = ""

    for line_index, line in enumerate(lines):
        date_match = DATE_RE.search(line)
        if date_match:
            current_date = f"2026-09-0{date_match.group(1)}"

        division_match = DIVISION_RE.match(line)
        if division_match:
            current_division = f"第{division_match.group(1)}部門"

        group_match = GROUP_RE.match(line)
        if group_match:
            current_division = group_match.group(1)

        header_match = SESSION_HEADER_RE.match(line)
        if header_match is None:
            continue

        if current_date not in TARGET_DATES:
            raise ValueError(f"対象日を特定できません（行 {line_index + 1}）")
        if not current_division:
            raise ValueError(f"部門を特定できません（行 {line_index + 1}）")

        next_header_index = next(
            (index for index in header_indexes if index > line_index), len(lines)
        )
        block = lines[line_index + 1 : next_header_index]
        chair_index = next(
            (index for index, value in enumerate(block) if compact_line(value).startswith(CHAIR_PREFIX)),
            None,
        )
        if chair_index is None:
            raise ValueError(f"座長行が見つかりません（行 {line_index + 1}）")

        title = join_wrapped(block[:chair_index])
        chair = compact_line(block[chair_index]).removeprefix(CHAIR_PREFIX).strip()
        room, campus = split_location(header_match.group(3))
        talks = parse_talks(block[chair_index + 1 :])

        if not title or not chair or not talks:
            raise ValueError(f"セッション情報が不足しています（行 {line_index + 1}）")

        sessions.append(
            {
                "id": f"session-{len(sessions) + 1:04d}",
                "date": current_date,
                "start": header_match.group(1),
                "end": header_match.group(2),
                "division": current_division,
                "title": title,
                "campus": campus,
                "room": room,
                "chair": chair,
                "talks": talks,
            }
        )

    return sessions


def validate(sessions: list[dict[str, object]]) -> None:
    if len(sessions) != EXPECTED_SESSION_COUNT:
        raise ValueError(
            f"セッション数が想定と異なります: {len(sessions)} != {EXPECTED_SESSION_COUNT}"
        )

    talks = [talk for session in sessions for talk in session["talks"]]  # type: ignore[index]
    if len(talks) != EXPECTED_PRESENTATION_COUNT:
        raise ValueError(
            f"講演数が想定と異なります: {len(talks)} != {EXPECTED_PRESENTATION_COUNT}"
        )

    codes = [talk[1] for talk in talks]
    duplicates = sorted({code for code in codes if codes.count(code) > 1})
    if duplicates:
        raise ValueError(f"講演番号が重複しています: {duplicates[:10]}")

    invalid_authors = [
        talk
        for talk in talks
        if len(talk) != 5
        or not talk[4]
        or any(
            marker in talk[4]
            for marker in (
                "© 2026 Japan Society of Civil Engineers",
                "令和8年度土木学会全国大会",
                "[共通セッション]",
            )
        )
    ]
    if invalid_authors:
        raise ValueError(f"著者・所属情報が不正です: {invalid_authors[0][1]}")

    dates = {session["date"] for session in sessions}
    if dates != TARGET_DATES:
        raise ValueError(f"対象日の集合が想定と異なります: {dates}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("2026/jsce2026_program_all.pdf"),
        help="全プログラムPDF",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/sessions.json"),
        help="出力JSON",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"入力PDFが見つかりません: {args.input}")

    text = extract_text(args.input)
    sessions = parse_program(text)
    validate(sessions)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(sessions, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    talk_count = sum(len(session["talks"]) for session in sessions)  # type: ignore[arg-type]
    print(f"出力完了: {len(sessions)}セッション / {talk_count}講演 -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
