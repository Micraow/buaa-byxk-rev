from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from byxt_bot.auth_client import AuthClient
from byxt_bot.course_client import Course, CourseClient, SessionExpiredError
from byxt_bot.course_csv import TargetCourseState, export_courses_csv, parse_target_courses_csv
from byxt_bot.enroll_executor import EnrollExecutor
from byxt_bot.file_config import FileConfig, load_or_create_config
from byxt_bot.http_session import AuthenticatedHttpClient
from byxt_bot.logging_setup import setup_logging
from byxt_bot.session_manager import SessionManager
from byxt_bot.session_relogin import call_with_relogin
from byxt_bot.target_monitor_service import TargetMonitorService


CONFIG_PATH = "output/byxt_config.json"


def _format_course_line(c: Course) -> str:
    return (
        f"{c.course_code}-{c.sequence} {c.name} | "
        f"内 {c.internal_selected}/{c.internal_capacity} | "
        f"外 {c.external_selected}/{c.external_capacity} | "
        f"总 {c.selected_count}/{c.capacity}"
    )


def _format_target_state_line(state: TargetCourseState) -> str:
    course = state.course
    if course is None:
        return f"[{state.spec.target_pool}] {state.spec.course_code}-{state.spec.sequence} NOT_FOUND"
    return f"[{state.spec.target_pool}] {_format_course_line(course)}"


def _should_stop_after_success(*, cfg: FileConfig, result: dict[str, object]) -> bool:
    return cfg.stop_after_success and cfg.execution_mode == "ARMED" and result.get("code") == 200


def _sync_batch_id(executor: EnrollExecutor, relogin_bundle: object) -> None:
    executor.batch_id = _extract_batch_id(relogin_bundle, executor.batch_id)


def _extract_batch_id(bundle: object, fallback: str) -> str:
    attr_batch_id = getattr(bundle, "batch_id", None)
    if isinstance(attr_batch_id, str) and attr_batch_id:
        return attr_batch_id

    if isinstance(bundle, dict):
        dict_batch_id = bundle.get("batch_id")
        if isinstance(dict_batch_id, str) and dict_batch_id:
            return dict_batch_id

    return fallback


def _fetch_all_courses(course_client: CourseClient, cfg: FileConfig) -> list[Course]:
    all_rows: list[Course] = []
    for teaching_class_type in cfg.teaching_class_types:
        rows = course_client.list_general_electives_all_pages(
            teaching_class_type=teaching_class_type,
            page_size=cfg.page_size,
            max_pages=cfg.max_pages,
        )
        all_rows.extend(rows)

    dedup: dict[tuple[str, str], Course] = {}
    ordered: list[Course] = []
    for c in all_rows:
        key = (c.course_code.strip().upper(), c.sequence.strip())
        if key in dedup:
            continue
        dedup[key] = c
        ordered.append(c)
    return ordered


def main() -> int:
    setup_logging()

    cfg, created = load_or_create_config(CONFIG_PATH)
    if created:
        print(f"[INFO] 首次运行已创建配置文件: {CONFIG_PATH}")

    if not cfg.username or not cfg.password:
        raise RuntimeError("配置文件缺少 username/password")

    auth = AuthClient(base_url=cfg.base_url)
    http_client = AuthenticatedHttpClient(config=cfg, auth=auth)
    auth.http_client = http_client

    try:
        session_manager = SessionManager(
            auth=auth,
            http_client=http_client,
            username=cfg.username,
            password=cfg.password,
        )
        bundle = session_manager.login()
        print("[INFO] 登录成功")

        course_client = CourseClient(base_url=cfg.base_url, http_client=http_client)

        courses = call_with_relogin(
            lambda: _fetch_all_courses(course_client, cfg),
            session_manager=session_manager,
            session_error_detector=lambda exc: isinstance(exc, SessionExpiredError),
        )
        export_courses_csv(courses, cfg.all_courses_csv)
        print(f"[INFO] 已导出课程 CSV: {cfg.all_courses_csv} (共 {len(courses)} 条)")

        target_specs = parse_target_courses_csv(cfg.target_courses_csv)
        if not target_specs:
            print(
                "[INFO] 目标 CSV 为空：请从 all_courses.csv 复制目标行到 targets.csv，"
                "并填写 target_pool（对内/对外）后重试"
            )
            return 0

        monitor = TargetMonitorService(
            course_client=course_client,
            target_specs=target_specs,
            teaching_class_types=cfg.teaching_class_types,
            page_size=cfg.page_size,
            max_pages=cfg.max_pages,
        )

        executor = EnrollExecutor(
            course_client=course_client,
            batch_id=bundle.batch_id,
            execution_mode=cfg.execution_mode,
        )

        while True:
            snapshot = call_with_relogin(
                monitor.watch_once_with_snapshot,
                session_manager=session_manager,
                session_error_detector=lambda exc: isinstance(exc, SessionExpiredError),
                on_relogin=lambda b: _sync_batch_id(executor, b),
            )

            print(
                "[ROUND] "
                f"scanned={snapshot.scanned_total} "
                f"targets={snapshot.target_total} "
                f"found={snapshot.found_total} "
                f"available={snapshot.available_total} "
                f"pool_full={snapshot.pool_full_total}"
            )

            for state in snapshot.states:
                print(f"[WATCH] {_format_target_state_line(state)}")

            if not snapshot.available:
                time.sleep(cfg.poll_interval_seconds)
                continue

            for state in snapshot.available[:5]:
                if state.course is None:
                    continue
                print(f"[CANDIDATE][{state.spec.target_pool}] {_format_course_line(state.course)}")

            state = snapshot.available[0]
            if state.course is None:
                time.sleep(cfg.poll_interval_seconds)
                continue

            result = call_with_relogin(
                lambda: executor.try_enroll(state.course),
                session_manager=session_manager,
                session_error_detector=lambda exc: isinstance(exc, SessionExpiredError),
                on_relogin=lambda b: _sync_batch_id(executor, b),
            )
            print(result)

            if _should_stop_after_success(cfg=cfg, result=result):
                return 0

            time.sleep(cfg.poll_interval_seconds)
    finally:
        http_client.close()


if __name__ == "__main__":
    sys.exit(main())
