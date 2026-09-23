"""Authenticated MCP server for Agent Command Center.

OAuth is enforced at the HTTP gateway boundary. The MCP server itself remains
provider-neutral so ChatGPT, Codex and other MCP hosts can use the same tools.
"""
from __future__ import annotations
import os
import httpx
from mcp.server.fastmcp import FastMCP

BASE = os.getenv("AGENT_COMMAND_INTERNAL_URL", "http://127.0.0.1:8000").rstrip("/")
mcp = FastMCP(
    "Agent Command Center",
    instructions=(
        "Operate only on verified Agent Command Center state. "
        "Never fabricate execution, credentials, approvals, diffs or receipts."
    ),
    stateless_http=True,
    json_response=True,
)

async def _get(path: str):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{BASE}{path}")
        if r.status_code >= 400:
            raise RuntimeError(f"Gateway returned {r.status_code}: {r.text[:500]}")
        return r.json()

async def _post(path: str, payload: dict):
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(f"{BASE}{path}", json=payload)
        if r.status_code >= 400:
            raise RuntimeError(f"Gateway returned {r.status_code}: {r.text[:500]}")
        return r.json()

@mcp.tool()
async def get_system_status() -> dict:
    """Return live control-plane health and agent connection state."""
    return await _get("/api/health")

@mcp.tool()
async def get_capabilities() -> dict:
    """Return live configured capabilities and connection state."""
    return await _get("/api/capabilities")

@mcp.tool()
async def list_runs() -> dict:
    """Return real recorded execution runs. No sample runs are inserted."""
    return await _get("/api/runs")

@mcp.tool()
async def list_objectives() -> dict:
    """Return real objective execution records and receipts."""
    return await _get("/api/objectives")

@mcp.tool()
async def get_objective(run_id: str) -> dict:
    """Return one objective run by exact run id."""
    return await _get(f"/api/objectives/{run_id}")

@mcp.tool()
async def execute_objective(objective: str) -> dict:
    """Start a real objective execution after the authenticated MCP client has been authorized."""
    if not objective.strip():
        raise ValueError("objective is required")
    return await _post("/api/objectives/run", {"objective": objective})

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=int(os.getenv("MCP_PORT", "8001")))
