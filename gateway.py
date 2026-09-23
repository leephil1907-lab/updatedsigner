from __future__ import annotations
import asyncio, importlib.util, json, os, sys, time, uuid, sqlite3, hashlib, secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from integrations.capabilities import status as capability_status, dify_run, firecrawl_action, orca_run, delta_diff
from integrations.openai_runtime import status as openai_status, run as openai_run
try:
    from mcp_server import mcp as mcp_server
except Exception:
    mcp_server = None

ROOT=Path(__file__).resolve().parent
RUNS=Path(os.getenv("AGENT_CENTER_DATA","~/.agent-command-center")).expanduser(); RUNS.mkdir(parents=True,exist_ok=True)
RUN_FILE=RUNS/"runs.jsonl"
OBJECTIVES_FILE=RUNS/"objectives.jsonl"
OBJECTIVES:dict[str,dict[str,Any]]={}
AUTH_DB=RUNS/"auth.sqlite3"
WOW_ROOT=os.getenv("WOW_AGENT_ROOT","").strip()
BROWSER_URL=os.getenv("BROWSER_USE_URL","").rstrip("/")
JEV_URL=(os.getenv("JEV_URL") or os.getenv("DECISION_RADAR_URL") or "").rstrip("/")
@asynccontextmanager
async def app_lifespan(_app):
    if mcp_server is not None:
        async with mcp_server.session_manager.run():
            yield
    else:
        yield

