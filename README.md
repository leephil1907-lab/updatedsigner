# Agent Command Center

A production-oriented multi-agent control surface combining **Browser Use**, **Jev**, and **WOW-Agent**.

The website deliberately contains **no demo catalogue, simulated browser execution, fabricated results, fake metrics, or pre-approved browser action list**. The UI reflects only connected runtime sources.

## Agent roles

### Browser Use
Real web-browser execution. The gateway can either proxy an existing Browser Use service with `BROWSER_USE_URL` or run the installed Browser Use Python package locally.

### Jev
Decision/routing layer and live Decision Radar. Configure `JEV_URL` (or `DECISION_RADAR_URL`) to a real Jev/Radar HTTP service.

### WOW-Agent
Integrated from [0xkaize/WOW-Agent](https://github.com/0xkaize/WOW-Agent). The integration calls its real `mcp_server.py` control-plane functions when `WOW_AGENT_ROOT` points at a local checkout.

The WOW integration respects that project's visible-screen supervision model: activation, visible evidence, bounded host approval, fresh verification and pause-on-uncertainty. The web UI does not invent gameplay success.

## Run the gateway

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows
# .venv\Scripts\activate

pip install -r requirements.txt
uvicorn gateway:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`.

## Environment

```bash
# Browser Use: choose one
BROWSER_USE_URL=
BROWSER_USE_API_KEY=
BROWSER_USE_MODEL=

# Jev / Decision Radar
JEV_URL=

# WOW-Agent checkout
WOW_AGENT_ROOT=C:\path\to\WOW-Agent

# Optional
AGENT_CENTER_DATA=~/.agent-command-center
CORS_ORIGINS=http://localhost:8000
```

If an agent is not configured, the UI shows it as **DISCONNECTED**. It does not substitute fake data.

## Routes

```text
GET  /api/health
POST /api/browser/run
POST /api/jev/route
GET  /api/jev/projects
POST /api/wow/activate
GET  /api/wow/status
POST /api/wow/plan
POST /api/wow/pause
GET  /api/runs
```

## WOW-Agent integration

The upstream package is designed as a visible-screen supervision kit. Its MCP control plane does not itself launch the game or send unrestricted input; the optional host adapter is responsible for bounded execution and verification.

For the full WOW-Agent setup and safety contract, use the upstream repository documentation rather than copying the project into this repository.

## Deployment

The included Dockerfile runs the gateway. For a browser-only static deployment, publish `index.html`, `styles.css`, and `app.js`; however, real agent execution still requires the gateway or another compatible backend.

Recommended production topology:

```text
Browser
  │
  ▼
Agent Command Center
  │
  ▼
Gateway
  ├── Browser Use
  ├── Jev / Decision Radar
  └── WOW-Agent MCP/control plane
```

Keep all credentials on the gateway. Never put model keys, Jev credentials, or WOW host paths in frontend JavaScript.

## Source integration

- Browser Use: https://github.com/leephil1907-lab/browser-use
- WOW-Agent: https://github.com/0xkaize/WOW-Agent
- Decision discovery: https://github.com/leephil1907-lab/awesome-jev-projects

## Validation

Before production deployment:

```bash
python -m py_compile gateway.py
uvicorn gateway:app --host 127.0.0.1 --port 8000
```

Then verify `/api/health` and test each connected adapter with a real environment. Do not use demo credentials or fake runs as validation evidence.
