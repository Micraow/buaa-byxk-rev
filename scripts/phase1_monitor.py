from __future__ import annotations

from byxt_bot.auth_client import AuthClient
from byxt_bot.config import RuntimeConfig
from byxt_bot.course_client import CourseClient
from byxt_bot.http_session import AuthenticatedHttpClient
from byxt_bot.logging_setup import setup_logging
from byxt_bot.monitor_service import MonitorService
from byxt_bot.token_login import login_and_get_session


def build_mode() -> str:
    return "READ_ONLY"


def _format_capacity_snapshot(c) -> str:
    return (
        f"{c.course_code}-{c.sequence} {c.name} | "
        f"内 {c.internal_selected}/{c.internal_capacity} | "
        f"外 {c.external_selected}/{c.external_capacity} | "
        f"总 {c.selected_count}/{c.capacity} | "
        f"{c.language} | {c.schedule_room}"
    )


def main() -> int:
    setup_logging()
    cfg = RuntimeConfig()

    auth = AuthClient(base_url=cfg.base_url)
    http_client = AuthenticatedHttpClient(config=cfg, auth=auth)
    auth.http_client = http_client

    if cfg.token and cfg.batch_id:
        auth.load_from_browser_capture(cfg.token, cfg.batch_id)
        http_client.apply_session(token=cfg.token, batch_id=cfg.batch_id)
    elif cfg.username and cfg.password:
        session = login_and_get_session(cfg.username, cfg.password)
        http_client.apply_session(
            token=session.token,
            batch_id=session.batch_id,
            jsessionid=session.jsessionid,
            route=session.route,
        )
    else:
        raise RuntimeError("需提供 BYXT_TOKEN+BYXT_BATCH_ID 或 BYXT_USERNAME+BYXT_PASSWORD")

    if not auth.is_authenticated():
        raise RuntimeError("认证失败：登录态无效")

    course_client = CourseClient(base_url=cfg.base_url, http_client=http_client)
    monitor = MonitorService(
        course_client=course_client,
        poll_interval_seconds=cfg.poll_interval_seconds,
        page_size=cfg.page_size,
    )

    snapshot = monitor.watch_once_with_snapshot()
    print(
        "[ROUND] "
        f"scanned={snapshot.scanned_total} "
        f"english_targets={snapshot.english_target_total} "
        f"available={snapshot.available_total} "
        f"pool_full={snapshot.pool_full_total}"
    )

    if not snapshot.available:
        print("[INFO] 本轮无可提交目标课程")

    for c in snapshot.available:
        print(f"[AVAILABLE] {_format_capacity_snapshot(c)}")

    http_client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
