from dataclasses import dataclass, field
from typing import Any


@dataclass
class AuthClient:
    base_url: str
    http_client: Any | None = None
    batch_id: str | None = None
    _session_token: str | None = field(default=None, init=False)

    def login(self, username: str, password: str) -> bool:
        if not username or not password:
            return False
        if self.http_client is None:
            return False

        try:
            resp = self.http_client.post_form(
                f"{self.base_url}/web/studentInfo",
                data={"token": password},
            )
        except Exception:
            return False

        if resp.status_code >= 400:
            return False

        token = password.strip()
        if not token:
            return False

        self._session_token = token
        return True

    def load_from_browser_capture(self, token: str, batch_id: str) -> None:
        self._session_token = token
        self.batch_id = batch_id

    def is_authenticated(self) -> bool:
        return bool(self._session_token)

    def refresh_if_needed(self) -> bool:
        if self.is_authenticated():
            return True
        return False

    def get_auth_headers(self) -> dict[str, str]:
        if not self._session_token:
            return {}
        headers = {
            "Authorization": self._session_token,
            "Content-Type": "application/json;charset=UTF-8",
        }
        if self.batch_id:
            headers["batchId"] = self.batch_id
        return headers