app=FastAPI(title="Agent Command Center Gateway",version="4.1.0",lifespan=app_lifespan)
app.add_middleware(CORSMiddleware,allow_origins=os.getenv("CORS_ORIGINS","*").split(","),allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
FRONTEND=ROOT/"dist"; STATIC_ROOT=FRONTEND if FRONTEND.exists() else ROOT
app.mount("/assets",StaticFiles(directory=STATIC_ROOT/"assets" if (STATIC_ROOT/"assets").exists() else STATIC_ROOT),name="assets")
if mcp_server is not None:
    app.mount("/mcp",mcp_server.streamable_http_app(host="0.0.0.0",stateless_http=True,json_response=True),name="mcp")
_wow=None

def now(): return datetime.now(timezone.utc).isoformat()
def record(x):
    x["createdAt"]=x.get("createdAt") or now()
    with RUN_FILE.open("a",encoding="utf-8") as f:f.write(json.dumps(x,ensure_ascii=False)+"\n")

def wow_module():
    global _wow
    if _wow:return _wow
    if not WOW_ROOT:return None
    p=Path(WOW_ROOT)/"mcp_server.py"
    if not p.exists():return None
    spec=importlib.util.spec_from_file_location("wow_agent_mcp_server",p)
    if not spec or not spec.loader:return None
    m=importlib.util.module_from_spec(spec); sys.path.insert(0,str(Path(WOW_ROOT))); spec.loader.exec_module(m); _wow=m; return m

def wow_status():
    m=wow_module()
    if not m:return {"connected":False,"message":"WOW_AGENT_ROOT is not configured or mcp_server.py is unavailable."}
    try:return {"connected":True,**m.status()}
    except Exception as e:return {"connected":False,"message":str(e)}


def objective_snapshot(run_id:str):
    if run_id in OBJECTIVES: return OBJECTIVES[run_id]
    if OBJECTIVES_FILE.exists():
        for line in OBJECTIVES_FILE.read_text(encoding="utf-8").splitlines():
            try:
                x=json.loads(line)
                if x.get("id")==run_id: OBJECTIVES[run_id]=x
            except Exception: pass
    return OBJECTIVES.get(run_id)

def persist_objective(run):
    OBJECTIVES[run["id"]]=run
    with OBJECTIVES_FILE.open("a",encoding="utf-8") as f:f.write(json.dumps(run,ensure_ascii=False)+"\n")

GRAPH=[
    {"id":"jev","label":"Jev","kind":"decision","depends":[]},
    {"id":"openai","label":"OpenAI Agent","kind":"reasoning","depends":["jev"]},
    {"id":"dify","label":"Dify","kind":"orchestration","depends":["openai"]},
    {"id":"firecrawl","label":"Firecrawl","kind":"web","depends":["dify"]},
    {"id":"browser","label":"Browser Use","kind":"browser","depends":["dify"]},
    {"id":"wow","label":"WOW-Agent","kind":"supervision","depends":["firecrawl","browser"]},
    {"id":"orca","label":"Orca","kind":"parallel","depends":["firecrawl","browser"]},
    {"id":"delta","label":"Delta","kind":"evidence","depends":["wow","orca"]},
]

def _stage(run,stage_id,status,**extra):
    s=next(x for x in run["stages"] if x["id"]==stage_id)
    s["status"]=status;s["updatedAt"]=now();s.update(extra)
    run["updatedAt"]=now();persist_objective(run)

async def _graph_call(run,stage_id,label,fn):
    _stage(run,stage_id,"running",label=label,startedAt=now())
    try:
        result=await fn()
        _stage(run,stage_id,"completed",finishedAt=now(),result=result)
        return result
    except Exception as e:
        _stage(run,stage_id,"blocked",finishedAt=now(),error=str(e))
        return None

async def _execute_objective(run_id):
    run=objective_snapshot(run_id)
    if not run:return
    run["status"]="running";run["startedAt"]=now();persist_objective(run)
    try:
        text=run["objective"]
        route=await _graph_call(run,"jev","Jev · objective routing",lambda: jev_route({"objective":text}))
        if route is None:
            for sid in ["openai","dify","firecrawl","browser","wow","orca","delta"]: _stage(run,sid,"blocked",finishedAt=now(),error="Blocked by failed Jev dependency.")
            run["status"]="blocked";run["finishedAt"]=now();persist_objective(run);return
        reasoning=await _graph_call(run,"openai","OpenAI Agent · reasoning",lambda: openai_run(text,{"jev":route}))
        if reasoning is None:
            for sid in ["dify","firecrawl","browser","wow","orca","delta"]: _stage(run,sid,"blocked",finishedAt=now(),error="Blocked by failed OpenAI Agent dependency.")
            run["status"]="blocked";run["finishedAt"]=now();persist_objective(run);return
        orch=await _graph_call(run,"dify","Dify · orchestration",lambda: dify({"query":text,"inputs":{"objective":text,"decision":route,"openai":reasoning}}))
        if orch is None:
            for sid in ["firecrawl","browser","wow","orca","delta"]: _stage(run,sid,"blocked",finishedAt=now(),error="Blocked by failed Dify dependency.")
            run["status"]="blocked";run["finishedAt"]=now();persist_objective(run);return
        fire_task=_graph_call(run,"firecrawl","Firecrawl · web intelligence",lambda: firecrawl("search",{"query":text,"limit":5}))
        browser_task=_graph_call(run,"browser","Browser Use · browser execution",lambda: browser_run({"task":text}))
        web,browser=await asyncio.gather(fire_task,browser_task)
        if web is None or browser is None:
            for sid in ["wow","orca","delta"]:
                if next(x for x in run["stages"] if x["id"]==sid)["status"]=="pending": _stage(run,sid,"blocked",finishedAt=now(),error="Blocked by incomplete web/browser dependency.")
            run["status"]="blocked";run["finishedAt"]=now();persist_objective(run);return
        wow_task=_graph_call(run,"wow","WOW-Agent · supervised execution",lambda: wow_activate({"goal":text,"launch_hud":True}))
        orca_task=_graph_call(run,"orca","Orca · parallel runtime",lambda: orca({"task":text,"prompt":text,"context":{"route":route,"orchestration":orch,"web":web,"browser":browser}}))
        wow,orca_result=await asyncio.gather(wow_task,orca_task)
        if wow is None or orca_result is None:
            _stage(run,"delta","blocked",finishedAt=now(),error="Blocked by incomplete WOW-Agent/Orca dependency.")
            run["status"]="blocked";run["finishedAt"]=now();persist_objective(run);return
        _stage(run,"delta","running",label="Delta · evidence boundary",startedAt=now())
        diff=run.get("diff") or ""
        if not diff:
            _stage(run,"delta","not_applicable",finishedAt=now(),error="No repository diff supplied; Delta did not fabricate evidence.")
            evidence={"mode":"runtime-receipt","sources":[x["id"] for x in run["stages"] if x.get("status")=="completed"],"note":"No Git diff was supplied, so the receipt contains runtime evidence only."}
        else:
            evidence=delta_diff({"diff":diff})
            _stage(run,"delta","completed",finishedAt=now(),result=evidence)
        run["status"]="completed";run["finishedAt"]=now()
        run["receipt"]={"status":"completed","objective":text,"stages":run["stages"],"evidence":evidence,"completedAt":run["finishedAt"]}
        persist_objective(run)
    except Exception as e:
        run["status"]="failed";run["error"]=str(e);run["finishedAt"]=now();persist_objective(run)

@app.post("/api/objectives/run")
async def objective_run(payload:dict[str,Any]):
    objective=str(payload.get("objective","")).strip()
    if not objective: raise HTTPException(422,detail="Objective is required.")
    run_id="objective-"+uuid.uuid4().hex[:12]
    run={"id":run_id,"objective":objective,"status":"queued","createdAt":now(),"updatedAt":now(),"stages":[
        {"id":x["id"],"label":x["label"],"kind":x["kind"],"depends":x["depends"],"status":"pending"} for x in GRAPH
    ],"receipt":None,"diff":payload.get("diff")}
    persist_objective(run)
    asyncio.create_task(_execute_objective(run_id))
    return {"id":run_id,"status":"queued","graph":GRAPH}

@app.get("/api/objectives/{run_id}")
async def objective_get(run_id:str):
    run=objective_snapshot(run_id)
    if not run: raise HTTPException(404,detail="Objective run not found.")
    return run

@app.get("/api/objectives")
async def objectives():
    if OBJECTIVES_FILE.exists():
        for line in OBJECTIVES_FILE.read_text(encoding="utf-8").splitlines():
            try:
                x=json.loads(line);OBJECTIVES[x["id"]]=x
            except Exception: pass
    return {"items":sorted(OBJECTIVES.values(),key=lambda x:x.get("createdAt",""),reverse=True)}

def auth_db():
    x=sqlite3.connect(AUTH_DB);x.row_factory=sqlite3.Row
    x.execute("CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,name TEXT NOT NULL,created_at TEXT NOT NULL)")
    x.execute("CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT NOT NULL,created_at TEXT NOT NULL)")
    x.commit();return x
def hash_password(password,salt=None):
    salt=salt or secrets.token_hex(16);return salt+"$"+hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),160000).hex()
