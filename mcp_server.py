"""Agent Command Center MCP server.

This exposes a deliberately small, truthful tool surface for ChatGPT and other
MCP clients. Read-only inspection is available without user credentials.
State-changing tools are opt-in via MCP_ALLOW_WRITE and should only be enabled
behind proper OAuth or a private trusted network.
"""
from __future__ import annotations
import os
import httpx
from mcp.server.fastmcp import FastMCP

BASE = os.getenv("AGENT_COMMAND_INTERNAL_URL", "http://127.0.0.1:8000").rstrip("/")
ALLOW_WRITE = os.getenv("MCP_ALLOW_WRITE", "0") == "1"
mcp = FastMCP("Agent Command Center", instructions="Use this server to inspect the real Agent Command Center runtime. Never infer unavailable capabilities or fabricate execution state.", stateless_http=True, json_response=True)

async def _get(path: str):
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.get(f"{BASE}{path}")
        if r.status_code>=400: raise RuntimeError(f"Gateway returned {r.status_code}: {r.text[:500]}")
        return r.json()

async def _post(path: str,payload: dict):
    async with httpx.AsyncClient(timeout=180) as client:
        r=await client.post(f"{BASE}{path}",json=payload)
        if r.status_code>=400: raise RuntimeError(f"Gateway returned {r.status_code}: {r.text[:500]}")
        return r.json()

@mcp.tool()
async def get_system_status() -> dict:
    """Return live connection and health state for the control plane."""
    return await _get("/api/health")

@mcp.tool()
async def get_capabilities() -> dict:
    """Return live configured capabilities and their connection state."""
    return await _get("/api/capabilities")

@mcp.tool()
async def list_runs() -> dict:
    """Return recorded execution runs. No sample runs are inserted."""
    return await _get("/api/runs")

@mcp.tool()
async def list_objectives() -> dict:
    """Return real objective execution records and receipts."""
    return await _get("/api/objectives")

@mcp.tool()
async def get_objective(run_id: str) -> dict:
    """Return one objective run by its exact run id."""
    return await _get(f"/api/objectives/{run_id}")

if ALLOW_WRITE:
    @mcp.tool()
    async def execute_objective(objective: str) -> dict:
        """Start a real objective execution through the Agent Command Center."""
        if not objective.strip(): raise ValueError("objective is required")
        return await _post("/api/objectives/run",{"objective":objective})

if __name__=="__main__":
    mcp.run(transport="streamable-http",host="0.0.0.0",port=int(os.getenv("MCP_PORT","8001")))
