"""Real capability adapters for the Agent Command Center.
No simulated responses: an adapter is connected only when its required environment is present.
"""
from __future__ import annotations
import os, shutil, subprocess, time
from typing import Any
import httpx

def _base(name, kind, connected, transport, detail=""):
    return {"id":name,"name":name.replace("_"," ").title(),"kind":kind,"connected":connected,"transport":transport,"detail":detail}

def status():
    return [
      _base("dify","ORCHESTRATION",bool(os.getenv("DIFY_API_KEY") and os.getenv("DIFY_URL")),"http","Agent/workflow API"),
      _base("firecrawl","WEB INTELLIGENCE",bool(os.getenv("FIRECRAWL_API_KEY") and os.getenv("FIRECRAWL_URL","https://api.firecrawl.dev")),"http","Search, scrape, map, crawl"),
      _base("orca","PARALLEL AGENTS",bool(os.getenv("ORCA_URL")),"http","Optional Orca bridge; no fake local status"),
      _base("delta","CHANGE EVIDENCE",bool(shutil.which("delta")),"local","git diff presentation CLI"),
    ]

async def dify_run(payload: dict[str, Any]):
    base=os.getenv("DIFY_URL","").rstrip("/")
    key=os.getenv("DIFY_API_KEY","")
    if not base or not key: raise RuntimeError("Dify is not configured. Set DIFY_URL and DIFY_API_KEY.")
    endpoint=f"{base}/v1/chat-messages"
    body={"inputs":payload.get("inputs",{}),"query":str(payload.get("query","")).strip(),"response_mode":payload.get("response_mode","blocking"),"user":payload.get("user","agent-command-center")}
    if not body["query"]: raise ValueError("query is required")
    if os.getenv("DIFY_APP_ID"): body["inputs"]={**body["inputs"],"_app_id":os.getenv("DIFY_APP_ID")}
    async with httpx.AsyncClient(timeout=180) as c:
        r=await c.post(endpoint,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},json=body)
        if r.status_code>=400: raise RuntimeError(f"Dify returned {r.status_code}: {r.text[:500]}")
        return r.json()

async def firecrawl_action(action: str, payload: dict[str, Any]):
    base=os.getenv("FIRECRAWL_URL","https://api.firecrawl.dev").rstrip("/")
    key=os.getenv("FIRECRAWL_API_KEY","")
    if not key: raise RuntimeError("Firecrawl is not configured. Set FIRECRAWL_API_KEY.")
    paths={"search":"/v2/search","scrape":"/v2/scrape","map":"/v2/map","crawl":"/v2/crawl"}
    if action not in paths: raise ValueError("Unsupported Firecrawl action")
    async with httpx.AsyncClient(timeout=180) as c:
        r=await c.post(base+paths[action],headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},json=payload)
        if r.status_code>=400: raise RuntimeError(f"Firecrawl returned {r.status_code}: {r.text[:500]}")
        return r.json()

async def orca_run(payload: dict[str, Any]):
    base=os.getenv("ORCA_URL","").rstrip("/")
    if not base: raise RuntimeError("Orca bridge is not configured. Set ORCA_URL to a real bridge you control.")
    async with httpx.AsyncClient(timeout=180) as c:
        r=await c.post(f"{base}/api/run",json=payload)
        if r.status_code>=400: raise RuntimeError(f"Orca bridge returned {r.status_code}: {r.text[:500]}")
        return r.json()

def delta_diff(payload: dict[str, Any]):
    if not shutil.which("delta"): raise RuntimeError("delta executable is not installed on the gateway host.")
    cmd=["delta","--paging","never"]
    raw=str(payload.get("diff",""))
    if not raw: raise ValueError("diff is required")
    p=subprocess.run(cmd,input=raw,text=True,capture_output=True,timeout=20,check=False)
    if p.returncode!=0: raise RuntimeError(p.stderr.strip() or "delta failed")
    return {"formatted":p.stdout}
