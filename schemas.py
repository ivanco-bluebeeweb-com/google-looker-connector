"""Pydantic parameter/result schemas for Google Looker Connector tools."""
from __future__ import annotations

from pydantic import BaseModel, Field


class NoParams(BaseModel):
    """Explicit empty params model -- V17 disallows untyped handlers."""
    pass


# ---- Connection management ----

class ConnectLookerParams(BaseModel):
    instance_hostname: str = Field(..., description="Looker instance hostname, e.g. mycompany.looker.com (no port -- added automatically).")
    client_id: str = Field(..., description="API3 Key client_id (Admin > Users > Edit Keys, or Admin > API Keys).")
    client_secret: str = Field(..., description="API3 Key client_secret.")
    label: str = Field("", description="Optional friendly label, e.g. 'Production instance'.")


class DisconnectLookerParams(BaseModel):
    connection_id: str = Field(..., description="Connection id from list_connections.")


class ConnectionInfo(BaseModel):
    id: str
    label: str
    instance_hostname: str


class ListConnectionsResult(BaseModel):
    items: list[ConnectionInfo] = Field(default_factory=list)


class ConnectionScopedParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the first connected instance.")


# ---- Folders ----

class FolderItem(BaseModel):
    id: str
    name: str
    parent_id: str = ""


class ListFoldersResult(BaseModel):
    items: list[FolderItem] = Field(default_factory=list)


# ---- Looks ----

class ListLooksParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the first connected instance.")
    folder_id: str = Field("", description="Filter to one folder; omit for all Looks visible to the API3 Key.")


class LookItem(BaseModel):
    id: str
    title: str
    folder_id: str = ""
    updated_at: str = ""
    user_id: str = ""


class ListLooksResult(BaseModel):
    items: list[LookItem] = Field(default_factory=list)


class LookScopedParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the first connected instance.")
    look_id: str = Field(..., description="Look id from list_looks.")


class RunLookParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the first connected instance.")
    look_id: str = Field(..., description="Look id from list_looks.")
    result_format: str = Field("json", description="Result format: json, csv, png, or xlsx.")


class RunLookResult(BaseModel):
    look_id: str
    result_format: str
    rows: list[dict] = Field(default_factory=list)
    raw_text: str = ""


class LookDetail(BaseModel):
    id: str
    title: str
    description: str = ""
    model_name: str = ""
    view_name: str = ""


# ---- Dashboards ----

class ListDashboardsParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the first connected instance.")
    folder_id: str = Field("", description="Filter to one folder; omit for all Dashboards visible to the API3 Key.")


class DashboardItem(BaseModel):
    id: str
    title: str
    folder_id: str = ""
    updated_at: str = ""


class ListDashboardsResult(BaseModel):
    items: list[DashboardItem] = Field(default_factory=list)


class DashboardScopedParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the first connected instance.")
    dashboard_id: str = Field(..., description="Dashboard id from list_dashboards.")


class DashboardElementItem(BaseModel):
    title: str = ""
    type: str = ""


class DashboardDetail(BaseModel):
    id: str
    title: str
    description: str = ""
    elements: list[DashboardElementItem] = Field(default_factory=list)


# ---- LookML models / Explores ----

class LookmlModelItem(BaseModel):
    name: str
    label: str = ""
    project_name: str = ""


class ListLookmlModelsResult(BaseModel):
    items: list[LookmlModelItem] = Field(default_factory=list)


class GetExploreParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the first connected instance.")
    model_name: str = Field(..., description="LookML model name from list_lookml_models.")
    explore_name: str = Field(..., description="Explore name within the model.")


class ExploreField(BaseModel):
    name: str
    label: str = ""
    type: str = ""


class ExploreDetail(BaseModel):
    name: str
    label: str = ""
    dimensions: list[ExploreField] = Field(default_factory=list)
    measures: list[ExploreField] = Field(default_factory=list)


# ---- Queries ----

class RunQueryParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the first connected instance.")
    model_name: str = Field(..., description="LookML model name, e.g. 'ecommerce'.")
    explore_name: str = Field(..., description="Explore name within the model, e.g. 'orders'.")
    fields: list[str] = Field(..., description="Dimension/measure field ids to select, e.g. ['orders.count', 'orders.created_date'].")
    limit: int = Field(500, description="Max rows to return.")


class RunQueryResult(BaseModel):
    rows: list[dict] = Field(default_factory=list)


# ---- Scheduled plans ----

class ListScheduledPlansResult(BaseModel):
    items: list["ScheduledPlanItem"] = Field(default_factory=list)


class ScheduledPlanItem(BaseModel):
    id: str
    name: str
    enabled: bool = False
    crontab: str = ""
    look_id: str = ""
    dashboard_id: str = ""


class ScheduledPlanScopedParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the first connected instance.")
    plan_id: str = Field(..., description="Scheduled plan id from list_scheduled_plans.")


class ScheduledPlanDetail(BaseModel):
    id: str
    name: str
    enabled: bool = False
    crontab: str = ""


class RunScheduledPlanResult(BaseModel):
    plan_id: str
    status: str = "triggered"


# ---- Users ----

class ListUsersResult(BaseModel):
    items: list["LookerUserItem"] = Field(default_factory=list)


class LookerUserItem(BaseModel):
    id: str
    display_name: str = ""
    email: str = ""
    role_ids: list[str] = Field(default_factory=list)


# ---- Content validation ----

class ContentValidationError(BaseModel):
    content_type: str = ""
    title: str = ""
    message: str = ""


class ContentValidationResult(BaseModel):
    error_count: int = 0
    errors: list[ContentValidationError] = Field(default_factory=list)


# ---- Audit ----

class AuditHealthParams(BaseModel):
    connection_id: str = Field("", description="Connection id; omit to use the first connected instance.")


class HealthAudit(BaseModel):
    folder_count: int = 0
    look_count: int = 0
    dashboard_count: int = 0
    failed_scheduled_plans_24h: int = 0
    content_validation_errors: int = 0
