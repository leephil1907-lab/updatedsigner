import React from 'react';
import {motion} from 'motion/react';
import {BrandMark} from './branding.js';

const POS=[
 {id:'jev',x:5,y:50},{id:'dify',x:19,y:50},{id:'firecrawl',x:38,y:25},{id:'browser',x:38,y:75},
 {id:'wow',x:62,y:25},{id:'orca',x:62,y:75},{id:'delta',x:86,y:50}
];
const EDGES=[['jev','dify'],['dify','firecrawl'],['dify','browser'],['firecrawl','wow'],['browser','wow'],['firecrawl','orca'],['browser','orca'],['wow','delta'],['orca','delta']];
export default function ExecutionGraph({stages=[],running=false}){
 const by=Object.fromEntries(stages.map(s=>[s.id,s]));
 const state=id=>by[id]?.status||'pending';
 const point=id=>POS.find(p=>p.id===id);
 return <div className="executionGraph" aria-label="Live objective execution graph">
  <svg className="graphEdges" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
   {EDGES.map(([a,b])=>{const p=point(a),q=point(b),active=['running','completed'].includes(state(a));return <motion.line key={a+b} x1={p.x} y1={p.y} x2={q.x} y2={q.y} className={active?'edge active':'edge'} initial={{pathLength:0,opacity:.15}} animate={{pathLength:1,opacity:active?1:.25}} transition={{duration:.5}}/>})}
  </svg>
  {POS.map(p=>{const s=state(p.id);return <motion.div key={p.id} className={'graphNode '+s} style={{left:p.x+'%',top:p.y+'%'}} animate={{scale:s==='running'?1.08:1,z:s==='running'?35:0}} transition={{duration:.3}}>
    <div className="graphNodeMark"><BrandMark id={p.id}/>{s==='running'&&<span className="nodePulse"/>}</div>
    <b>{by[p.id]?.label||p.id}</b>
    <small>{s.toUpperCase()}</small>
    {s==='blocked'&&<em>{by[p.id]?.error||'Blocked by dependency or unavailable capability'}</em>}
   </motion.div>})}
  <div className="graphLegend"><span className={running?'live':''}><i/>{running?'LIVE STATE':'WAITING'}</span><span>Edges activate only after upstream completion</span></div>
 </div>
}
