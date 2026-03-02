ALLOWED_ENDPOINTS = {"login", "list_courses", "course_detail", "enroll", "my_selected_courses"}
DENIED_ENDPOINT_KEYWORDS = ("drop", "withdraw", "cancel", "delete", "退选", "deselect")
DENIED_ENDPOINTS = {"/elective/clazz/del", "/elective/deselect"}


def ensure_endpoint_allowed(endpoint_name: str) -> None:
    lowered = endpoint_name.lower()
    if any(keyword in lowered for keyword in DENIED_ENDPOINT_KEYWORDS):
        raise RuntimeError(f"Denied endpoint: {endpoint_name}")
    if endpoint_name in DENIED_ENDPOINTS:
        raise RuntimeError(f"Denied endpoint: {endpoint_name}")
    if endpoint_name not in ALLOWED_ENDPOINTS:
        raise RuntimeError(f"Endpoint is not in whitelist: {endpoint_name}")


def ensure_course_not_already_selected(target: str, selected_set: set[str]) -> None:
    if target in selected_set:
        raise RuntimeError(f"Target course already selected: {target}")


def ensure_no_course_lost(before_set: set[str], after_set: set[str]) -> None:
    if not before_set.issubset(after_set):
        lost = before_set - after_set
        raise RuntimeError(f"Selected courses lost after action: {sorted(lost)}")
