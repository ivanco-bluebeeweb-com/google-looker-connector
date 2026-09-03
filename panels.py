"""Panel UI -- connections/connect form + Folders list + center content.

SIDEBAR CONTENT -- NO CARDS, per ~/UI_INTERFACE_STANDARD.md. Every section is
a plain ui.Stack, content stacked vertically and left-aligned, sections
separated by ui.Divider() -- no Card border/background/shadow anywhere.
Disconnect lives in the "App settings" screen (panels_settings.py). The one
secondary "App settings" button is always the LAST element at the bottom.

Form is fully labelled (ui.Text caption + input) and stretched full-width
(align="stretch"). No setup instructions above the form -- that content
lives ONLY in the connect-help modal, never duplicated in the sidebar.

CORRECTED ui.* usage (learned from Qlik Connector's deploy rejection):
ui.Badge takes label+color (not variant); there is no ui.Column (use
ui.Stack direction="v"); ui.Input has no input_type kwarg; ui.DataTable
only accepts columns/rows/on_row_click/on_cell_edit.
"""
from __future__ import annotations

from imperal_sdk import ui

import handlers as h
from app import ext


def _settings_button() -> ui.UINode:
    return ui.Button(
        "App settings", variant="secondary", size="sm", icon="settings", on_click=ui.Call("__panel__looker_settings"),
    )


def _field(label: str, node: ui.UINode) -> ui.UINode:
    return ui.Stack(direction="v", gap=1, children=[ui.Text(label, variant="caption"), node])


def _connect_section() -> ui.UINode:
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("How do I set this up?", variant="ghost", size="sm", icon="HelpCircle",
                  on_click=ui.Call("__panel__looker_connect_help")),
        ui.Button("Sign in with Google Looker (OAuth 2.0)", variant="primary", size="sm", icon="login"),
        ui.Divider(),
        ui.Text("Or connect via API3 Key", variant="caption"),
        ui.Form(
            action="connect_looker",
            submit_label="Verify and connect",
            children=[
                _field("Instance hostname", ui.Input(param_name="instance_hostname", placeholder="e.g. mycompany.looker.com")),
                _field("Client ID", ui.Input(param_name="client_id", placeholder="Admin > Users > Edit Keys")),
                _field("Client secret", ui.Input(param_name="client_secret", placeholder="API3 Key client_secret")),
                _field("Label (optional)", ui.Input(param_name="label", placeholder="e.g. Production instance")),
            ],
        ),
    ])


def _connect_help_body() -> list[ui.UINode]:
    return [
        ui.Text("How to connect Google Looker", variant="heading"),
        ui.Text("1. In Looker, go to Admin > Users, open your own profile (or a service account user), and click 'Edit Keys'.", variant="body"),
        ui.Text("2. Click 'New API3 Key' -- Looker generates a client_id and client_secret pair. Copy both now; the secret is shown only once.", variant="body"),
        ui.Text("3. Your instance hostname is the part before '.looker.com' in your browser's address bar when using Looker -- do not include the API port, it's added automatically.", variant="body"),
        ui.Text("4. Paste both values into the form on the left and press 'Verify and connect'.", variant="body"),
    ]


@ext.panel("looker_connect_help", slot="overlay", title="Connect Google Looker")
async def looker_connect_help(ctx, **kwargs) -> object:
    return ui.Stack(direction="v", gap=2, children=_connect_help_body())


def _folder_row(folder: dict) -> ui.UINode:
    return ui.Stack(direction="v", gap=1, align="start", children=[
        ui.Button(folder.get("name", ""), variant="ghost", size="sm", on_click=ui.Call("__panel__looker_folder", {"folder_id": folder.get("id", "")})),
    ])


