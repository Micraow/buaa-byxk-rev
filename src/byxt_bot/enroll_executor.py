from dataclasses import dataclass
from typing import Any

from byxt_bot.course_client import Course, CourseClient
from byxt_bot.safety_guard import (
    ensure_course_not_already_selected,
    ensure_endpoint_allowed,
    ensure_no_course_lost,
)


@dataclass
class EnrollExecutor:
    course_client: CourseClient
    batch_id: str
    execution_mode: str = "DRY_RUN"

    def try_enroll(self, course: Course) -> dict[str, Any]:
        ensure_endpoint_allowed("enroll")
        ensure_endpoint_allowed("list_courses")

        before_set = self.course_client.get_my_selected_courses()
        ensure_course_not_already_selected(course.course_id, before_set)

        if self.execution_mode != "ARMED":
            return {
                "code": 0,
                "msg": "dry run",
                "course_id": course.course_id,
                "course_name": course.name,
            }

        clazz_type = str(course.raw.get("teachingClassType") or "XGKC")
        result = self.course_client.enroll(
            clazz_type=clazz_type,
            clazz_id=course.course_id,
            secret_val=course.secret_val,
            batch_id=self.batch_id,
        )

        after_set = self.course_client.get_my_selected_courses()
        ensure_no_course_lost(before_set, after_set)

        return result
