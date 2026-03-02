import time
from dataclasses import dataclass
from typing import Iterable

from byxt_bot.course_client import Course, CourseClient
from byxt_bot.rule_engine import is_target_course


@dataclass(frozen=True)
class MonitorSnapshot:
    scanned_total: int
    english_target_total: int
    pool_full_total: int
    available_total: int
    targets: list[Course]
    available: list[Course]


@dataclass
class MonitorService:
    course_client: CourseClient
    poll_interval_seconds: float = 3.0
    teaching_class_type: str = "XGKC"
    page_size: int = 10

    def list_targets(self) -> list[Course]:
        courses = self.course_client.list_general_electives_all_pages(
            teaching_class_type=self.teaching_class_type,
            page_size=self.page_size,
        )
        return [c for c in courses if is_target_course(_to_rule_dict(c))]

    def watch_once_with_snapshot(self) -> MonitorSnapshot:
        courses = self.course_client.list_general_electives_all_pages(
            teaching_class_type=self.teaching_class_type,
            page_size=self.page_size,
        )
        targets = [c for c in courses if is_target_course(_to_rule_dict(c))]
        pool_full = [c for c in targets if _is_pool_fully_occupied(c)]
        available = [
            c
            for c in targets
            if c.can_select and not c.is_selected and not _is_pool_fully_occupied(c)
        ]
        return MonitorSnapshot(
            scanned_total=len(courses),
            english_target_total=len(targets),
            pool_full_total=len(pool_full),
            available_total=len(available),
            targets=targets,
            available=available,
        )

    def watch_once(self) -> list[Course]:
        return self.watch_once_with_snapshot().available

    def run_polling_loop(self, *, max_rounds: int = 0) -> Iterable[MonitorSnapshot]:
        rounds = 0
        while True:
            yield self.watch_once_with_snapshot()
            rounds += 1
            if max_rounds and rounds >= max_rounds:
                break
            time.sleep(self.poll_interval_seconds)


def _to_rule_dict(c: Course) -> dict[str, str]:
    return {
        "category": c.category,
        "language": c.language,
        "schedule_room": c.schedule_room,
    }


def _is_pool_fully_occupied(c: Course) -> bool:
    pools: list[tuple[int, int]] = [
        (c.internal_capacity, c.internal_selected),
        (c.external_capacity, c.external_selected),
    ]
    enabled_pools = [(cap, sel) for cap, sel in pools if cap > 0]
    if not enabled_pools:
        return c.selected_count >= c.capacity if c.capacity > 0 else False
    return all(sel >= cap for cap, sel in enabled_pools)
