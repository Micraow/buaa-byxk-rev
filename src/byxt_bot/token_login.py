from __future__ import annotations

import re
from dataclasses import dataclass

import httpx


LOGIN_URL = "https://sso.buaa.edu.cn/login?service=https%3A%2F%2Fbyxk.buaa.edu.cn%2Fxsxk%2Fauth%2Fcas"


@dataclass(frozen=True)
class SessionBundle:
    token: str
    batch_id: str
    jsessionid: str
    route: str


def login_and_get_session(username: str, password: str) -> SessionBundle:
    if not username or not password:
        raise RuntimeError("username/password 不能为空")

    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        page = client.get(LOGIN_URL)
        page.raise_for_status()

        execution_match = re.search(r'name="execution"\s+value="([^"]+)"', page.text)
        if not execution_match:
            raise RuntimeError("未找到 CAS execution 参数")

        execution = execution_match.group(1)

        form = {
            "username": username,
            "password": password,
            "type": "username_password",
            "execution": execution,
            "_eventId": "submit",
            "submit": "LOGIN",
        }

        resp = client.post(
            "https://sso.buaa.edu.cn/login",
            data=form,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": LOGIN_URL,
                "Origin": "https://sso.buaa.edu.cn",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) byxt-bot/0.1",
            },
        )
        resp.raise_for_status()

        token = client.cookies.get("token", domain="byxk.buaa.edu.cn") or client.cookies.get("token")
        jsessionid = client.cookies.get("JSESSIONID", domain="byxk.buaa.edu.cn") or client.cookies.get("JSESSIONID")
        route = client.cookies.get("route", domain="byxk.buaa.edu.cn") or client.cookies.get("route")

        if not token:
            raise RuntimeError("登录后未获取到 token")

        # 先从 studentInfo 获取可选轮次（无需预先知道 batchId）
        info_resp = client.post(
            "https://byxk.buaa.edu.cn/xsxk/web/studentInfo",
            data={"token": token},
            headers={
                "Authorization": token,
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "https://byxk.buaa.edu.cn/xsxk/profile/index.html",
                "Origin": "https://byxk.buaa.edu.cn",
            },
        )

        if info_resp.status_code >= 400:
            raise RuntimeError("web/studentInfo 请求失败")

        ctype = info_resp.headers.get("content-type", "")
        if "application/json" not in ctype:
            raise RuntimeError("web/studentInfo 未返回 JSON")

        payload = info_resp.json()
        student = payload.get("data", {}).get("student", {}) if isinstance(payload, dict) else {}
        batches = student.get("electiveBatchList", []) if isinstance(student, dict) else []

        batch_id = ""
        for item in batches:
            if not isinstance(item, dict):
                continue
            if str(item.get("canSelect", "0")) == "1" and item.get("code"):
                batch_id = str(item.get("code"))
                break

        if not batch_id and batches:
            first = batches[0]
            if isinstance(first, dict) and first.get("code"):
                batch_id = str(first.get("code"))

        if not batch_id:
            raise RuntimeError("登录后未能提取 batchId")

        return SessionBundle(
            token=token,
            batch_id=batch_id,
            jsessionid=jsessionid or "",
            route=route or "",
        )
