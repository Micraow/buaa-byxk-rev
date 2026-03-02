from dataclasses import dataclass
from typing import Any


class SessionExpiredError(RuntimeError):
    pass


@dataclass(frozen=True)
class Course:
    course_id: str
    course_code: str
    sequence: str
    name: str
    category: str
    language: str
    schedule_room: str
    can_select: bool
    is_full: bool
    is_selected: bool
    selected_count: int
    capacity: int
    secret_val: str
    raw: dict[str, Any]
    internal_capacity: int = 0
    internal_selected: int = 0
    external_capacity: int = 0
    external_selected: int = 0


def normalize_course(raw: dict[str, Any]) -> Course:
    language = str(raw.get("teachingLanguageName") or raw.get("SKYZMC") or "")
    schedule_room = str(raw.get("teachingPlace") or raw.get("YPSJDD") or "")
    can_select = str(raw.get("SFKT", "0")) == "1"
    is_full = str(raw.get("SFYM", "0")) == "1"
    is_selected = str(raw.get("SFYX", "0")) == "1"

    return Course(
        course_id=str(raw.get("JXBID", "")),
        course_code=str(raw.get("KCH", "")),
        sequence=str(raw.get("KXH", "")),
        name=str(raw.get("KCM", "")),
        category=str(raw.get("KCLB", "")),
        language=language,
        schedule_room=schedule_room,
        can_select=can_select,
        is_full=is_full,
        is_selected=is_selected,
        selected_count=int(raw.get("YXRS", 0) or 0),
        capacity=int(raw.get("KRL", 0) or 0),
        secret_val=str(raw.get("secretVal", "")),
        raw=raw,
        internal_capacity=int(raw.get("internalCapacity", 0) or 0),
        internal_selected=int(raw.get("internalSelectedNum", 0) or 0),
        external_capacity=int(raw.get("externalCapacity", 0) or 0),
        external_selected=int(raw.get("externalSelectedNum", 0) or 0),
    )


class CourseClient:
    def __init__(self, base_url: str, http_client: Any) -> None:
        self.base_url = base_url.rstrip("/")
        self.http_client = http_client

    def _list_general_electives_page(
        self,
        *,
        page_number: int = 1,
        page_size: int = 10,
        campus: str = "1",
        sfct: str = "0",
        teaching_class_type: str = "XGKC",
    ) -> tuple[list[Course], int]:
        payload = {
            "teachingClassType": teaching_class_type,
            "pageNumber": page_number,
            "pageSize": page_size,
            "orderBy": "",
            "campus": campus,
            "SFCT": sfct,
        }
        resp = self.http_client.post(
            f"{self.base_url}/elective/buaa/clazz/list",
            json=payload,
        )
        resp.raise_for_status()
        try:
            body = resp.json()
        except Exception as exc:
            raise SessionExpiredError("clazz/list 未返回 JSON，可能登录态已失效") from exc
        data = body.get("data", {}) if isinstance(body, dict) else {}
        rows = data.get("rows", []) if isinstance(data, dict) else []
        total = int(data.get("total", len(rows)) or len(rows)) if isinstance(data, dict) else len(rows)
        return [normalize_course(r) for r in rows], total

    def list_general_electives(
        self,
        *,
        page_number: int = 1,
        page_size: int = 10,
        campus: str = "1",
        sfct: str = "0",
        teaching_class_type: str = "XGKC",
    ) -> list[Course]:
        rows, _ = self._list_general_electives_page(
            page_number=page_number,
            page_size=page_size,
            campus=campus,
            sfct=sfct,
            teaching_class_type=teaching_class_type,
        )
        return rows

    def list_general_electives_all_pages(
        self,
        *,
        page_size: int = 10,
        campus: str = "1",
        sfct: str = "0",
        teaching_class_type: str = "XGKC",
        max_pages: int = 200,
    ) -> list[Course]:
        all_rows: list[Course] = []
        total_expected = 0

        for page in range(1, max_pages + 1):
            page_rows, total = self._list_general_electives_page(
                page_number=page,
                page_size=page_size,
                campus=campus,
                sfct=sfct,
                teaching_class_type=teaching_class_type,
            )
            total_expected = total
            all_rows.extend(page_rows)

            if not page_rows:
                break
            if total_expected and len(all_rows) >= total_expected:
                break

        dedup: dict[str, Course] = {}
        ordered: list[Course] = []
        for course in all_rows:
            if course.course_id and course.course_id in dedup:
                continue
            if course.course_id:
                dedup[course.course_id] = course
            ordered.append(course)
        return ordered

    def get_my_selected_courses(self) -> set[str]:
        payload: dict[str, Any] = {}
        resp = self.http_client.post(f"{self.base_url}/elective/select", json=payload)
        resp.raise_for_status()
        try:
            body = resp.json()
        except Exception as exc:
            raise SessionExpiredError("elective/select 未返回 JSON，可能登录态已失效") from exc
        rows = body.get("data", []) if isinstance(body, dict) else []
        ids: set[str] = set()
        for row in rows:
            if isinstance(row, dict):
                ids.add(str(row.get("JXBID", "")))
        return {i for i in ids if i}

    def enroll(
        self,
        *,
        clazz_type: str,
        clazz_id: str,
        secret_val: str,
        batch_id: str,
    ) -> dict[str, Any]:
        payload = {
            "clazzType": clazz_type,
            "clazzId": clazz_id,
            "secretVal": secret_val,
            "batchId": batch_id,
            "introduction": "",
            "needBook": "",
        }
        resp = self.http_client.post(f"{self.base_url}/elective/clazz/add", json=payload)
        resp.raise_for_status()
        try:
            body = resp.json()
        except Exception as exc:
            raise SessionExpiredError("elective/clazz/add 未返回 JSON，可能登录态已失效") from exc
        return body if isinstance(body, dict) else {"code": -1, "msg": "invalid response"}
