from dataclasses import dataclass
from typing import Any

import httpx

from byxt_bot.auth_client import AuthClient


@dataclass
class AuthenticatedHttpClient:
    config: Any
    auth: AuthClient

    def __post_init__(self) -> None:
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
                "Origin": "https://byxk.buaa.edu.cn",
                "Referer": "https://byxk.buaa.edu.cn/xsxk/profile/index.html",
            },
        )

        token = (self.config.token or "").strip()
        if token:
            self.client.cookies.set("token", token, domain="byxk.buaa.edu.cn", path="/")
            self.client.cookies.set("Authorization", token, domain="byxk.buaa.edu.cn", path="/")
            self.auth.load_from_browser_capture(token=token, batch_id=self.config.batch_id)

    def apply_session(self, *, token: str, batch_id: str, jsessionid: str = "", route: str = "") -> None:
        self.client.cookies.set("token", token, domain="byxk.buaa.edu.cn", path="/")
        self.client.cookies.set("Authorization", token, domain="byxk.buaa.edu.cn", path="/")
        if jsessionid:
            self.client.cookies.set("JSESSIONID", jsessionid, domain="byxk.buaa.edu.cn", path="/xsxk")
        if route:
            self.client.cookies.set("route", route, domain="byxk.buaa.edu.cn", path="/")
        self.auth.load_from_browser_capture(token=token, batch_id=batch_id)

    def post(self, url: str, *, json: dict[str, Any]) -> httpx.Response:
        headers = self.auth.get_auth_headers()
        return self.client.post(url, json=json, headers=headers)

    def post_form(self, url: str, data: dict[str, Any]) -> httpx.Response:
        headers = {
            "Authorization": self.auth.get_auth_headers().get("Authorization", ""),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        return self.client.post(url, data=data, headers=headers)

    def close(self) -> None:
        self.client.close()
