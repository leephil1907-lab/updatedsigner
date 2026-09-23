# Agent Command Center · OpenAI + MCP

## OpenAI Agent
The gateway has a first-class OpenAI Agents SDK runtime.
Required: `OPENAI_API_KEY`.
Optional: `OPENAI_AGENT_MODEL` (default `gpt-5.6-luna`), `OPENAI_AGENT_REASONING` (default `medium`).

## MCP
`mcp_server.py` uses Streamable HTTP. Standalone endpoint: `/mcp`.
Read-only tools: `get_system_status`, `get_capabilities`, `list_runs`, `list_objectives`, `get_objective`.
State-changing `execute_objective` is disabled unless `MCP_ALLOW_WRITE=1`.

## ChatGPT
Deploy the gateway behind public HTTPS and add its MCP endpoint in ChatGPT Developer Mode / Apps. OpenAI's current integration expects OAuth 2.1 for authenticated private data and write actions. This repository deliberately does not pretend a static bearer token is a production ChatGPT identity system.

Before enabling write actions for ChatGPT, add a real OAuth 2.1 authorization server (Auth0, Supabase/Auth, or another established IdP), protected-resource metadata, PKCE, token verification and per-tool scopes.

## Other agents
Any MCP-compatible agent can consume the same endpoint, keeping the control plane provider-neutral.

## Environment
```
OPENAI_API_KEY=
OPENAI_AGENT_MODEL=gpt-5.6-luna
OPENAI_AGENT_REASONING=medium
AGENT_COMMAND_INTERNAL_URL=http://127.0.0.1:8000
MCP_ALLOW_WRITE=0
MCP_PORT=8001
PUBLIC_MCP_URL=
```
