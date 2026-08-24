"""Chat tool handlers for Google Looker Connector.

Connection storage follows the Power BI/Tableau/Qlik precedent: one secret
holding a JSON array of connection records. The live access_token is
cached separately in looker_client.py, never persisted here.
"""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import looker_client as lc
from app import chat
from schemas import (
    NoParams, ConnectLookerParams, DisconnectLookerParams, ConnectionInfo, ListConnectionsResult,
    ConnectionScopedParams, FolderItem, ListFoldersResult,
    ListLooksParams, LookItem, ListLooksResult, LookScopedParams, LookDetail,
    RunLookParams, RunLookResult,
    ListDashboardsParams, DashboardItem, ListDashboardsResult, DashboardScopedParams, DashboardDetail, DashboardElementItem,
    ListLookmlModelsResult, LookmlModelItem, GetExploreParams, ExploreDetail,
    RunQueryParams, RunQueryResult,
    ListScheduledPlansResult, ScheduledPlanItem, ScheduledPlanScopedParams, RunScheduledPlanResult,
    ListUsersResult, LookerUserItem,
    ContentValidationResult, ContentValidationError,
    AuditHealthParams, HealthAudit,
)

SECRET_NAME = "looker_connections"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(SECRET_NAME)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return []


async def _save_connections(ctx, connections: list[dict]) -> None:
    await ctx.secrets.set(SECRET_NAME, json.dumps(connections))


async def _resolve_connection(ctx, connection_id: str) -> dict:
    connections = await _load_connections(ctx)
    if not connections:
        raise ValueError("No Looker instance connected yet. Run connect_looker first.")
    if connection_id:
        for c in connections:
            if c.get("id") == connection_id:
                return c
        raise ValueError(f"Connection '{connection_id}' not found.")
    return connections[0]


@chat.function("connect_looker", "Connect a Google Looker instance via API3 Key, after validating the credentials actually work (logs in and lists folders).", action_type="write", chain_callable=True, data_model=ConnectionInfo, event="google-looker-connector.connect_looker", effects=["looker.provider.connected"])
async def connect_looker(ctx, params: ConnectLookerParams) -> ActionResult:
    """Imperal action: connect_looker."""
    conn = {
        "id": str(uuid.uuid4()), "label": params.label or params.instance_hostname,
        "instance_hostname": params.instance_hostname, "client_id": params.client_id, "client_secret": params.client_secret,
    }
    try:
        await lc.verify_connection(conn)
    except lc.ClientFail as e:
        return ActionResult.error(str(e.message), code="LOOKER_CONNECT_FAILED")
    connections = await _load_connections(ctx)
    connections.append(conn)
    await _save_connections(ctx, connections)
    return ActionResult.success(
        data=ConnectionInfo(id=conn["id"], label=conn["label"], instance_hostname=conn["instance_hostname"]),
        summary=f"Connected to Looker instance '{conn['label']}'.",
        refresh_panels=["looker_sidebar"],
    )


@chat.function("disconnect_looker", "Disconnect a Looker instance: deletes only the saved credentials. Nothing in Looker itself is changed.", action_type="write", chain_callable=True, data_model=ListConnectionsResult, event="google-looker-connector.disconnect_looker", effects=["looker.provider.disconnected"])
async def disconnect_looker(ctx, params: DisconnectLookerParams) -> ActionResult:
    """Imperal action: disconnect_looker."""
    connections = await _load_connections(ctx)
    remaining = [c for c in connections if c.get("id") != params.connection_id]
    if len(remaining) == len(connections):
        return ActionResult.error(f"Connection '{params.connection_id}' not found.", code="LOOKER_CONNECTION_NOT_FOUND")
    await _save_connections(ctx, remaining)
    lc._session_cache.pop(params.connection_id, None)
    items = [ConnectionInfo(id=c["id"], label=c.get("label", ""), instance_hostname=c.get("instance_hostname", "")) for c in remaining]
    return ActionResult.success(data=ListConnectionsResult(items=items), summary="Disconnected.", refresh_panels=["looker_sidebar", "looker_settings"])


@chat.function("list_connections", "List the connected Looker instances.", action_type="read", chain_callable=True, data_model=ListConnectionsResult, event="google-looker-connector.list_connections")
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """Imperal action: list_connections."""
    connections = await _load_connections(ctx)
    items = [ConnectionInfo(id=c["id"], label=c.get("label", ""), instance_hostname=c.get("instance_hostname", "")) for c in connections]
    return ActionResult.success(data=ListConnectionsResult(items=items))


