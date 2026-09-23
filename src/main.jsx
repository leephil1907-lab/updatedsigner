import React,{useEffect,useMemo,useRef,useState}from'react';
import{createRoot}from'react-dom/client';
import{motion,AnimatePresence}from'motion/react';
import{Activity,ArrowUpRight,Bot,BrainCircuit,ChevronRight,Command,Compass,Database,ExternalLink,FileDiff,Globe2,Layers3,LockKeyhole,Pause,Play,RefreshCw,Search,ServerCog,Settings2,ShieldCheck,Sparkles,Terminal,Workflow,X,Zap}from'lucide-react';
import BlurText from'./reactbits/BlurText.jsx';
import SpotlightCard from'./reactbits/SpotlightCard.jsx';
import'./app.css';

const api=async(path,opt={})=>{const r=await fetch(path,{credentials:'include',headers:{'Content-Type':'application/json',...(opt.headers||{})},...opt});if(!r.ok){let m='Request failed';try{m=(await r.json()).detail||m}catch{}throw Error(m)}return r.status===204?null:r.json()};
const META={
 browser:{name:'Browser Use',type:'WEB EXECUTION',desc:'Real browser navigation, interaction and extraction.',icon:Globe2},
 jev:{name:'Jev',type:'DECISION LAYER',desc:'Live objective routing and decision discovery.',icon:BrainCircuit},
 wow:{name:'WOW-Agent',type:'SUPERVISED HOST',desc:'Visible-screen execution with bounded supervision.',icon:ShieldCheck},
 dify:{name:'Dify',type:'ORCHESTRATION',desc:'Model, tool and workflow orchestration through its API.',icon:Workflow},
 firecrawl:{name:'Firecrawl',type:'WEB INTELLIGENCE',desc:'Search, scrape, map and crawl real web sources.',icon:Search},
 orca:{name:'Orca',type:'PARALLEL AGENTS',desc:'Bridge parallel coding agents and isolated worktrees.',icon:Layers3},
 delta:{name:'Delta',type:'CHANGE EVIDENCE',desc:'Render real Git diffs with syntax-aware presentation.',icon:FileDiff}
};
const ICONS={command:Command,runs:Activity,radar:Compass,receipts:FileDiff,capabilities:ServerCog};

function Ambient(){return <div className="ambient" aria-hidden="true"><div className="gridGlow"/><div className="orb orbA"/><div className="orb orbB"/><div className="orb orbC"/><div className="scanline"/></div>}
function Status({connected}){return <span className={'status '+(connected?'on':'off')}><i/>{connected?'CONNECTED':'NOT CONFIGURED'}</span>}
function PageHead({title,kicker,action}){return <div className="pageHead"><div><div className="eyebrow">{kicker}</div><h1>{title}</h1></div>{action&&<button className="iconBtn" onClick={action}><RefreshCw size={14}/>Refresh</button>}</div>}
function Empty({icon:Icon=Sparkles,title,text}){return <div className="empty"><Icon size={28}/><h3>{title}</h3><p>{text}</p></div>}

