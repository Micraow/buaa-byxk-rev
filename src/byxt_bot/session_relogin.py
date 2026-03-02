from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import logging


T = TypeVar("T")

logger = logging.getLogger(__name__)


def call_with_relogin(
    operation: Callable[[], T],
    *,
    session_manager,
    session_error_detector: Callable[[Exception], bool],
    on_relogin: Callable[[object], None] | None = None,
) -> T:
    try:
        return operation()
    except Exception as exc:
        if not session_error_detector(exc):
            raise
        logger.warning("检测到登录态失效，正在自动重登并重试一次")
        bundle = session_manager.relogin()
        if on_relogin is not None:
            on_relogin(bundle)
        return operation()
