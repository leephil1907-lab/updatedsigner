from __future__ import annotations
import importlib.util, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT=Path(__file__).resolve().parent
RUNS=Path(os.getenv("AGENT_CENTER_DATA","~/.agent-command-center")).expanduser()
RUNS.mkdir(parents=True,exist_ok=True)
RUN_FILE=RUNS/"runs.jsonl"
WOW_ROOT=os.getenv("WOW_AGENT_ROOT","").strip()
BROWSER_URL=os.getenv("BROWSER_USE_URL","").rstrip("/")
JEV_URL=(os.getenv("JEV_URL") or os.getenv("DECISION_RADAR_URL") or "").rstrip("/")
app=FastAPI(title="Agent Command Center Gateway",version="2.0.0")
app.add_middleware(CORSMiddleware,allow_origins=os.getenv("CORS_ORIGINS","*").split(","),allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.mount("/assets",StaticFiles(directory=ROOT),name="assets")
_wow=None
def now(): return datetime.now(timezone.utc).isoformat()
def record(x):
 x["createdAt"]=x.get("createdAt") or now()
 with RUN_FILE.open("a",encoding="utf-8") as f:f.write(json.dumps(x,ensure_ascii=False)+"\n")
def wow_module():
 global _wow
 if _wow:return _wow
 if not WOW_ROOT: return None
 p=Path(WOW_ROOT)/"mcp_server.py"
 if not p.exists():return None
 spec=importlib.util.spec_from_file_location("wow_agent_mcp_server",p)
 if not spec or not spec.loader:return None
 m=importlib.util.module_from_spec(spec);sys.path.insert(0,str(Path(WOW_ROOT)))
 spec.loader.exec_module(m);_wow=m;return m
def wow_status():
 m=wow_module()
 if not m:return {"connected":False,"message":"WOW_AGENT_ROOT is not configured or mcp_server.py is unavailable."}
 try:return {"connected":True,**m.status()}
 except Exception as e:return {"connected":False,"message":str(e)}
@app.get("/")
async def root():return FileResponse(ROOT/"index.html")
@app.get("/api/health")
async def health():
 return {"status":"ok","agents":[{"id":"browser","connected":bool(BROWSER_URL or _browser_local_available()),"transport":"http" if BROWSER_URL else "local"},{"id":"jev","connected":bool(JEV_URL),"transport":"http"},{"id":"wow","connected":bool(wow_status().get("connected")),"transport":"local-mcp"}]}
def _browser_local_available():
 try:
  import browser_use
  return True
 except Exception:return False
async def _browser_local(payload):
 try:
  from browser_use import Agent,Browser,ChatBrowserUse
  from browser_use.llm.models import get_llm_by_name
  from browser_use import Browser
 except Exception as e:raise HTTPException(503,detail="Browser Use Python package is not installed; set BROWSER_USE_URL or install browser-use.") from e
 task=str(payload.get("task","")).strip()
 if not task:raise HTTPException(422,detail="Task is required.")
 llm_name=os.getenv("BROWSER_USE_MODEL","").strip()
 if not llm_name and not os.getenv("BROWSER_USE_API_KEY"):raise HTTPException(503,detail="No Browser Use model credentials are configured.")
 llm=get_llm_by_name(llm_name) if llm_name else ChatBrowserUse()
 browser=Browser(use_cloud=bool(payload.get("cloud")))
 try:
  agent=Agent(task=task,llm=llm,browser=browser);history=await agent.run()
  actions=[]
  for item in getattr(history,"history",[]):
   out=getattr(item,"model_output",None)
   for action in getattr(out,"action",[]) if out else []:actions.append(action.model_dump(exclude_none=True,mode="json"))
  return {"id":"browser-"+str(int(time.time()*1000)),"agent":"Browser Use","result":history.final_result(),"successful":history.is_successful(),"browser":{"actions":actions}}
 finally:
  try:await browser.close()
  except Exception:pass
@app.post("/api/browser/run")
async def browser_run(payload:dict[str,Any]):
 if BROWSER_URL:
  async with httpx.AsyncClient(timeout=180) as c:
   r=await c.post(f"{BROWSER_URL}/api/agent/run",json=payload)
   if r.status_code>=400:raise HTTPException(r.status_code,detail=r.text[:500])
   d=r.json()
 else:d=await _browser_local(payload)
 record({"id":d.get("id"),"agent":"Browser Use","objective":payload.get("task"),"status":"completed" if d.get("successful") is not False else "failed"})
 return d
@app.post("/api/wow/activate")
async def wow_activate(payload:dict[str,Any]):
 m=wow_module()
 if not m:raise HTTPException(503,detail="WOW-Agent is not connected. Configure WOW_AGENT_ROOT.")
 try:d=m.activate(str(payload.get("goal","")).strip(),launch_hud=bool(payload.get("launch_hud",True)),harness="Agent Command Center")
 except Exception as e:raise HTTPException(500,detail=str(e))
 record({"id":"wow-"+str(int(time.time()*1000)),"agent":"WOW-Agent","objective":payload.get("goal"),"status":"activated"})
 return d
@app.get("/api/wow/status")
async def wow_get_status():return wow_status()
@app.post("/api/wow/pause")
async def wow_pause(payload:dict[str,Any]):
 m=wow_module()
 if not m:raise HTTPException(503,detail="WOW-Agent is not connected.")
 return m.pause(str(payload.get("reason","Operator pause")))
@app.post("/api/wow/plan")
async def wow_plan(payload:dict[str,Any]):
 m=wow_module()
 if not m:raise HTTPException(503,detail="WOW-Agent is not connected.")
 return m.plan(**payload)
@app.post("/api/jev/route")
async def jev_route(payload:dict[str,Any]):
 if not JEV_URL:raise HTTPException(503,detail="Jev is not configured. Set JEV_URL.")
 async with httpx.AsyncClient(timeout=30) as c:
  r=await c.post(f"{JEV_URL}/decision/select",json=payload)
  if r.status_code>=400:raise HTTPException(r.status_code,detail=r.text[:500])
  d=r.json()
 record({"id":"jev-"+str(int(time.time()*1000)),"agent":"Jev","objective":payload.get("objective"),"status":"routed"})
 return d
@app.get("/api/jev/projects")
async def jev_projects(q:str|None=None,category:str|None=None):
 if not JEV_URL:raise HTTPException(503,detail="Jev/Radar is not configured.")
 params={k:v for k,v in {"q":q,"category":category}.items() if v}
 async with httpx.AsyncClient(timeout=20) as c:
  r=await c.get(f"{JEV_URL}/projects",params=params)
  if r.status_code>=400:raise HTTPException(r.status_code,detail=r.text[:500])
  return r.json()
@app.get("/api/runs")
async def runs():
 if not RUN_FILE.exists():return {"items":[]}
 latest={}
 for line in RUN_FILE.read_text(encoding="utf-8").splitlines():
  try:
   x=json.loads(line);latest[x.get("id")]=x
  except Exception:pass
 return {"items":list(reversed(list(latest.values())))}