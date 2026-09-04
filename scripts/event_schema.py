"""イベント共通JSONの最小スキーマ検証。"""

from __future__ import annotations

import re
from collections.abc import Iterable


TIME_RE = re.compile(r"^(?:[01]?\d|2[0-3]):[0-5]\d$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def presentation_code(talk: object) -> str:
    if isinstance(talk, list):
        return str(talk[1]) if len(talk) > 1 else ""
    if isinstance(talk, dict):
        return str(talk.get("code") or talk.get("id") or "")
    return ""


def validate_sessions(
    sessions: list[dict[str, object]],
    *,
    event_dates: set[str],
    expected_session_count: int | None = None,
    expected_presentation_count: int | None = None,
) -> None:
    if expected_session_count is not None and len(sessions) != expected_session_count:
        raise ValueError(
            f"セッション数が想定と異なります: {len(sessions)} != {expected_session_count}"
        )

    session_ids: list[str] = []
    codes: list[str] = []
    dates: set[str] = set()
    for index, session in enumerate(sessions, start=1):
        session_id = str(session.get("id") or "")
        date = str(session.get("date") or "")
        start = str(session.get("start") or "")
        end = str(session.get("end") or "")
        title = str(session.get("title") or "")
        talks = session.get("talks")
        if not session_id or not title or not isinstance(talks, list) or not talks:
            raise ValueError(f"セッション必須項目が不足しています: #{index}")
        if not DATE_RE.fullmatch(date) or date not in event_dates:
            raise ValueError(f"対象外または不正な日付です: {session_id}: {date!r}")
        if not TIME_RE.fullmatch(start) or not TIME_RE.fullmatch(end):
            raise ValueError(f"セッション時刻が不正です: {session_id}: {start!r}-{end!r}")
        if _minutes(start) >= _minutes(end):
            raise ValueError(f"セッションの終了が開始以前です: {session_id}")
        session_ids.append(session_id)
        dates.add(date)
        for talk in talks:
            code = presentation_code(talk)
            if not code:
                raise ValueError(f"講演番号がありません: {session_id}")
            if isinstance(talk, dict):
                talk_start = str(talk.get("start") or "")
                talk_end = str(talk.get("end") or "")
                if bool(talk_start) != bool(talk_end):
                    raise ValueError(f"講演の開始・終了時刻が片方だけです: {code}")
                if talk_start and (
                    not TIME_RE.fullmatch(talk_start)
                    or not TIME_RE.fullmatch(talk_end)
                    or _minutes(talk_start) >= _minutes(talk_end)
                ):
                    raise ValueError(f"講演時刻が不正です: {code}")
            codes.append(code)

    _validate_unique("セッションID", session_ids)
    _validate_unique("講演番号", codes)
    if dates != event_dates:
        raise ValueError(f"対象日の集合が想定と異なります: {sorted(dates)}")
    if expected_presentation_count is not None and len(codes) != expected_presentation_count:
        raise ValueError(
            f"講演数が想定と異なります: {len(codes)} != {expected_presentation_count}"
        )


def _minutes(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def _validate_unique(label: str, values: Iterable[str]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        raise ValueError(f"{label}が重複しています: {sorted(duplicates)[:10]}")
