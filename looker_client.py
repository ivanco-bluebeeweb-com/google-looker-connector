"""Thin async HTTP client for the Looker REST API 4.0.

Auth: POST /login with client_id+client_secret (form-encoded), get back
access_token (Bearer). No refresh token -- re-login transparently on 401.
"""
from __future__ import annotations

import time
from typing import Any

import httpx

API_PORT = 19999
TOKEN_TTL_GUESS = 55 * 60  # seconds; real TTL is expires_in from /login (usually 3600s)

_session_cache: dict[str, dict] = {}  # conn_id -> {access_token, expires_at}


class ClientFail(Exception):
    def __init__(self, message: str, status: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.status = status
        self.retryable = retryable


def _base(instance_hostname: str) -> str:
    host = instance_hostname.strip().rstrip("/")
    if host.startswith("http"):
        host = host.split("://", 1)[1]
    host = host.split(":")[0]
    return f"https://{host}:{API_PORT}"


def _safe_json(resp: httpx.Response) -> dict:
    try:
        return resp.json()
    except Exception:
        return {}


async def login(instance_hostname: str, client_id: str, client_secret: str) -> dict:
    """Exchange client_id/client_secret for an access_token."""
    url = f"{_base(instance_hostname)}/api/4.0/login"
    async with httpx.AsyncClient(timeout=30, verify=True) as http:
        resp = await http.post(url, data={"client_id": client_id, "client_secret": client_secret})
    if resp.status_code != 200:
        body = _safe_json(resp)
        detail = body.get("message", resp.text[:200])
        raise ClientFail(f"Login failed: {detail}", status=resp.status_code, retryable=resp.status_code >= 500)
    data = _safe_json(resp)
    token = data.get("access_token")
    if not token:
        raise ClientFail("Login succeeded but no access_token returned.", status=200)
    return {"access_token": token, "expires_in": data.get("expires_in", TOKEN_TTL_GUESS)}


async def _ensure_session(conn: dict) -> str:
    cid = conn["id"]
    cached = _session_cache.get(cid)
    if cached and cached["expires_at"] > time.time() + 30:
        return cached["access_token"]
    result = await login(conn["instance_hostname"], conn["client_id"], conn["client_secret"])
    _session_cache[cid] = {"access_token": result["access_token"], "expires_at": time.time() + result["expires_in"]}
    return result["access_token"]


async def _request(method: str, conn: dict, path: str, retry: bool = True, **kwargs) -> httpx.Response:
    token = await _ensure_session(conn)
    url = f"{_base(conn['instance_hostname'])}/api/4.0{path}"
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=45) as http:
        resp = await http.request(method, url, headers=headers, **kwargs)
    if resp.status_code == 401 and retry:
        _session_cache.pop(conn["id"], None)
        return await _request(method, conn, path, retry=False, headers=headers, **kwargs)
    return resp


def _raise_for_error(resp: httpx.Response, action: str) -> None:
    if resp.status_code >= 400:
        body = _safe_json(resp)
        detail = body.get("message") or (body.get("errors") or [{}])[0].get("message", "") or resp.text[:200]
        raise ClientFail(f"{action} failed: {detail}", status=resp.status_code, retryable=resp.status_code >= 500 or resp.status_code == 429)


async def verify_connection(conn: dict) -> dict:
    """Validate credentials by calling a harmless read (list folders, 1 page)."""
    resp = await _request("GET", conn, "/folders?fields=id,name&limit=1")
    _raise_for_error(resp, "Connection verification")
    return {}


async def list_folders(conn: dict) -> list[dict]:
    resp = await _request("GET", conn, "/folders?fields=id,name,parent_id")
    _raise_for_error(resp, "List folders")
    return _safe_json(resp) if isinstance(_safe_json(resp), list) else []


async def list_looks(conn: dict, folder_id: str = "") -> list[dict]:
    path = "/looks?fields=id,title,folder,updated_at,user_id"
    resp = await _request("GET", conn, path)
    _raise_for_error(resp, "List looks")
    items = _safe_json(resp) or []
    if folder_id:
        items = [i for i in items if str((i.get("folder") or {}).get("id", "")) == str(folder_id)]
    return items


async def get_look(conn: dict, look_id: str) -> dict:
    resp = await _request("GET", conn, f"/looks/{look_id}")
    _raise_for_error(resp, "Get look")
    return _safe_json(resp)


async def run_look(conn: dict, look_id: str, result_format: str = "json") -> Any:
    resp = await _request("GET", conn, f"/looks/{look_id}/run/{result_format}")
    _raise_for_error(resp, "Run look")
    return _safe_json(resp) if result_format == "json" else resp.text


async def list_dashboards(conn: dict, folder_id: str = "") -> list[dict]:
    resp = await _request("GET", conn, "/dashboards?fields=id,title,folder,updated_at")
    _raise_for_error(resp, "List dashboards")
    items = _safe_json(resp) or []
    if folder_id:
        items = [i for i in items if str((i.get("folder") or {}).get("id", "")) == str(folder_id)]
    return items


async def get_dashboard(conn: dict, dashboard_id: str) -> dict:
    resp = await _request("GET", conn, f"/dashboards/{dashboard_id}")
    _raise_for_error(resp, "Get dashboard")
    return _safe_json(resp)


async def list_lookml_models(conn: dict) -> list[dict]:
    resp = await _request("GET", conn, "/lookml_models?fields=name,label,project_name")
    _raise_for_error(resp, "List LookML models")
    return _safe_json(resp) or []


async def get_explore(conn: dict, model_name: str, explore_name: str) -> dict:
    resp = await _request("GET", conn, f"/lookml_models/{model_name}/explores/{explore_name}")
    _raise_for_error(resp, "Get explore")
    return _safe_json(resp)


async def run_query(conn: dict, model_name: str, explore_name: str, fields: list[str], limit: int) -> list[dict]:
    body = {"model": model_name, "view": explore_name, "fields": fields, "limit": limit}
    resp = await _request("POST", conn, "/queries/run/json", json=body)
    _raise_for_error(resp, "Run query")
    return _safe_json(resp) or []


async def list_scheduled_plans(conn: dict) -> list[dict]:
    resp = await _request("GET", conn, "/scheduled_plans/search?fields=id,name,enabled,crontab,look_id,dashboard_id")
    _raise_for_error(resp, "List scheduled plans")
    return _safe_json(resp) or []


async def get_scheduled_plan(conn: dict, plan_id: str) -> dict:
    resp = await _request("GET", conn, f"/scheduled_plans/{plan_id}")
    _raise_for_error(resp, "Get scheduled plan")
    return _safe_json(resp)


async def run_scheduled_plan_once(conn: dict, plan_id: str) -> dict:
    plan = await get_scheduled_plan(conn, plan_id)
    resp = await _request("POST", conn, "/scheduled_plans/run_once", json=plan)
    _raise_for_error(resp, "Run scheduled plan once")
    return _safe_json(resp)


async def list_users(conn: dict) -> list[dict]:
    resp = await _request("GET", conn, "/users?fields=id,display_name,email,role_ids")
    _raise_for_error(resp, "List users")
    return _safe_json(resp) or []


async def run_content_validation(conn: dict) -> dict:
    resp = await _request("GET", conn, "/content_validation")
    _raise_for_error(resp, "Run content validation")
    return _safe_json(resp)
