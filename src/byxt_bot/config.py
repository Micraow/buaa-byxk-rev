from dataclasses import dataclass
import os


@dataclass(frozen=True)
class RuntimeConfig:
    base_url: str = os.getenv("BYXT_BASE_URL", "https://byxk.buaa.edu.cn/xsxk")
    username: str = os.getenv("BYXT_USERNAME", "")
    password: str = os.getenv("BYXT_PASSWORD", "")
    execution_mode: str = os.getenv("EXECUTION_MODE", "READ_ONLY")
    token: str = os.getenv("BYXT_TOKEN", "")
    batch_id: str = os.getenv("BYXT_BATCH_ID", "")
    page_size: int = int(os.getenv("BYXT_PAGE_SIZE", "10"))
    poll_interval_seconds: float = float(os.getenv("BYXT_POLL_INTERVAL", "0.5"))