def valid_password(password,stored):
    salt,value=stored.split("$",1);return secrets.compare_digest(value,hash_password(password,salt).split("$",1)[1])
def auth_user(req:Request):
    token=req.cookies.get("agent_session")
    if not token:return None
    with auth_db() as x:r=x.execute("SELECT u.id,u.email,u.name,u.created_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?",(token,)).fetchone()
    return dict(r) if r else None
def public_user(u):return {"id":u["id"],"email":u["email"],"name":u["name"],"createdAt":u["created_at"]}

@app.post("/api/auth/signup")
async def auth_signup(payload:dict[str,Any],response:Response):
    email=str(payload.get("email","")).strip().lower();password=str(payload.get("password",""));name=str(payload.get("name","")).strip()
    if not name or "@" not in email or len(password)<8:raise HTTPException(422,detail="Name, valid email and password of at least 8 characters are required.")
    uid="usr_"+secrets.token_hex(10);token=secrets.token_urlsafe(32)
    try:
        with auth_db() as x:x.execute("INSERT INTO users VALUES(?,?,?,?,?)",(uid,email,hash_password(password),name,now()));x.execute("INSERT INTO sessions VALUES(?,?,?)",(token,uid,now()));x.commit()    except sqlite3.IntegrityError:raise HTTPException(409,detail="An account with this email already exists.")
    response.set_cookie("agent_session",token,httponly=True,samesite="lax",secure=os.getenv("COOKIE_SECURE","0")=="1",max_age=2592000)
    return {"user":public_user({"id":uid,"email":email,"name":name,"created_at":now()})}

@app.post("/api/auth/login")
async def auth_login(payload:dict[str,Any],response:Response):
    email=str(payload.get("email","")).strip().lower();password=str(payload.get("password",""))
    with auth_db() as x:r=x.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
    if not r or not valid_password(password,r["password_hash"]):raise HTTPException(401,detail="Invalid email or password.")
    token=secrets.token_urlsafe(32)
    with auth_db() as x:x.execute("INSERT INTO sessions VALUES(?,?,?)",(token,r["id"],now()));x.commit()
    response.set_cookie("agent_session",token,httponly=True,samesite="lax",secure=os.getenv("COOKIE_SECURE","0")=="1",max_age=2592000)
    return {"user":public_user(r)}

@app.post("/api/auth/logout")
async def auth_logout(req:Request,response:Response):
    token=req.cookies.get("agent_session")
    if token:
        with auth_db() as x:x.execute("DELETE FROM sessions WHERE token=?",(token,));x.commit()
    response.delete_cookie("agent_session");return {"ok":True}

