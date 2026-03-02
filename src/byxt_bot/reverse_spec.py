from typing import Any


try:
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover
    BaseModel = object  # type: ignore[assignment]
    Field = None  # type: ignore[assignment]


class EndpointSpec(BaseModel):
    method: str
    path: str
    required_headers: list[str] = []
    required_params: list[str] = []
    signature_rule: dict[str, Any] | None = None


class ReverseSpec(BaseModel):
    login: EndpointSpec
    list_courses: EndpointSpec
    course_detail: EndpointSpec | None = None
    enroll: EndpointSpec | None = None
    my_selected_courses: EndpointSpec | None = None
