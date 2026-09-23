# Agent Command Center · OpenAI, ChatGPT MCP and OAuth 2.1

The control plane now exposes a real Streamable HTTP MCP endpoint with OAuth 2.1 discovery, PKCE authorization-code flow, JWT access tokens, JWKS, explicit consent, and scoped write access.

## Production environment

Set these on the deployed gateway:

```
OAUTH_ISSUER=https://YOUR-MCP-DOMAIN
OAUTH_RESOURCE=https://YOUR-MCP-DOMAIN
OAUTH_CLIENT_IDS=https://chatgpt.com/oauth/client.json
OPENAI_API_KEY=...
OPENAI_AGENT_MODEL=...
OPENAI_AGENT_REASONING=medium
AGENT_COMMAND_INTERNAL_URL=http://127.0.0.1:8000
CORS_ORIGINS=https://YOUR-MCP-DOMAIN
COOKIE_SECURE=1
MCP_PORT=8001
```

The OAuth signing key is generated once in the persistent `AGENT_CENTER_DATA` directory and reused across restarts. Protect that persistent volume.

## OAuth discovery

The server publishes:

- `/.well-known/oauth-protected-resource`
- `/.well-known/oauth-authorization-server`
- `/oauth/jwks.json`
- `/oauth/authorize`
- `/oauth/token`

The authorization flow uses OAuth 2.1 authorization code + PKCE S256 and echoes the requested `resource` into the access-token audience.

OpenAI's current MCP authentication guidance requires protected-resource metadata, authorization-server metadata, PKCE S256, resource binding, token verification, and scope enforcement for authenticated MCP servers. citeturn1search1

## Scopes

- `mcp:read` — inspect control-plane status, capabilities, runs and objectives.
- `mcp:write` — required for `execute_objective`.

The MCP endpoint requires a valid bearer token. Write calls without `mcp:write` are rejected before the tool executes.

## ChatGPT

Deploy the MCP endpoint at:

`https://YOUR-MCP-DOMAIN/mcp`

Then add that MCP app/connector in ChatGPT Developer Mode. ChatGPT discovers the protected-resource metadata and can run the OAuth authorization-code + PKCE flow. The current OpenAI documentation specifies the stable callback `https://chatgpt.com/connector_platform_oauth_redirect` when the authorization server supports issuer identification. citeturn1search1turn0search2

For production, also enable OpenAI-managed mTLS at the edge if your hosting architecture supports it. OpenAI documents mTLS as an additional way to authenticate ChatGPT as the MCP client; OAuth remains the user authorization mechanism. citeturn0search0

## Other MCP-compatible agents

The same `/mcp` endpoint can be consumed by other MCP clients. They must complete the OAuth flow and receive a token containing the scopes they need.

For OpenAI Agents/API, remote MCP servers are configured with `server_url`; an OAuth access token can be supplied when the server requires authentication. citeturn0search7

## Controlled execution

`execute_objective` is intentionally narrow. It starts the existing objective pipeline rather than exposing arbitrary shell commands or arbitrary HTTP execution.

The execution graph remains:

```
Jev
 ↓
OpenAI Agent
 ↓
Dify
 ├── Firecrawl
 └── Browser Use
      ↓
 WOW-Agent + Orca
      ↓
 Delta
      ↓
 Receipt
```

No demo actions, fake receipts, arbitrary shell execution, or pre-approved objectives are introduced.

## Before public launch

1. Put the gateway behind HTTPS.
2. Set `OAUTH_ISSUER` and `OAUTH_RESOURCE` to the exact canonical MCP origin.
3. Persist `AGENT_CENTER_DATA` so OAuth signing keys and user sessions survive restarts.
4. Test OAuth with MCP Inspector.
5. Test `mcp:read` and `mcp:write` separately.
6. Add rate limits and audit correlation IDs at the edge.
7. Keep write scope disabled for users who should only inspect the system.

OpenAI recommends testing the MCP endpoint with MCP Inspector and enforcing authorization server-side rather than relying on the model to decide whether an action is permitted. citeturn1search0turn1search1
