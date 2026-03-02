from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from byxt_bot.course_client import Course


@dataclass(frozen=True)
class TargetCourseSpec:
    course_code: str
    sequence: str
    target_pool: str  # internal | external


@dataclass(frozen=True)
class TargetCourseState:
    spec: TargetCourseSpec
    course: Course | None
    found: bool
    pool_full: bool
    selectable: bool


_BASE_EXPORT_COLUMNS = [
    "course_id",
    "course_code",
    "sequence",
    "name",
    "category",
    "language",
    "schedule_room",
    "can_select",
    "is_full",
    "is_selected",
    "selected_count",
    "capacity",
    "internal_capacity",
    "internal_selected",
    "external_capacity",
    "external_selected",
    "target_pool",
]


def export_courses_csv(courses: list[Course], file_path: str) -> None:
    raw_keys: set[str] = set()
    for c in courses:
        raw_keys.update((c.raw or {}).keys())

    raw_columns = sorted(k for k in raw_keys if k not in _BASE_EXPORT_COLUMNS)
    columns = _BASE_EXPORT_COLUMNS + raw_columns

    out_path = Path(file_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for c in courses:
            row = {
                "course_id": c.course_id,
                "course_code": c.course_code,
                "sequence": c.sequence,
                "name": c.name,
                "category": c.category,
                "language": c.language,
                "schedule_room": c.schedule_room,
                "can_select": c.can_select,
                "is_full": c.is_full,
                "is_selected": c.is_selected,
                "selected_count": c.selected_count,
                "capacity": c.capacity,
                "internal_capacity": c.internal_capacity,
                "internal_selected": c.internal_selected,
                "external_capacity": c.external_capacity,
                "external_selected": c.external_selected,
                "target_pool": "",
            }

            raw = c.raw or {}
            for key in raw_columns:
                value = raw.get(key, "")
                if isinstance(value, (dict, list)):
                    row[key] = json.dumps(value, ensure_ascii=False)
                else:
                    row[key] = value

            writer.writerow(row)


def parse_target_courses_csv(file_path: str) -> list[TargetCourseSpec]:
    in_path = Path(file_path)
    if not in_path.exists():
        return []

    specs: list[TargetCourseSpec] = []
    seen: set[tuple[str, str, str]] = set()

    with in_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_index, row in enumerate(reader, start=2):
            pool_raw = str(row.get("target_pool", "")).strip()
            if not pool_raw:
                continue

            course_code = str(row.get("course_code") or row.get("KCH") or "").strip()
            sequence = str(row.get("sequence") or row.get("KXH") or "").strip()
            if not course_code or not sequence:
                raise ValueError(f"targets csv 第 {row_index} 行缺少 course_code/sequence")

            pool = _normalize_pool(pool_raw)
            key = (_normalize_text(course_code), _normalize_sequence(sequence), pool)
            if key in seen:
                continue
            seen.add(key)

            specs.append(TargetCourseSpec(course_code=course_code, sequence=sequence, target_pool=pool))

    return specs


def evaluate_target_courses(courses: list[Course], specs: list[TargetCourseSpec]) -> list[TargetCourseState]:
    index: dict[tuple[str, str], Course] = {}
    for c in courses:
        key = (_normalize_text(c.course_code), _normalize_sequence(c.sequence))
        index[key] = c

    states: list[TargetCourseState] = []
    for spec in specs:
        key = (_normalize_text(spec.course_code), _normalize_sequence(spec.sequence))
        course = index.get(key)

        if course is None:
            states.append(
                TargetCourseState(spec=spec, course=None, found=False, pool_full=True, selectable=False)
            )
            continue

        pool_full = _is_target_pool_full(course, spec.target_pool)
        selectable = course.can_select and (not course.is_selected) and (not pool_full)
        states.append(
            TargetCourseState(
                spec=spec,
                course=course,
                found=True,
                pool_full=pool_full,
                selectable=selectable,
            )
        )

    return states


def _normalize_pool(value: str) -> str:
    lowered = value.strip().lower()
    mapping = {
        "对内": "internal",
        "内": "internal",
        "internal": "internal",
        "in": "internal",
        "dn": "internal",
        "对外": "external",
        "外": "external",
        "external": "external",
        "out": "external",
        "dw": "external",
    }
    pool = mapping.get(lowered)
    if pool:
        return pool

    if value.strip() in {"对内", "内"}:
        return "internal"
    if value.strip() in {"对外", "外"}:
        return "external"

    raise ValueError(f"不支持的 target_pool 值: {value}")


def _normalize_text(value: str) -> str:
    return value.strip().upper()


def _normalize_sequence(value: str) -> str:
    s = value.strip()
    if s.isdigit():
        return str(int(s))
    return s


def _is_target_pool_full(course: Course, target_pool: str) -> bool:
    if target_pool == "internal":
        if course.internal_capacity <= 0:
            return True
        return course.internal_selected >= course.internal_capacity

    if target_pool == "external":
        if course.external_capacity <= 0:
            return True
        return course.external_selected >= course.external_capacity

    raise ValueError(f"不支持的池类型: {target_pool}")