@app.get("/api/auth/me")
async def auth_me(req:Request):
    u=auth_user(req);return {"authenticated":bool(u),"user":public_user(u) if u else None}

@app.post("/api/auth/forgot")
async def auth_forgot(payload:dict[str,Any]):
    email=str(payload.get("email","")).strip().lower()
    with auth_db() as x:r=x.execute("SELECT id FROM users WHERE email=?",(email,)).fetchone()
    return {"ok":True,"message":"If an account exists for that email, reset instructions will be sent."}

@app.get("/api/profile")
async def profile(req:Request):
    u=auth_user(req)
    if not u:raise HTTPException(401,detail="Authentication required.")
    return {"user":public_user(u)}

@app.get("/api/integrations")
async def integrations(req:Request):
    if not auth_user(req):raise HTTPException(401,detail="Authentication required.")
    return {"connections":capability_status(),"skills":[{"id":"objective-orchestration","name":"Objective Orchestration","source":"native"},{"id":"openai-reasoning","name":"OpenAI Reasoning Agent","source":"OpenAI Agents SDK"},{"id":"mcp-interface","name":"MCP Agent Interface","source":"Model Context Protocol"},{"id":"web-intelligence","name":"Web Intelligence","source":"Firecrawl"},{"id":"browser-execution","name":"Browser Execution","source":"Browser Use"},{"id":"supervised-execution","name":"Supervised Execution","source":"WOW-Agent"},{"id":"parallel-runtime","name":"Parallel Runtime","source":"Orca"},{"id":"evidence-rendering","name":"Git Evidence","source":"Delta"}]}
@app.get("/")
async def root(): return FileResponse(STATIC_ROOT/"index.html")

@app.get("/api/health")
async def health():
    wow=wow_status()
    caps=capability_status()
    return {"status":"ok","version":"4.0.0","agents":[
      {"id":"browser","name":"Browser Use","connected":bool(BROWSER_URL or _browser_local_available()),"transport":"http" if BROWSER_URL else "local"},
      openai_status(),
      {"id":"jev","name":"Jev","connected":bool(JEV_URL),"transport":"http"},
      {"id":"wow","name":"WOW-Agent","connected":bool(wow.get("connected")),"transport":"local-mcp"},
      *caps]}

@app.get("/api/capabilities")
async def capabilities(): return {"items":[*capability_status(),openai_status()]}

def _browser_local_available():
    try: import browser_use; return True
    except Exception: return False

async def _browser_local(payload):
    try:
        from browser_use import Agent, Browser, ChatBrowserUse
        from browser_use.llm.models import get_llm_by_name
    except Exception as e: raise HTTPException(503,detail="Browser Use Python package is not installed; set BROWSER_USE_URL or install browser-use.") from e
    task=str(payload.get("task","")).strip()
    if not task: raise HTTPException(422,detail="Task is required.")
    llm_name=os.getenv("BROWSER_USE_MODEL","").strip()
    if not llm_name and not os.getenv("BROWSER_USE_API_KEY"): raise HTTPException(503,detail="No Browser Use model credentials are configured.")
    llm=get_llm_by_name(llm_name) if llm_name else ChatBrowserUse()
    browser=Browser(use_cloud=bool(payload.get("cloud")))
    try:
        agent=Agent(task=task,llm=llm,browser=browser); history=await agent.run()
        actions=[]
        for item in getattr(history,"history",[]):
            out=getattr(item,"model_output",None)
            for action in getattr(out,"action",[]) if out else []: actions.append(action.model_dump(exclude_none=True,mode="json"))
        return {"id":"browser-"+str(int(time.time()*1000)),"agent":"Browser Use","result":history.final_result(),"successful":history.is_successful(),"browser":{"actions":actions}}
    finally:
        try: await browser.close()
        except Exception: pass

@app.post("/api/browser/run")
async def browser_run(payload:dict[str,Any]):
    if BROWSER_URL:
        async with httpx.AsyncClient(timeout=180) as c:
            r=await c.post(f"{BROWSER_URL}/api/agent/run",json=payload)
            if r.status_code>=400: raise HTTPException(r.status_code,detail=r.text[:500])
            d=r.json()
    else:d=await _browser_local(payload)
    record({"id":d.get("id"),"agent":"Browser Use","objective":payload.get("task"),"status":"completed" if d.get("successful") is not False else "failed"})
    return d