@chat.function("list_folders", "List folders on the connected Looker instance.", action_type="read", chain_callable=True, data_model=ListFoldersResult, event="google-looker-connector.list_folders")
async def list_folders(ctx, params: ConnectionScopedParams) -> ActionResult:
    """Imperal action: list_folders."""
    try:
        conn = await _resolve_connection(ctx, params.connection_id)
        raw = await lc.list_folders(conn)
    except (lc.ClientFail, ValueError) as e:
        return ActionResult.error(str(getattr(e, "message", e)), code="LOOKER_LIST_FOLDERS_FAILED")
    items = [FolderItem(id=str(f["id"]), name=f.get("name", ""), parent_id=str(f.get("parent_id") or "")) for f in raw]
    return ActionResult.success(data=ListFoldersResult(items=items))


@chat.function("list_looks", "List Looks on the connected Looker instance, optionally filtered to one folder.", action_type="read", chain_callable=True, data_model=ListLooksResult, event="google-looker-connector.list_looks")
async def list_looks(ctx, params: ListLooksParams) -> ActionResult:
    """Imperal action: list_looks."""
    try:
        conn = await _resolve_connection(ctx, params.connection_id)
        raw = await lc.list_looks(conn, params.folder_id)
    except (lc.ClientFail, ValueError) as e:
        return ActionResult.error(str(getattr(e, "message", e)), code="LOOKER_LIST_LOOKS_FAILED")
    items = [LookItem(
        id=str(l["id"]), title=l.get("title", ""),
        folder_id=str((l.get("folder") or {}).get("id", "")), updated_at=l.get("updated_at", ""),
        user_id=str(l.get("user_id", "")),
    ) for l in raw]
    return ActionResult.success(data=ListLooksResult(items=items))


@chat.function("get_look", "Read one Look's metadata in full by id.", action_type="read", chain_callable=True, data_model=LookDetail, event="google-looker-connector.get_look")
async def get_look(ctx, params: LookScopedParams) -> ActionResult:
    """Imperal action: get_look."""
    try:
        conn = await _resolve_connection(ctx, params.connection_id)
        l = await lc.get_look(conn, params.look_id)
    except (lc.ClientFail, ValueError) as e:
        return ActionResult.error(str(getattr(e, "message", e)), code="LOOKER_GET_LOOK_FAILED")
    q = l.get("query") or {}
    return ActionResult.success(data=LookDetail(
        id=str(l.get("id", "")), title=l.get("title", ""), description=l.get("description", "") or "",
        model_name=q.get("model", ""), view_name=q.get("view", ""),
    ))


@chat.function("run_look", "Run a Look and return its result rows (or raw text for csv/png/xlsx).", action_type="read", chain_callable=True, data_model=RunLookResult, event="google-looker-connector.run_look")
async def run_look(ctx, params: RunLookParams) -> ActionResult:
    """Imperal action: run_look."""
    try:
        conn = await _resolve_connection(ctx, params.connection_id)
        result = await lc.run_look(conn, params.look_id, params.result_format)
    except (lc.ClientFail, ValueError) as e:
        return ActionResult.error(str(getattr(e, "message", e)), code="LOOKER_RUN_LOOK_FAILED")
    if isinstance(result, list):
        return ActionResult.success(data=RunLookResult(look_id=params.look_id, result_format=params.result_format, rows=result))
    return ActionResult.success(data=RunLookResult(look_id=params.look_id, result_format=params.result_format, raw_text=str(result)[:5000]))


@chat.function("list_dashboards", "List Dashboards on the connected Looker instance, optionally filtered to one folder.", action_type="read", chain_callable=True, data_model=ListDashboardsResult, event="google-looker-connector.list_dashboards")
async def list_dashboards(ctx, params: ListDashboardsParams) -> ActionResult:
    """Imperal action: list_dashboards."""
    try:
        conn = await _resolve_connection(ctx, params.connection_id)
        raw = await lc.list_dashboards(conn, params.folder_id)
    except (lc.ClientFail, ValueError) as e:
        return ActionResult.error(str(getattr(e, "message", e)), code="LOOKER_LIST_DASHBOARDS_FAILED")
    items = [DashboardItem(
        id=str(d["id"]), title=d.get("title", ""),
        folder_id=str((d.get("folder") or {}).get("id", "")), updated_at=d.get("updated_at", ""),
    ) for d in raw]
    return ActionResult.success(data=ListDashboardsResult(items=items))


