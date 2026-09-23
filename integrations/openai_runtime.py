"""OpenAI Agents SDK runtime for Agent Command Center.

OpenAI is a first-class reasoning agent here. It can inspect the real control-plane
surfaces through narrowly scoped tools, but it does not get fake state or hidden
credentials.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

try:
    from agents import Agent, Runner, ModelSettings, function_tool
    from openai.types.shared import Reasoning
except Exception:  # dependency may be absent during local development
    Agent = Runner = None
    function_tool = None

GATEWAY_BASE = os.getenv("AGENT_COMMAND_INTERNAL_URL", "http://127.0.0.1:8000").rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_AGENT_MODEL", "gpt-5.6-luna")
OPENAI_REASONING = os.getenv("OPENAI_AGENT_REASONING", "medium")


def status() -> dict[str, Any]:
    configured = bool(os.getenv("OPENAI_API_KEY"))
    installed = Agent is not None and Runner is not None
    return {
        "id": "openai",
        "name": "OpenAI Agent",
        "kind": "REASONING AGENT",
        "connected": configured and installed,
        "transport": "openai-agents-sdk" if installed else "unavailable",
        "detail": (
            f"{OPENAI_MODEL} · Responses API · Agents SDK"
            if configured and installed
            else "Set OPENAI_API_KEY and install openai-agents."
        ),
        "model": OPENAI_MODEL,
    }


async def _get(path: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{GATEWAY_BASE}{path}")
        if response.status_code >= 400:
            raise RuntimeError(f"Gateway returned {response.status_code}: {response.text[:500]}")
        return response.json()


async def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(f"{GATEWAY_BASE}{path}", json=payload)
        if response.status_code >= 400:
            raise RuntimeError(f"Gateway returned {response.status_code}: {response.text[:500]}")
        return response.json()


def _build_agent():
    if Agent is None or Runner is None:
        raise RuntimeError("OpenAI Agents SDK is not installed. Install openai-agents.")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OpenAI is not configured. Set OPENAI_API_KEY.")

    @function_tool
    async def inspect_system() -> str:
        """Inspect the real Agent Command Center capability and connection state."""
        return str(await _get("/api/health"))

    @function_tool
    async def inspect_capabilities() -> str:
        """Inspect the currently configured runtime capabilities."""
        return str(await _get("/api/capabilities"))

    @function_tool
    async def inspect_recent_runs() -> str:
        """Inspect recorded execution runs. Never invent a run that is not returned."""
        return str(await _get("/api/runs"))

    @function_tool
    async def inspect_objectives() -> str:
        """Inspect objective execution records and their real dependency states."""
        return str(await _get("/api/objectives"))

    @function_tool
    async def inspect_receipt(run_id: str) -> str:
        """Inspect one objective receipt by its exact run id."""
        return str(await _get(f"/api/objectives/{run_id}"))

    return Agent(
        name="Command Intelligence",
        model=OPENAI_MODEL,
        instructions="""
You are the reasoning agent inside Agent Command Center.

Treat every connected runtime as a real codebase capability, not a simulated persona.
Never claim an agent is connected unless the control plane reports it connected.
Never fabricate execution, web results, browser actions, code changes, diffs, receipts,
or approvals.

Use the inspection tools when current runtime state matters. Distinguish planning from
execution. The gateway remains the execution authority; your job is to reason, inspect,
route, synthesize and explain.

When a requested capability is unavailable, say exactly which dependency is missing.
Do not silently substitute a fake implementation.

Prefer concise, operational outputs:
1. objective interpretation
2. verified runtime evidence
3. recommended next action
4. limitations or blockers
""",
        tools=[
            inspect_system,
            inspect_capabilities,
            inspect_recent_runs,
            inspect_objectives,
            inspect_receipt,
        ],
        model_settings=ModelSettings(reasoning=Reasoning(effort=OPENAI_REASONING), verbosity="medium"),
    )


async def run(objective: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    objective = str(objective or "").strip()
    if not objective:
        raise ValueError("Objective is required.")

    agent = _build_agent()
    prompt = objective
    if context:
        prompt += "\n\nVerified control-plane context:\n" + str(context)

    result = await Runner.run(agent, prompt)
    return {
        "agent": "OpenAI Agent",
        "model": OPENAI_MODEL,
        "reasoning": OPENAI_REASONING,
        "output": result.final_output,
        "last_agent": getattr(getattr(result, "last_agent", None), "name", "Command Intelligence"),
    }
