"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK. Looker lives inside the user's own Google Cloud Looker instance --
Imperal cannot and should not broker access centrally.

WHY API3 KEY + LOGIN, NOT A GENERIC OAUTH FLOW. Looker's REST API auth model
is client_id+client_secret exchanged via POST /login for a short-lived
(~60min) Bearer access_token -- no refresh token, so on expiry the client
simply re-logs-in with the same client_id/secret. Confirmed in
CONNECTOR_DISCOVERY.md section 3. Simpler than Tableau (no site/session
concept) but still needs the same transparent re-auth pattern.

WHY ONE SECRET HOLDING A JSON ARRAY, SAME PRECEDENT AS Power BI/Tableau/Qlik
Connector. A user may have several instances connected, so connections are
stored as a JSON array of {id, label, instance_hostname, client_id,
client_secret} objects under one declared secret. The live access_token is
cached separately per connection id in looker_client.py, never persisted
here.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "google-looker-connector",
    version="0.1.0",
    display_name="Google Looker",
    description=(
        "Connect your own Google Looker instance (API3 Key) to manage "
        "Looks, Dashboards, Explores and Scheduled Plans from Imperal -- "
        "run ad-hoc queries, trigger scheduled deliveries, and validate "
        "content integrity. Nothing is hosted or proxied by Imperal beyond "
        "the request itself."
    ),
    icon="icon.svg",
    capabilities=["looker:read", "looker:write"],
)

chat = ChatExtension(ext)


@ext.health_check
async def health_check(ctx) -> dict:
    """Report whether at least one Looker instance is connected."""
    raw = await ctx.secrets.get("looker_connections")
    import json
    connections = json.loads(raw) if raw else []
    return {
        "healthy": True,
        "connections": len(connections),
        "detail": f"{len(connections)} Looker instance(s) connected." if connections else "No Looker instance connected yet.",
    }