@ext.panel("looker_sidebar", slot="left")
async def looker_sidebar(ctx, **kwargs) -> object:
    connections = await h._load_connections(ctx)
    if not connections:
        return ui.Stack(direction="v", align="stretch", gap=3, children=[_connect_section(), ui.Divider(), _settings_button()])

    result = await h.list_folders(ctx, h.ConnectionScopedParams())
    folders = result.data.items if (result.success and result.data) else []

    children: list[ui.UINode] = []
    if not folders:
        children.append(ui.Text("No folders visible to this API3 Key.", variant="caption"))
    else:
        for i, f in enumerate(folders):
            if i > 0:
                children.append(ui.Divider())
            children.append(_folder_row(f.model_dump()))

    return ui.Stack(direction="v", align="stretch", gap=3, children=[
        ui.Stack(direction="v", gap=2, align="stretch", children=children),
        ui.Divider(),
        _settings_button(),
    ])


@ext.panel("looker_folder", slot="center", title="Folder", icon="📁", center_overlay=True)
async def looker_folder_panel(ctx, folder_id: str = "", **kwargs) -> object:
    looks_result = await h.list_looks(ctx, h.ListLooksParams(folder_id=folder_id))
    looks = looks_result.data.items if (looks_result.success and looks_result.data) else []
    dash_result = await h.list_dashboards(ctx, h.ListDashboardsParams(folder_id=folder_id))
    dashboards = dash_result.data.items if (dash_result.success and dash_result.data) else []

    looks_table = ui.DataTable(
        columns=[{"key": "title", "label": "Title"}, {"key": "updated_at", "label": "Updated"}],
        rows=[l.model_dump() for l in looks],
        on_row_click=ui.Call("__panel__looker_look", {"look_id": "{id}"}),
    ) if looks else ui.Text("No Looks in this folder.", variant="caption")

    dash_table = ui.DataTable(
        columns=[{"key": "title", "label": "Title"}, {"key": "updated_at", "label": "Updated"}],
        rows=[d.model_dump() for d in dashboards],
        on_row_click=ui.Call("__panel__looker_dashboard", {"dashboard_id": "{id}"}),
    ) if dashboards else ui.Text("No Dashboards in this folder.", variant="caption")

    return ui.Tabs(tabs=[
        {"label": "Looks", "content": looks_table},
        {"label": "Dashboards", "content": dash_table},
    ])


@ext.panel("looker_look", slot="center", title="Look", icon="🔍", center_overlay=True)
async def looker_look_panel(ctx, look_id: str = "", **kwargs) -> object:
    result = await h.get_look(ctx, h.LookScopedParams(look_id=look_id))
    if not (result.success and result.data):
        return ui.Text(f"Could not load Look: {result.error}", variant="caption")
    l = result.data
    run_result = await h.run_look(ctx, h.RunLookParams(look_id=look_id, result_format="json"))
    rows = run_result.data.rows if (run_result.success and run_result.data) else []
    columns = [{"key": k, "label": k} for k in rows[0].keys()] if rows else []

    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("← Back", variant="ghost", size="sm", on_click=ui.Call("__panel__looker_folder", {"folder_id": l.folder_id})),
        ui.KeyValue(items=[
            {"label": "Model", "value": l.model_name},
            {"label": "Explore", "value": l.explore_name},
            {"label": "Description", "value": l.description or "--"},
        ]),
        ui.Button("Run now", variant="primary", size="sm", on_click=ui.Call("run_look", {"look_id": look_id})),
        ui.DataTable(columns=columns, rows=rows) if rows else ui.Text("No result rows yet -- press 'Run now'.", variant="caption"),
    ])


@ext.panel("looker_dashboard", slot="center", title="Dashboard", icon="📊", center_overlay=True)
async def looker_dashboard_panel(ctx, dashboard_id: str = "", **kwargs) -> object:
    result = await h.get_dashboard(ctx, h.DashboardScopedParams(dashboard_id=dashboard_id))
    if not (result.success and result.data):
        return ui.Text(f"Could not load Dashboard: {result.error}", variant="caption")
    d = result.data
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("← Back", variant="ghost", size="sm", on_click=ui.Call("__panel__looker_sidebar")),
        ui.Text(d.description or "No description.", variant="caption"),
        ui.List(items=[{"title": e.title or "(untitled)", "subtitle": e.type} for e in d.elements]) if d.elements else ui.Text("No elements on this dashboard.", variant="caption"),
    ])