@chat.function("get_dashboard", "Read one Dashboard in full by id, including its elements.", action_type="read", chain_callable=True, data_model=DashboardDetail, event="google-looker-connector.get_dashboard")
async def get_dashboard(ctx, params: DashboardScopedParams) -> ActionResult:
    """Imperal action: get_dashboard."""
    try:
        conn = await _resolve_connection(ctx, params.connection_id)
        d = await lc.get_dashboard(conn, params.dashboard_id)
    except (lc.ClientFail, ValueError) as e:
        return ActionResult.error(str(getattr(e, "message", e)), code="LOOKER_GET_DASHBOARD_FAILED")
    elements = [DashboardElementItem(title=e.get("title", "") or "", type=e.get("type", "")) for e in (d.get("dashboard_elements") or [])]
    return ActionResult.success(data=DashboardDetail(id=str(d.get("id", "")), title=d.get("title", ""), description=d.get("description", "") or "", elements=elements))


@chat.function("list_lookml_models", "List LookML models available on the connected Looker instance.", action_type="read", chain_callable=True, data_model=ListLookmlModelsResult, event="google-looker-connector.list_lookml_models")
async def list_lookml_models(ctx, params: ConnectionScopedParams) -> ActionResult:
    """Imperal action: list_lookml_models."""
    try:
        conn = await _resolve_connection(ctx, params.connection_id)
        raw = await lc.list_lookml_models(conn)
    except (lc.ClientFail, ValueError) as e:
        return ActionResult.error(str(getattr(e, "message", e)), code="LOOKER_LIST_LOOKML_MODELS_FAILED")
    items = [LookmlModelItem(name=m.get("name", ""), label=m.get("label", "") or "", project_name=m.get("project_name", "") or "") for m in raw]
    return ActionResult.success(data=ListLookmlModelsResult(items=items))


@chat.function("get_explore", "Read one Explore's field metadata (dimensions/measures) in full.", action_type="read", chain_callable=True, data_model=ExploreDetail, event="google-looker-connector.get_explore")
async def get_explore(ctx, params: GetExploreParams) -> ActionResult:
    """Imperal action: get_explore."""
    try:
        conn = await _resolve_connection(ctx, params.connection_id)
        e = await lc.get_explore(conn, params.model_name, params.explore_name)
    except (lc.ClientFail, ValueError) as ex:
        return ActionResult.error(str(getattr(ex, "message", ex)), code="LOOKER_GET_EXPLORE_FAILED")
    fields = e.get("fields") or {}
    dims = [f.get("name", "") for f in (fields.get("dimensions") or [])]
    measures = [f.get("name", "") for f in (fields.get("measures") or [])]
    return ActionResult.success(data=ExploreDetail(name=e.get("name", ""), label=e.get("label", "") or "", dimensions=dims, measures=measures))


@chat.function("run_query", "Run an ad-hoc query directly against a model/explore, without saving it as a Look.", action_type="read", chain_callable=True, data_model=RunQueryResult, event="google-looker-connector.run_query")
async def run_query(ctx, params: RunQueryParams) -> ActionResult:
    """Imperal action: run_query."""
    try:
        conn = await _resolve_connection(ctx, params.connection_id)
        rows = await lc.run_query(conn, params.model_name, params.explore_name, params.fields, params.limit)
    except (lc.ClientFail, ValueError) as e:
        return ActionResult.error(str(getattr(e, "message", e)), code="LOOKER_RUN_QUERY_FAILED")
    return ActionResult.success(data=RunQueryResult(rows=rows))


@chat.function("list_scheduled_plans", "List Scheduled Plans (recurring deliveries) configured on the connected Looker instance.", action_type="read", chain_callable=True, data_model=ListScheduledPlansResult, event="google-looker-connector.list_scheduled_plans")
async def list_scheduled_plans(ctx, params: ConnectionScopedParams) -> ActionResult:
    """Imperal action: list_scheduled_plans."""
    try:
        conn = await _resolve_connection(ctx, params.connection_id)
        raw = await lc.list_scheduled_plans(conn)
    except (lc.ClientFail, ValueError) as e:
        return ActionResult.error(str(getattr(e, "message", e)), code="LOOKER_LIST_SCHEDULED_PLANS_FAILED")
    items = [ScheduledPlanItem(
        id=str(p["id"]), name=p.get("name", ""), enabled=bool(p.get("enabled", False)), crontab=p.get("crontab", "") or "",
        look_id=str(p.get("look_id") or ""), dashboard_id=str(p.get("dashboard_id") or ""),
    ) for p in raw]
    return ActionResult.success(data=ListScheduledPlansResult(items=items))


