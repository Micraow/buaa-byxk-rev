from __future__ import annotations

from dataclasses import dataclass

from byxt_bot.auth_client import AuthClient
from byxt_bot.http_session import AuthenticatedHttpClient
from byxt_bot.token_login import SessionBundle, login_and_get_session


@dataclass
class SessionManager:
    auth: AuthClient
    http_client: AuthenticatedHttpClient
    username: str
    password: str

    def login(self) -> SessionBundle:
        bundle = login_and_get_session(self.username, self.password)
        self.http_client.apply_session(
            token=bundle.token,
            batch_id=bundle.batch_id,
            jsessionid=bundle.jsessionid,
            route=bundle.route,
        )
        return bundle

    def relogin(self) -> SessionBundle:
        return self.login()
