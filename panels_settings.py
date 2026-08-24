"""The single 'App settings' screen (center slot) -- connection management
and health snapshot for Google Looker Connector."""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
import handlers as h
from schemas import AuditHealthParams


def _connection_row(c: dict) -> ui.UINode:
    label = c.get("label") or c.get("instance_hostname", "")
    return ui.Stack(direction="v", gap=1, align="start", children=[
        ui.Text(label, variant="body"),
        ui.Text(f"Instance: {c.get('instance_hostname', '')}", variant="caption"),
        ui.Button("Disconnect", variant="danger", size="sm",
                  on_click=ui.Call("disconnect_looker", {"connection_id": c.get("id")})),
    ])


def _connections_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Stack(direction="v", gap=1, children=[
            ui.Text("Connections", variant="heading"),
            ui.Text("No instances connected yet.", variant="caption"),
        ])
    children: list[ui.UINode] = [ui.Text("Connections", variant="heading")]
    for i, c in enumerate(connections):
        if i > 0:
            children.append(ui.Divider())
        children.append(_connection_row(c))
    return ui.Stack(direction="v", gap=2, align="start", children=children)


@ext.panel("looker_settings", slot="center", title="App settings", icon="⚙️", center_overlay=True)
async def looker_settings_panel(ctx, **kwargs) -> object:
    connections = await h._load_connections(ctx)
    audit_children: list[ui.UINode] = [ui.Text("Health snapshot", variant="heading")]
    if connections:
        result = await h.audit_instance_health(ctx, AuditHealthParams(connection_id=connections[0].get("id", "")))
        if result.success and result.data:
            a = result.data
            audit_children.append(ui.Stats(children=[
                ui.Stat(label="Folders", value=str(a.folder_count)),
                ui.Stat(label="Looks", value=str(a.look_count)),
                ui.Stat(label="Dashboards", value=str(a.dashboard_count)),
                ui.Stat(label="Failed scheduled plans (24h)", value=str(a.failed_scheduled_plans_24h)),
                ui.Stat(label="Content validation errors", value=str(a.content_validation_errors)),
            ]))
        else:
            audit_children.append(ui.Text("Could not load health snapshot.", variant="caption"))
    else:
        audit_children.append(ui.Text("Connect an instance to see a health snapshot.", variant="caption"))

    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        _connections_section(connections),
        ui.Divider(),
        ui.Stack(direction="v", gap=2, align="stretch", children=audit_children),
    ])