@chat.function("run_scheduled_plan_once", "Manually run a Scheduled Plan right now, regardless of its cron timing.", action_type="write", chain_callable=True, data_model=RunScheduledPlanResult, event="google-looker-connector.run_scheduled_plan_once", effects=["looker.scheduled_plan.triggered"])
async def run_scheduled_plan_once(ctx, params: ScheduledPlanScopedParams) -> ActionResult:
    """Imperal action: run_scheduled_plan_once."""
    try:
        conn = await _resolve_connection(ctx, params.connection_id)
        await lc.run_scheduled_plan_once(conn, params.plan_id)
    except (lc.ClientFail, ValueError) as e:
        return ActionResult.error(str(getattr(e, "message", e)), code="LOOKER_RUN_SCHEDULED_PLAN_FAILED")
    return ActionResult.success(data=RunScheduledPlanResult(plan_id=params.plan_id, status="triggered"), summary="Scheduled plan triggered.", refresh_panels=["looker_center"])


@chat.function("list_users", "List users registered on the connected Looker instance.", action_type="read", chain_callable=True, data_model=ListUsersResult, event="google-looker-connector.list_users")
async def list_users(ctx, params: ConnectionScopedParams) -> ActionResult:
    """Imperal action: list_users."""
    try:
        conn = await _resolve_connection(ctx, params.connection_id)
        raw = await lc.list_users(conn)
    except (lc.ClientFail, ValueError) as e:
        return ActionResult.error(str(getattr(e, "message", e)), code="LOOKER_LIST_USERS_FAILED")
    items = [LookerUserItem(id=str(u["id"]), display_name=u.get("display_name", "") or "", email=u.get("email", "") or "", role_ids=[str(r) for r in (u.get("role_ids") or [])]) for u in raw]
    return ActionResult.success(data=ListUsersResult(items=items))


@chat.function("run_content_validation", "Run Looker's built-in content validation -- scans Looks/Dashboards for broken references to deleted LookML fields.", action_type="read", chain_callable=True, data_model=ContentValidationResult, event="google-looker-connector.run_content_validation")
async def run_content_validation(ctx, params: ConnectionScopedParams) -> ActionResult:
    """Imperal action: run_content_validation."""
    try:
        conn = await _resolve_connection(ctx, params.connection_id)
        raw = await lc.run_content_validation(conn)
    except (lc.ClientFail, ValueError) as e:
        return ActionResult.error(str(getattr(e, "message", e)), code="LOOKER_CONTENT_VALIDATION_FAILED")
    errors = []
    for item in (raw.get("content_with_errors") or []):
        errors.append(ContentValidationError(
            content_type=item.get("content_type", ""),
            title=(item.get("look") or item.get("dashboard") or {}).get("title", "") or "",
            message="; ".join(e.get("message", "") for e in (item.get("errors") or [])) or "Broken reference",
        ))
    return ActionResult.success(data=ContentValidationResult(error_count=len(errors), errors=errors))


@chat.function("audit_instance_health", "Build one aggregated health report across the connected Looker instance: folder/Look/Dashboard counts and content validation errors.", action_type="read", chain_callable=True, data_model=HealthAudit, event="google-looker-connector.audit_instance_health")
async def audit_instance_health(ctx, params: AuditHealthParams) -> ActionResult:
    """Imperal action: audit_instance_health."""
    try:
        conn = await _resolve_connection(ctx, params.connection_id)
        folders = await lc.list_folders(conn)
        looks = await lc.list_looks(conn)
        dashboards = await lc.list_dashboards(conn)
        validation = await lc.run_content_validation(conn)
        plans = await lc.list_scheduled_plans(conn)
    except (lc.ClientFail, ValueError) as e:
        return ActionResult.error(str(getattr(e, "message", e)), code="LOOKER_AUDIT_FAILED")
    failed_recent = sum(1 for p in plans if str(p.get("last_run_status", "")).lower() == "failure")
    return ActionResult.success(data=HealthAudit(
        folder_count=len(folders), look_count=len(looks), dashboard_count=len(dashboards),
        failed_scheduled_plans_24h=failed_recent,
        content_validation_errors=len(validation.get("content_with_errors") or []),
    ))