@app.post("/api/wow/activate")
async def wow_activate(payload:dict[str,Any]):
    m=wow_module()
    if not m: raise HTTPException(503,detail="WOW-Agent is not connected. Configure WOW_AGENT_ROOT.")
    try:d=m.activate(str(payload.get("goal","")).strip(),launch_hud=bool(payload.get("launch_hud",True)),harness="Agent Command Center")
    except Exception as e: raise HTTPException(500,detail=str(e))
    record({"id":"wow-"+str(int(time.time()*1000)),"agent":"WOW-Agent","objective":payload.get("goal"),"status":"activated"}); return d

@app.get("/api/wow/status")
async def wow_get_status(): return wow_status()

@app.post("/api/wow/pause")
async def wow_pause(payload:dict[str,Any]):
    m=wow_module()
    if not m: raise HTTPException(503,detail="WOW-Agent is not connected.")
    return m.pause(str(payload.get("reason","Operator pause")))

@app.post("/api/wow/plan")
async def wow_plan(payload:dict[str,Any]):
    m=wow_module()
    if not m: raise HTTPException(503,detail="WOW-Agent is not connected.")
    return m.plan(**payload)

@app.post("/api/jev/route")
async def jev_route(payload:dict[str,Any]):
    if not JEV_URL: raise HTTPException(503,detail="Jev is not configured. Set JEV_URL.")
    async with httpx.AsyncClient(timeout=30) as c:
        r=await c.post(f"{JEV_URL}/decision/select",json=payload)
        if r.status_code>=400: raise HTTPException(r.status_code,detail=r.text[:500])
        d=r.json()
    record({"id":"jev-"+str(int(time.time()*1000)),"agent":"Jev","objective":payload.get("objective"),"status":"routed"}); return d

@app.get("/api/jev/projects")
async def jev_projects(q:str|None=None,category:str|None=None):
    if not JEV_URL: raise HTTPException(503,detail="Jev/Radar is not configured.")
    params={k:v for k,v in {"q":q,"category":category}.items() if v}
    async with httpx.AsyncClient(timeout=20) as c:
        r=await c.get(f"{JEV_URL}/projects",params=params)
        if r.status_code>=400: raise HTTPException(r.status_code,detail=r.text[:500])
        return r.json()

@app.post("/api/dify/run")
async def dify(payload:dict[str,Any]):
    try:d=await dify_run(payload)
    except (RuntimeError,ValueError) as e: raise HTTPException(503,detail=str(e))
    record({"id":"dify-"+str(int(time.time()*1000)),"agent":"Dify","objective":payload.get("query"),"status":"completed"}); return d

@app.post("/api/firecrawl/{action}")
async def firecrawl(action:str,payload:dict[str,Any]):
    try:d=await firecrawl_action(action,payload)
    except (RuntimeError,ValueError) as e: raise HTTPException(503,detail=str(e))
    record({"id":"firecrawl-"+str(int(time.time()*1000)),"agent":"Firecrawl","objective":payload.get("query") or payload.get("url"),"status":"completed"}); return d

@app.post("/api/orca/run")
async def orca(payload:dict[str,Any]):
    try:d=await orca_run(payload)
    except (RuntimeError,ValueError) as e: raise HTTPException(503,detail=str(e))
    record({"id":"orca-"+str(int(time.time()*1000)),"agent":"Orca","objective":payload.get("prompt") or payload.get("task"),"status":"completed"}); return d

@app.post("/api/delta/format")
async def delta(payload:dict[str,Any]):
    try:return delta_diff(payload)
    except (RuntimeError,ValueError) as e: raise HTTPException(503,detail=str(e))\n\n@app.post("/api/openai/run")\nasync def openai_route(payload:dict[str,Any],req:Request):\n    if not auth_user(req): raise HTTPException(401,detail="Authentication required.")\n    objective=str(payload.get("objective") or payload.get("query") or "").strip()\n    if not objective: raise HTTPException(422,detail="Objective is required.")\n    try:\n        result=await openai_run(objective,payload.get("context"))\n    except (RuntimeError,ValueError) as e:\n        raise HTTPException(503,detail=str(e))\n    record({"id":"openai-"+str(int(time.time()*1000)),"agent":"OpenAI Agent","objective":objective,"status":"completed","model":result.get("model")})\n    return result

@app.get("/api/runs")
async def runs():
    if not RUN_FILE.exists(): return {"items":[]}
    latest={}
    for line in RUN_FILE.read_text(encoding="utf-8").splitlines():
        try:
            x=json.loads(line); latest[x.get("id")]=x
        except Exception: pass
    return {"items":list(reversed(list(latest.values())))}