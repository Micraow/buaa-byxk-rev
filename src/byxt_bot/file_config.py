from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from getpass import getpass
from pathlib import Path
from typing import Callable


_ALLOWED_MODES = {"READ_ONLY", "DRY_RUN", "ARMED"}


@dataclass(frozen=True)
class FileConfig:
    base_url: str = "https://byxk.buaa.edu.cn/xsxk"
    username: str = ""
    password: str = ""
    execution_mode: str = "DRY_RUN"
    token: str = ""
    batch_id: str = ""
    poll_interval_seconds: float = 3.0
    page_size: int = 10
    teaching_class_types: tuple[str, ...] = ("XGKC", "TJKC")
    max_pages: int = 200
    all_courses_csv: str = "output/all_courses.csv"
    target_courses_csv: str = "output/targets.csv"
    stop_after_success: bool = True


InputFn = Callable[[str], str]


def load_or_create_config(
    file_path: str,
    *,
    input_fn: InputFn = input,
    password_fn: InputFn = getpass,
) -> tuple[FileConfig, bool]:
    path = Path(file_path)

    if path.exists():
        return _load_config(path), False

    username = input_fn("请输入 BYXT 学号/用户名: ").strip()
    password = password_fn("请输入 BYXT 密码: ").strip()

    cfg = FileConfig(username=username, password=password)
    save_config(path, cfg)
    return cfg, True


def save_config(path: Path, cfg: FileConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(cfg)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_config(path: Path) -> FileConfig:
    raw_text = path.read_text(encoding="utf-8")
    data = json.loads(raw_text) if raw_text.strip() else {}
    if not isinstance(data, dict):
        raise ValueError("配置文件格式错误：应为 JSON object")

    defaults = asdict(FileConfig())
    merged = {**defaults, **data}

    execution_mode = str(merged.get("execution_mode", defaults["execution_mode"])).upper()
    if execution_mode not in _ALLOWED_MODES:
        raise ValueError(f"execution_mode 必须是 {_ALLOWED_MODES} 之一")

    return FileConfig(
        base_url=str(merged.get("base_url", defaults["base_url"])),
        username=str(merged.get("username", "")),
        password=str(merged.get("password", "")),
        execution_mode=execution_mode,
        token=str(merged.get("token", defaults["token"])),
        batch_id=str(merged.get("batch_id", defaults["batch_id"])),
        poll_interval_seconds=float(merged.get("poll_interval_seconds", defaults["poll_interval_seconds"])),
        page_size=int(merged.get("page_size", defaults["page_size"])),
        teaching_class_types=_to_teaching_class_types(
            merged.get("teaching_class_types", defaults["teaching_class_types"])
        ),
        max_pages=int(merged.get("max_pages", defaults["max_pages"])),
        all_courses_csv=str(merged.get("all_courses_csv", defaults["all_courses_csv"])),
        target_courses_csv=str(merged.get("target_courses_csv", defaults["target_courses_csv"])),
        stop_after_success=bool(merged.get("stop_after_success", defaults["stop_after_success"])),
    )


def _to_teaching_class_types(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        cleaned = [x.strip().upper() for x in value.split(",") if x.strip()]
        return tuple(cleaned) if cleaned else ("XGKC", "TJKC")

    if isinstance(value, list):
        cleaned = [str(x).strip().upper() for x in value if str(x).strip()]
        return tuple(cleaned) if cleaned else ("XGKC", "TJKC")

    if isinstance(value, tuple):
        cleaned = [str(x).strip().upper() for x in value if str(x).strip()]
        return tuple(cleaned) if cleaned else ("XGKC", "TJKC")

    return ("XGKC", "TJKC")
