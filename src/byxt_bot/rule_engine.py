from collections.abc import Iterable
from typing import Any


TARGET_CATEGORIES = {"通识选修课", "综合素养课"}
TARGET_LANGUAGE_PREFIX = "全英语"
TARGET_ROOM_KEYWORDS = ("智慧树[主讲]", "网络授课无教室")


def is_target_course(course: dict[str, Any]) -> bool:
    category = str(course.get("category", ""))
    language = str(course.get("language", ""))
    schedule_room = str(course.get("schedule_room", ""))

    return (
        category in TARGET_CATEGORIES
        and language.startswith(TARGET_LANGUAGE_PREFIX)
        and any(k in schedule_room for k in TARGET_ROOM_KEYWORDS)
    )


def extract_targets(courses: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [course for course in courses if is_target_course(course)]