function App(){
 const[agents,setAgents]=useState([]),[agent,setAgent]=useState('browser'),[objective,setObjective]=useState(''),[busy,setBusy]=useState(false),[result,setResult]=useState(null),[events,setEvents]=useState([]),[runs,setRuns]=useState([]),[radar,setRadar]=useState([]),[caps,setCaps]=useState([]),[wow,setWow]=useState(null),[view,setView]=useState('command'),[toast,setToast]=useState(''),[palette,setPalette]=useState(false),inputRef=useRef(null);
 const online=agents.filter(a=>a.connected).length;
 const notify=m=>{setToast(m);setTimeout(()=>setToast(''),3000)};
 const refresh=async()=>{try{const h=await api('/api/health');setAgents(h.agents||[])}catch{setAgents([])}};
 const loadRuns=async()=>{try{const d=await api('/api/runs');setRuns(d.items||[])}catch{}};
 const loadRadar=async()=>{try{const d=await api('/api/jev/projects');setRadar(Array.isArray(d)?d:d.items||[])}catch{setRadar([])}};
 const loadCaps=async()=>{try{const d=await api('/api/capabilities');setCaps(d.items||[])}catch{setCaps([])}};
 const loadWow=async()=>{try{setWow(await api('/api/wow/status'))}catch(e){setWow({connected:false,message:e.message})}};
 useEffect(()=>{refresh();loadRuns();loadCaps()},[]);
 useEffect(()=>{if(view==='radar')loadRadar();if(view==='runs')loadRuns();if(view==='receipts')loadWow();if(view==='capabilities')loadCaps()},[view]);
 const execute=async()=>{const text=objective.trim();if(!text){notify('Enter an objective first.');inputRef.current?.focus();return}setBusy(true);setResult(null);setEvents([]);
  try{let d;
   if(agent==='browser')d=await api('/api/browser/run',{method:'POST',body:JSON.stringify({task:text})});
   if(agent==='jev')d=await api('/api/jev/route',{method:'POST',body:JSON.stringify({objective:text})});
   if(agent==='wow')d=await api('/api/wow/activate',{method:'POST',body:JSON.stringify({goal:text})});
   if(agent==='dify')d=await api('/api/dify/run',{method:'POST',body:JSON.stringify({query:text})});
   if(agent==='firecrawl')d=await api('/api/firecrawl/search',{method:'POST',body:JSON.stringify({query:text,limit:5})});
   if(agent==='orca')d=await api('/api/orca/run',{method:'POST',body:JSON.stringify({task:text,prompt:text})});
   if(agent==='delta')throw Error('Delta is an evidence renderer. Provide a real diff to /api/delta/format rather than treating it as an agent.');
   setResult(d);setEvents([META[agent].name+' returned a live gateway result']);notify(META[agent].name+' completed');loadRuns();refresh();loadCaps();
  }catch(e){setResult({error:e.message});setEvents(['ERROR · '+e.message]);notify(e.message)}finally{setBusy(false)}
 };
 const nav=id=>{setView(id);setPalette(false)};
 const selected=META[agent],Icon=selected.icon;
 return <div className="app"><Ambient/>
  <header className="topbar">
   <button className="brand" onClick={()=>nav('command')}><span className="brandmark"><Sparkles size={17}/></span><span><b>Agent Command</b><small>EXECUTION CONTROL PLANE</small></span></button>
   <nav>{[['command','Command'],['runs','Runs'],['radar','Decision Radar'],['receipts','Receipts'],['capabilities','Capabilities']].map(([id,label])=>{const N=ICONS[id];return <button className={view===id?'active':''} onClick={()=>nav(id)} key={id}><N size={13}/>{label}</button>})}</nav>
   <div className="topright"><span className="online"><i/>{online}/{agents.length||7} CONNECTED</span><button className="cmd" onClick={()=>setPalette(true)}><Command size={13}/>K</button></div>
  </header>
  <main>
   {view==='command'&&<section className="page">
    <div className="hero"><div><div className="eyebrow">MULTI-AGENT CONTROL PLANE · 4.0</div><BlurText text="Give it the objective. Keep the evidence." animateBy="words" className="heroTitle" delay={70}/><p>Coordinate real agents, web intelligence, orchestration and engineering evidence from one operational surface. Every status is sourced from a connected runtime.</p><div className="heroChips"><span><ShieldCheck size={12}/>No fabricated state</span><span><LockKeyhole size={12}/>Credentials stay server-side</span><span><Activity size={12}/>Live capability registry</span></div></div><div className="heroVisual"><div className="visualRing r1"/><div className="visualRing r2"/><div className="visualCore"><Sparkles size={34}/></div><div className="visualLabel">OBJECTIVE → EXECUTION → EVIDENCE</div></div></div>
    <div className="agentGrid">{Object.entries(META).map(([id,m])=>{const a=agents.find(x=>x.id===id)||caps.find(x=>x.id===id);const I=m.icon;return <SpotlightCard key={id} className={'agentCard '+(agent===id?'selected':'')} spotlightColor="rgba(112,224,155,.16)"><button onClick={()=>setAgent(id)} className="agentButton"><div className="agentTop"><span className="agentIcon"><I size={18}/></span><span className="agentType">{m.type}</span></div><h3>{m.name}</h3><p>{m.desc}</p><Status connected={!!a?.connected}/></button></SpotlightCard>})}</div>
    <SpotlightCard className="composer" spotlightColor="rgba(112,224,155,.09)"><div className="sectionTop"><div><span className="eyebrow">OBJECTIVE INPUT</span><h2>What needs to happen?</h2></div><span className="shortcut">CTRL / ⌘ + ENTER</span></div><textarea ref={inputRef} value={objective} onChange={e=>setObjective(e.target.value)} onKeyDown={e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter')execute()}} placeholder="Describe the outcome in natural language. No pre-approved action catalogue is injected."/><div className="composerFoot"><div className="routes">{Object.entries(META).map(([id,m])=><button key={id} className={agent===id?'route active':'route'} onClick={()=>setAgent(id)}><m.icon size={12}/>{m.name}</button>)}</div><button className="execute" onClick={execute} disabled={busy}>{busy?<><Activity size={14}/>Executing…</>:<><Zap size={14}/>Execute objective</>}<kbd>↵</kbd></button></div></SpotlightCard>
    <div className="workspace"><SpotlightCard className="livePanel"><div className="sectionTop"><div><span className="eyebrow">LIVE EXECUTION</span><h2>Agent workspace</h2></div><span className={'pill '+(busy?'live':'')}>{busy?'RUNNING':result?'RETURNED':'IDLE'}</span></div>{!result&&!busy?<Empty icon={Icon} title="Awaiting an objective" text="Real agent output, execution events and evidence appear only after a connected runtime is called."/>:<><div className="trace"><span><Icon size={13}/><b>{selected.name}</b></span><span>{busy?'EXECUTING':'RETURNED'}</span></div><pre className="result">{JSON.stringify(result,null,2)}</pre><div className="events">{events.map((e,i)=><div key={i}><ChevronRight size={12}/>{e}</div>)}</div></>}</SpotlightCard>
     <SpotlightCard className="decisionPanel"><div className="sectionTop"><div><span className="eyebrow">CONTROL PLANE</span><h2>Execution context</h2></div><span className="contextIcon"><Icon size={16}/></span></div><div className="decision"><span>SELECTED SURFACE</span><b>{selected.name}</b><p>{selected.desc}</p></div><dl><div><dt>Capability</dt><dd>{selected.type}</dd></div><div><dt>Evidence</dt><dd>{agent==='delta'?'Git diff renderer':'Runtime response + audit record'}</dd></div><div><dt>Authority</dt><dd>{agent==='wow'?'Supervised host':'Gateway policy boundary'}</dd></div></dl><button className="linkBtn" onClick={()=>nav('capabilities')}>Inspect capability registry <ArrowUpRight size={13}/></button></SpotlightCard></div>
   </section>}
   {view==='runs'&&<section className="page"><PageHead title="Runs" kicker="AUDITABLE HISTORY" action={loadRuns}/><div className="table">{runs.length?runs.map(x=><div className="run" key={x.id}><div><b>{x.objective||x.task||'Objective'}</b><small>{x.id}</small></div><span>{x.status||'recorded'}</span><small>{x.agent||''}</small><small>{x.createdAt||''}</small></div>):<Empty title="No runs recorded" text="Execute a real objective to create the first run."/>}</div></section>}
   {view==='radar'&&<section className="page"><PageHead title="Decision Radar" kicker="LIVE JEV DISCOVERY" action={loadRadar}/><div className="cardGrid">{radar.length?radar.map((p,i)=><SpotlightCard className="radarCard" key={p.id||i}><span className="eyebrow">{p.category||'RADAR'}</span><h3>{p.name||p.title||'Untitled'}</h3><p>{p.summary||p.description||''}</p></SpotlightCard>):<Empty icon={Compass} title="Radar not connected" text="Configure JEV_URL or DECISION_RADAR_URL on the gateway to load live discovery."/>}</div></section>}
   {view==='receipts'&&<section className="page"><PageHead title="Receipts" kicker="PROOF & SUPERVISION" action={loadWow}/><div className="receiptGrid"><SpotlightCard><span className="eyebrow">WOW-AGENT</span><h2>Supervision state</h2><div className="state"><span>{wow?.connected?'ONLINE':'OFFLINE'}</span><b>{wow?.state?.mode||'Not connected'}</b><p>{wow?.state?.event||wow?.message||'Connect the real WOW-Agent MCP control plane to expose state.'}</p></div></SpotlightCard><SpotlightCard><span className="eyebrow">OPERATOR BOUNDARIES</span><h2>Execution contract</h2><ul><li><ShieldCheck size={13}/>Visible evidence before state-changing actions</li><li><LockKeyhole size={13}/>Host approval where required</li><li><RefreshCw size={13}/>Fresh verification after state changes</li><li><Pause size={13}/>Ambiguity pauses execution</li><li><Terminal size={13}/>No hidden/private APIs</li></ul></SpotlightCard></div></section>}
   {view==='capabilities'&&<section className="page"><PageHead title="Capabilities" kicker="LIVE INTEGRATION REGISTRY" action={loadCaps}/><div className="capGrid">{agents.map(a=>{const m=META[a.id]||{name:a.name||a.id,type:a.kind||'CAPABILITY',desc:a.detail||'',icon:ServerCog};const I=m.icon;return <SpotlightCard className="capCard" key={a.id}><div className="capIcon"><I size={17}/></div><div><span className="eyebrow">{m.type}</span><h3>{m.name}</h3><p>{a.detail||m.desc}</p><Status connected={!!a.connected}/></div><span className="transport">{a.transport||'runtime'}</span></SpotlightCard>})}</div></section>}
  </main>
  <AnimatePresence>{palette&&<motion.div className="paletteBack" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} onClick={()=>setPalette(false)}><motion.div className="palette" initial={{y:-12,scale:.98}} animate={{y:0,scale:1}} exit={{y:-12,scale:.98}} onClick={e=>e.stopPropagation()}><div className="paletteHead"><span><Command size={15}/>Command palette</span><button onClick={()=>setPalette(false)}><X size={15}/></button></div>{[['command','Command'],['runs','Runs'],['radar','Decision Radar'],['receipts','Receipts'],['capabilities','Capabilities']].map(([id,label])=><button key={id} onClick={()=>nav(id)}><span>{label}</span><ChevronRight size={14}/></button>)}</motion.div></motion.div>}</AnimatePresence>
  {toast&&<div className="toast"><Activity size={13}/>{toast}</div>}
 </div>
}
createRoot(document.getElementById('root')).render(<App/>);