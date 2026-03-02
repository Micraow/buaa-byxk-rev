from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable

from byxt_bot.course_client import Course, CourseClient
from byxt_bot.course_csv import TargetCourseSpec, TargetCourseState, evaluate_target_courses


@dataclass(frozen=True)
class TargetMonitorSnapshot:
    scanned_total: int
    target_total: int
    found_total: int
    pool_full_total: int
    available_total: int
    states: list[TargetCourseState]
    available: list[TargetCourseState]


@dataclass
class TargetMonitorService:
    course_client: CourseClient
    target_specs: list[TargetCourseSpec]
    poll_interval_seconds: float = 3.0
    teaching_class_types: tuple[str, ...] = ("XGKC", "TJKC")
    page_size: int = 10
    max_pages: int = 200

    def watch_once_with_snapshot(self) -> TargetMonitorSnapshot:
        courses = self._list_courses_from_all_types()
        states = evaluate_target_courses(courses, self.target_specs)
        available = [s for s in states if s.selectable]
        return TargetMonitorSnapshot(
            scanned_total=len(courses),
            target_total=len(self.target_specs),
            found_total=sum(1 for s in states if s.found),
            pool_full_total=sum(1 for s in states if s.found and s.pool_full),
            available_total=len(available),
            states=states,
            available=available,
        )

    def run_polling_loop(self, *, max_rounds: int = 0) -> Iterable[TargetMonitorSnapshot]:
        rounds = 0
        while True:
            yield self.watch_once_with_snapshot()
            rounds += 1
            if max_rounds and rounds >= max_rounds:
                break
            time.sleep(self.poll_interval_seconds)

    def _list_courses_from_all_types(self) -> list[Course]:
        all_rows = []
        for teaching_class_type in self.teaching_class_types:
            rows = self.course_client.list_general_electives_all_pages(
                teaching_class_type=teaching_class_type,
                page_size=self.page_size,
                max_pages=self.max_pages,
            )
            all_rows.extend(rows)

        dedup: dict[tuple[str, str], Course] = {}
        ordered = []
        for c in all_rows:
            key = (c.course_code.strip().upper(), c.sequence.strip())
            if key in dedup:
                continue
            dedup[key] = c
            ordered.append(c)
        return ordered
