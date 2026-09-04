"""日本機械学会2026年度年次大会PDFのプログラム欄を静的JSONへ変換する。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from scripts.event_schema import validate_sessions


PROGRAM_FIRST_PAGE = 1
PROGRAM_LAST_PAGE = 117
EXPECTED_SESSION_COUNT = 250
EXPECTED_PRESENTATION_COUNT = 1096
EXPECTED_ORGANIZED_SESSION_COUNT = 61
TARGET_DATES = {
    "2026-09-06",
    "2026-09-07",
    "2026-09-08",
    "2026-09-09",
}

DATE_RE = re.compile(r"^2026年9月([6-9])日\([日月火水]\)$")
GROUPS = {
    "解析･設計･機械要素": "解析・設計・機械要素",
    "解析・設計・機械要素": "解析・設計・機械要素",
    "バイオ･生体･医工学": "バイオ・生体・医工学",
    "バイオ・生体・医工学": "バイオ・生体・医工学",
    "環境･エネルギー": "環境・エネルギー",
    "環境・エネルギー": "環境・エネルギー",
    "情報･知能･機械システム": "情報・知能・機械システム",
    "情報・知能・機械システム": "情報・知能・機械システム",
    "材料･加工･生産技術": "材料・加工・生産技術",
    "材料・加工・生産技術": "材料・加工・生産技術",
    "技術･社会･教育": "技術・社会・教育",
    "技術・社会・教育": "技術・社会・教育",
    "その他": "その他",
}
GROUP_HEADER_RE = re.compile(
    rf"^({'|'.join(re.escape(group) for group in GROUPS)})\s*\|\s*(.+)$"
)
SESSION_TIME_RE = re.compile(
    r"^(\d{1,2}:\d{2})\s*~\s*(\d{1,2}:\d{2})\s*\|\s*(.+)$"
)
TALK_TIME_RE = re.compile(r"^(\d{1,2}:\d{2})\s*~\s*(\d{1,2}:\d{2})$")
SESSION_CODE_RE = re.compile(r"^\[([^\]\s]+)\]\s*(.*)$")
TALK_CODE_RE = re.compile(r"^\[([^\]\s]+-[^\]\s]+)\]\s*(.*)$")
SPEAKER_LINE_RE = re.compile(r"^.+?[（(].+[）)]$")
SPEAKER_LIST_RE = re.compile(r"[）)][、，,]")
FOOTER_LINES = {
    "プログラム",
    "日本機械学会 2026年度年次大会",
    "©一般社団法人日本機械学会",
}


@dataclass(frozen=True)
class ProgramBlock:
    date: str
    group: str
    heading: str
    lines: list[str]


def compact_line(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").strip().split())


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


def extract_program_lines(pdf_path: Path) -> list[str]:
    document = pymupdf.open(pdf_path)
    if document.page_count < PROGRAM_LAST_PAGE:
        raise ValueError(
            f"PDFのページ数が不足しています: {document.page_count} < {PROGRAM_LAST_PAGE}"
        )
    first_detail_page = document[PROGRAM_LAST_PAGE].get_text().splitlines()
    if "プログラム" in {compact_line(line) for line in first_detail_page}:
        raise ValueError(
            f"プログラム欄が{PROGRAM_LAST_PAGE}ページを超えています"
        )

    lines: list[str] = []
    for page_index in range(PROGRAM_FIRST_PAGE - 1, PROGRAM_LAST_PAGE):
        page_lines = document[page_index].get_text().splitlines()
        if "プログラム" not in {compact_line(line) for line in page_lines}:
            raise ValueError(f"プログラム欄ではないページです: {page_index + 1}")
        for raw_line in page_lines:
            line = compact_line(raw_line)
            if line and line not in FOOTER_LINES:
                lines.append(line)
    return lines


def split_program_blocks(lines: list[str]) -> list[ProgramBlock]:
    blocks: list[ProgramBlock] = []
    current_date = ""
    current_group = ""
    current_heading = ""
    current_lines: list[str] = []
    pending_group = ""
    pending_heading = ""
    pending_lines: list[str] = []

    def flush() -> None:
        nonlocal current_group, current_heading, current_lines
        if current_lines:
            if not current_date:
                raise ValueError(f"日付より前に企画が現れました: {current_heading}")
            blocks.append(
                ProgramBlock(current_date, current_group, current_heading, current_lines)
            )
        current_group = ""
        current_heading = ""
        current_lines = []

    for line in lines:
        date_match = DATE_RE.fullmatch(line)
        if date_match:
            flush()
            pending_group = ""
            pending_heading = ""
            pending_lines = []
            current_date = f"2026-09-0{date_match.group(1)}"
            continue
        header_match = GROUP_HEADER_RE.fullmatch(line)
        if header_match:
            flush()
            pending_group = GROUPS[header_match.group(1)]
            pending_heading = header_match.group(2)
            pending_lines = []
            continue
        if SESSION_TIME_RE.fullmatch(line):
            flush()
            if not current_date:
                raise ValueError(f"日付より前に企画時刻が現れました: {line}")
            current_group = pending_group or "その他"
            current_heading = pending_heading
            current_lines = [*pending_lines, line]
            pending_group = ""
            pending_heading = ""
            pending_lines = []
            continue
        if current_lines:
            current_lines.append(line)
        elif pending_heading:
            pending_lines.append(line)
    flush()
    return blocks


def parse_venue(value: str) -> tuple[str, str, str]:
    match = re.fullmatch(r"(.+?)\(([^()]*)\)", compact_line(value))
    if match is None:
        raise ValueError(f"会場を分割できません: {value!r}")
    room, location = match.groups()
    building_match = re.match(r"(.+?号館)", location)
    building = building_match.group(1) if building_match else location
    detail = location[len(building) :]
    display_room = f"{room}（{detail}）" if detail else room
    return building, display_room, compact_line(value)


def parse_kind_and_subject(heading: str, continuation: list[str]) -> tuple[str, str, bool]:
    recommended = any(line == "学生におすすめ" for line in continuation)
    if not heading:
        return "関係者向け", "", recommended
    full_heading = join_wrapped(
        [heading, *(line for line in continuation if line != "学生におすすめ")]
    )
    kind, separator, subject = full_heading.partition("：")
    if not separator:
        return full_heading, "", recommended
    if kind in {"部門単独セッション", "部門横断セッション"}:
        return kind, re.sub(r"^[A-Z][A-Za-z0-9]*\s+", "", subject), recommended
    return full_heading, "", recommended


def split_title_and_topics(lines: list[str]) -> tuple[str, list[str]]:
    title = join_wrapped(lines)
    topics: list[str] = []
    while True:
        match = re.search(r"\s*\[([^\[\]]+)\]\s*$", title)
        if match is None:
            break
        topics[:0] = [compact_line(item) for item in match.group(1).split(",") if item.strip()]
        title = title[: match.start()].rstrip()
    return title, topics


def presenter_from(authors: str) -> str:
    marker_match = re.search(r"〇\s*([^\d、,（(]+)", authors)
    if marker_match:
        return compact_line(marker_match.group(1))
    speaker = re.split(r"[（(]", authors, maxsplit=1)[0]
    return compact_line(re.split(r"[、，,]", speaker, maxsplit=1)[0])


def looks_like_speaker_line(value: str) -> bool:
    return "〇" in value or bool(SPEAKER_LINE_RE.fullmatch(value))


def parse_talks(lines: list[str]) -> list[dict[str, object]]:
    child_indexes = [
        index for index, line in enumerate(lines) if TALK_CODE_RE.fullmatch(line)
    ]
    talks: list[dict[str, object]] = []
    for position, child_index in enumerate(child_indexes):
        next_index = child_indexes[position + 1] if position + 1 < len(child_indexes) else len(lines)
        code_match = TALK_CODE_RE.fullmatch(lines[child_index])
        assert code_match is not None
        code, first_title_line = code_match.groups()

        time_match = TALK_TIME_RE.fullmatch(lines[child_index - 1]) if child_index else None
        content = [first_title_line]
        content.extend(
            line
            for line in lines[child_index + 1 : next_index]
            if not TALK_TIME_RE.fullmatch(line)
            and not line.startswith(("座長:", "座長：", "対象："))
        )
        author_index = next(
            (
                index
                for index, line in enumerate(content[1:], start=1)
                if "〇" in line
            ),
            None,
        )
        if author_index is None:
            author_index = next(
                (
                    index
                    for index, line in enumerate(content[1:], start=1)
                    if SPEAKER_LIST_RE.search(line)
                ),
                None,
            )
        if author_index is None:
            speaker_indexes = [
                index
                for index, line in enumerate(content[1:], start=1)
                if looks_like_speaker_line(line)
            ]
            author_index = speaker_indexes[-1] if speaker_indexes else None
        title_lines = content if author_index is None else content[:author_index]
        author_lines = [] if author_index is None else content[author_index:]
        title = join_wrapped(title_lines)
        authors = join_wrapped(author_lines)
        if not title:
            raise ValueError(f"講演題名を抽出できません: {code}")
        status = "missing" if title == "欠番" else "scheduled"
        presenter = "" if status == "missing" else presenter_from(authors)
        talks.append(
            {
                "start": time_match.group(1) if time_match else "",
                "end": time_match.group(2) if time_match else "",
                "code": code,
                "title": title,
                "presenter": presenter,
                "authors": authors,
                "contributors": {
                    "names": authors,
                    "presenter": presenter,
                    "presenterAffiliations": [],
                    "coauthorAffiliations": [],
                    "hasCoauthors": False,
                },
                "status": status,
            }
        )
    return talks


def parse_block(block: ProgramBlock, index: int) -> dict[str, object]:
    session_time_index = next(
        (
            line_index
            for line_index, line in enumerate(block.lines)
            if SESSION_TIME_RE.fullmatch(line)
        ),
        None,
    )
    if session_time_index is None:
        raise ValueError(f"企画時刻が見つかりません: {block.heading}")
    time_match = SESSION_TIME_RE.fullmatch(block.lines[session_time_index])
    assert time_match is not None
    start, end, raw_venue = time_match.groups()
    kind, subject, recommended = parse_kind_and_subject(
        block.heading, block.lines[:session_time_index]
    )
    building, room, venue = parse_venue(raw_venue)
    body = block.lines[session_time_index + 1 :]

    session_code_index = next(
        (line_index for line_index, line in enumerate(body) if SESSION_CODE_RE.fullmatch(line)),
        None,
    )
    if session_code_index is None:
        raise ValueError(f"セッション番号が見つかりません: {block.heading}")
    session_match = SESSION_CODE_RE.fullmatch(body[session_code_index])
    assert session_match is not None
    session_code, first_title_line = session_match.groups()

    title_lines = [first_title_line]
    for line in body[session_code_index + 1 :]:
        if line.startswith(("座長:", "座長：", "対象：")):
            break
        if TALK_TIME_RE.fullmatch(line) or TALK_CODE_RE.fullmatch(line):
            break
        title_lines.append(line)
    title, topics = split_title_and_topics(title_lines)
    if not topics:
        topics = [block.group]
    chair_line = next(
        (line for line in body if line.startswith(("座長:", "座長："))), ""
    )
    chair = re.sub(r"^座長[:：]", "", chair_line).strip()
    target_line = next((line for line in body if line.startswith("対象：")), "")
    target = target_line.removeprefix("対象：").strip()
    talks = parse_talks(body[session_code_index + 1 :])
    if not talks:
        talks = [
            {
                "start": start,
                "end": end,
                "code": session_code,
                "title": title,
                "presenter": "",
                "authors": "",
                "contributors": {
                    "names": "",
                    "presenter": "",
                    "presenterAffiliations": [],
                    "coauthorAffiliations": [],
                    "hasCoauthors": False,
                },
                "status": "session",
            }
        ]

    return {
        "id": f"session-{index:04d}",
        "code": session_code,
        "date": block.date,
        "start": start,
        "end": end,
        "division": kind,
        "group": block.group,
        "title": title,
        "topics": topics,
        "campus": building,
        "room": room,
        "venue": venue,
        "chair": chair,
        "target": target,
        "recommendedForStudents": recommended,
        "talks": talks,
    }


def parse_program(lines: list[str]) -> list[dict[str, object]]:
    blocks = split_program_blocks(lines)
    return [parse_block(block, index) for index, block in enumerate(blocks, start=1)]


def validate_organized_sessions(
    sessions: list[dict[str, object]], session_list_path: Path
) -> None:
    session_list = pymupdf.open(session_list_path)
    listed_codes = set(
        re.findall(
            r"(?m)^([JS]\d{3})\s+",
            "\n".join(page.get_text() for page in session_list),
        )
    )
    scheduled_codes = {
        re.sub(r"p$", "", str(session["code"]))
        for session in sessions
        if re.fullmatch(r"[JS]\d{3}p?", str(session["code"]))
    }
    if len(listed_codes) != EXPECTED_ORGANIZED_SESSION_COUNT:
        raise ValueError(
            "セッション一覧のS・Jセッション数が想定と異なります: "
            f"{len(listed_codes)} != {EXPECTED_ORGANIZED_SESSION_COUNT}"
        )
    if scheduled_codes != listed_codes:
        missing = sorted(listed_codes - scheduled_codes)
        extra = sorted(scheduled_codes - listed_codes)
        raise ValueError(
            f"S・Jセッションの突合に失敗しました: missing={missing}, extra={extra}"
        )


def topic_id(label: str) -> str:
    digest = hashlib.sha1(label.encode("utf-8"), usedforsecurity=False).hexdigest()[:10]
    return f"topic-{digest}"


def category_documents(
    sessions: list[dict[str, object]],
) -> tuple[dict[str, object], dict[str, object]]:
    labels = sorted(
        {
            str(topic)
            for session in sessions
            for topic in session.get("topics", [])  # type: ignore[union-attr]
        }
    )
    ids = {label: topic_id(label) for label in labels}
    taxonomy = {
        "schema_version": 1,
        "axes": [
            {
                "id": "topic",
                "label": "分野",
                "values": [{"id": ids[label], "label": label} for label in labels],
            }
        ],
        "browse_collections": [
            {
                "id": ids[label],
                "label": label,
                "any": [f"topic:{ids[label]}"],
            }
            for label in labels
        ],
    }
    presentations = []
    for session in sessions:
        topic_ids = [ids[str(label)] for label in session["topics"]]  # type: ignore[index]
        for talk in session["talks"]:  # type: ignore[index]
            presentations.append(
                {"code": talk["code"], "labels": {"topic": topic_ids}}
            )
    categories = {"schema_version": 1, "presentations": presentations}
    return taxonomy, categories


def write_json(path: Path, value: object, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("sources/jsme2026/jsme2026_program_all.pdf"),
        help="JSMEプログラムPDF",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("events/jsme2026"),
        help="公開JSONの出力先",
    )
    parser.add_argument(
        "--session-list",
        type=Path,
        default=Path(
            "sources/jsme2026/nenji2026sessions_ja_20260511131150123.pdf"
        ),
        help="S・Jセッションの突合に使うセッション一覧PDF",
    )
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"入力PDFが見つかりません: {args.input}")
    if not args.session_list.is_file():
        parser.error(f"セッション一覧PDFが見つかりません: {args.session_list}")

    sessions = parse_program(extract_program_lines(args.input))
    validate_sessions(
        sessions,
        event_dates=TARGET_DATES,
        expected_session_count=EXPECTED_SESSION_COUNT,
        expected_presentation_count=EXPECTED_PRESENTATION_COUNT,
    )
    validate_organized_sessions(sessions, args.session_list)
    taxonomy, categories = category_documents(sessions)
    write_json(args.output_dir / "sessions.json", sessions)
    write_json(args.output_dir / "category_taxonomy.json", taxonomy, pretty=True)
    write_json(args.output_dir / "categories.json", categories)
    print(
        f"出力完了: {len(sessions)}セッション / "
        f"{sum(len(session['talks']) for session in sessions)}講演枠 / "
        f"S・Jセッション{EXPECTED_ORGANIZED_SESSION_COUNT}件突合済み -> "
        f"{args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
