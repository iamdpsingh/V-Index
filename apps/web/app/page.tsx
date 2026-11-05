'use client';
import { FormEvent, useEffect, useState } from 'react';

type Provenance = {source_id:number; source_url:string; application_url:string; status:string; last_checked_at:string};
type Job = {id:number; title:string; company:string; location:string; description:string; application_url:string; employment_type:string|null; remote_status:string|null; sources:Provenance[]};
type Results = {total:number; items:Job[]; limit:number; offset:number};
type Provider = {name:string; kind:string; implementation_status:string; evidence_status:string; extraction_count:number|null; last_run_at:string|null; limitations:string[]; failure_reason:string|null};
type Source = {id:number; company:string; provider:string; slug:string; url:string; failures:number; next_check:string};
type Run = {id:number; source_id:number; status:string; count:number; error:string|null; started_at:string};
async function request<T>(path:string, token='', init:RequestInit={}):Promise<T> {
  const response=await fetch(`/api/v1/${path}`, {...init, headers:{'Content-Type':'application/json', ...(token ? {'Authorization':`Bearer ${token}`} : {}), ...init.headers}});
  if(!response.ok) { const body=await response.json().catch(()=>({})); throw new Error(typeof body.detail==='string' ? body.detail : `Request failed (${response.status})`); }
  return response.json();
}
function when(value:string|null) { return value ? new Date(value).toLocaleString() : 'Never'; }
function label(value:string) { return value.toLowerCase().replaceAll('_',' '); }
export default function Home() {
  const [tab,setTab]=useState('jobs');
  const [results,setResults]=useState<Results>({total:0,items:[],limit:25,offset:0});
  const [providers,setProviders]=useState<Provider[]>([]);
  const [filters,setFilters]=useState({keyword:'',company:'',location:''});
  const [applied,setApplied]=useState(filters);
  const [offset,setOffset]=useState(0);
  const [selected,setSelected]=useState<Job|null>(null);
  const [busy,setBusy]=useState(true);
  const [error,setError]=useState('');
  const [token,setToken]=useState('');
  const [sources,setSources]=useState<Source[]>([]);
  const [runs,setRuns]=useState<Run[]>([]);
  const [source,setSource]=useState({url:'',company:''});
  const [message,setMessage]=useState('');
  const [adminBusy,setAdminBusy]=useState(false);
  useEffect(()=>{ let active=true; setBusy(true); setError('');
    request<Results>(`jobs?${new URLSearchParams({...applied,limit:'25',offset:String(offset)})}`)
      .then(data=>{if(active)setResults(data);}).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setBusy(false);});
    return ()=>{active=false;};
  },[applied,offset]);
  useEffect(()=>{request<Provider[]>('providers').then(setProviders).catch(e=>setError(e.message));},[]);
  async function loadSources() {
    setError(''); setAdminBusy(true);
    try { const [s,r]=await Promise.all([request<Source[]>('sources',token), request<Run[]>('runs',token)]); setSources(s);setRuns(r); }
    catch(e){setError((e as Error).message);} finally{setAdminBusy(false);}
  }
  async function addSource(event:FormEvent) {
    event.preventDefault(); setAdminBusy(true);setError('');setMessage('');
    try { await request('sources',token,{method:'POST',body:JSON.stringify(source)});setMessage('Source added. The worker will pick it up on its next cycle.');setSource({url:'',company:''});await loadSources(); }
    catch(e){setError((e as Error).message);} finally{setAdminBusy(false);}
  }
  async function refresh(id:number) {
    setAdminBusy(true);setError('');setMessage('');
    try{await request(`sources/${id}/refresh`,token,{method:'POST'});setMessage('Refresh scheduled. Reload status after the worker completes.');await loadSources();}
    catch(e){setError((e as Error).message);}finally{setAdminBusy(false);}
  }
  const verified=providers.filter(p=>p.evidence_status==='LIVE_VERIFIED').length;
  return <><header><a className="wordmark" href="/">V<span>—</span>Index</a><span className="header-note">A source-first job index</span><nav aria-label="Main navigation">{['jobs','sources','coverage'].map(name=><button key={name} aria-current={tab===name?'page':undefined} onClick={()=>{setTab(name);setError('');}}>{name}</button>)}</nav></header>
  <main><div className="eyebrow">THE INDEX / {tab.toUpperCase()}</div><section className="intro"><div><h1>{tab==='jobs'?'Find your next opening.':tab==='sources'?'Keep the index current.':'Coverage, with evidence.'}</h1><p>{tab==='jobs'?'Real openings. Original sources. A clearer place to search.':tab==='sources'?'Add a supported hosted career board and inspect its refresh history.':'Implementation and live verification are tracked separately for every required platform.'}</p></div><div className="index-note"><span className="dot"/>{verified} / {providers.length||'—'} platforms live-checked<small>Point-in-time evidence · initial release</small></div></section>
  {error&&<div className="notice error" role="alert">{error}</div>}
  {tab==='jobs'&&<><form className="search" onSubmit={e=>{e.preventDefault();setOffset(0);setApplied({...filters});setSelected(null);}}>{(['keyword','company','location'] as const).map(key=><label key={key}>{key}<input value={filters[key]} placeholder={key==='keyword'?'Title or description':key==='company'?'Any company':'Any location'} onChange={e=>setFilters({...filters,[key]:e.target.value})}/></label>)}<button className="primary" type="submit">Search jobs <span aria-hidden>↗</span></button></form>
  <div className="results-bar"><span aria-live="polite">{busy?'Searching…':`${results.total.toLocaleString()} open ${results.total===1?'role':'roles'}`}</span><span>Recently indexed first</span></div>
  <div className="job-layout"><section aria-label="Search results" aria-busy={busy}>{!busy&&!error&&results.items.length===0&&<div className="empty"><h2>No openings here yet.</h2><p>Add a source and let its first refresh finish, or try broader filters.</p></div>}{!busy&&results.items.map(job=><article key={job.id} className={`job-card ${selected?.id===job.id?'selected':''}`}><div className="job-top"><span>{job.company}</span><span className="pill">{job.remote_status||'Workplace unspecified'}</span></div><h2><button className="job-title" onClick={()=>setSelected(job)} aria-expanded={selected?.id===job.id}>{job.title}</button></h2><p>{job.location||'Location unspecified'}</p><div className="job-bottom"><span>{job.employment_type||'Employment type unspecified'}</span><span>{job.sources.length} {job.sources.length===1?'source':'sources'} · checked {when(job.sources[0]?.last_checked_at)}</span></div></article>)}
  <div className="pagination"><button disabled={busy||offset===0} onClick={()=>{setOffset(Math.max(0,offset-25));setSelected(null);}}>← Previous</button><span>{results.total?`${offset+1}–${Math.min(offset+25,results.total)} of ${results.total}`:'0 results'}</span><button disabled={busy||offset+25>=results.total} onClick={()=>{setOffset(offset+25);setSelected(null);}}>Next →</button></div></section>
  <aside>{selected?<><div className="eyebrow">{selected.company}</div><h2>{selected.title}</h2><p>{selected.location}</p><a className="apply" href={selected.application_url} target="_blank" rel="noopener noreferrer">Apply at original source ↗</a><h3>About the role</h3><p className="description">{selected.description||'The source did not provide a description.'}</p><h3>Source history</h3>{selected.sources.map(s=><p key={s.source_id}><a href={s.source_url} target="_blank" rel="noopener noreferrer">Original listing ↗</a><br/><small>{s.status} · checked {when(s.last_checked_at)}</small></p>)}</>:<><div className="eyebrow">TRACEABLE BY DESIGN</div><h2>Every role has a source.</h2><p>Select an opening to read its description, inspect where it came from and apply directly.</p><div className="aside-rule"/><p>Listings are refreshed on a schedule. Missing roles need reconfirmation before they close.</p><button className="text-button" onClick={()=>setTab('coverage')}>Inspect platform coverage ↗</button></>}</aside></div></>}
  {tab==='coverage'&&<><div className="notice">{providers.filter(p=>p.implementation_status==='IMPLEMENTED').length} connectors implemented. {verified} have live evidence. {providers.filter(p=>p.implementation_status==='NOT_STARTED').length} remain unimplemented.</div><div className="table-wrap"><table><caption>Required ATS and job-board platforms</caption><thead><tr><th>Platform</th><th>Implementation</th><th>Live evidence</th><th>Jobs extracted</th><th>Latest check / limitation</th></tr></thead><tbody>{providers.map(p=><tr key={p.name}><th scope="row">{p.name}<small>{p.kind==='ats'?'ATS':'Job board'}</small></th><td>{label(p.implementation_status)}</td><td><span className={`pill ${p.evidence_status==='LIVE_VERIFIED'?'good':''}`}>{label(p.evidence_status)}</span></td><td>{p.extraction_count??'—'}</td><td>{when(p.last_run_at)}<small>{p.failure_reason||p.limitations.join('; ')}</small></td></tr>)}</tbody></table></div></>}
  {tab==='sources'&&<><div className="admin-grid"><section className="panel"><h2>Connect a career board</h2><p>Greenhouse, Lever and Ashby hosted boards are supported in this release.</p><label>Admin token<input type="password" autoComplete="off" value={token} onChange={e=>setToken(e.target.value)}/></label><form onSubmit={addSource}><label>Company name<input required maxLength={200} value={source.company} onChange={e=>setSource({...source,company:e.target.value})}/></label><label>Hosted board URL<input type="url" required value={source.url} onChange={e=>setSource({...source,url:e.target.value})}/></label><button className="primary" disabled={adminBusy||!token} type="submit">Add source ↗</button></form><button className="text-button" disabled={adminBusy||!token} onClick={loadSources}>Reload source status ↻</button>{message&&<p role="status">{message}</p>}</section><section><h2>Connected sources</h2>{sources.length===0&&<p>Enter your admin token and load source status.</p>}{sources.map(s=><article className="job-card" key={s.id}><div className="job-top"><h3>{s.company}</h3><span className="pill">{s.provider}</span></div><p>{s.url}</p><p>{s.failures} consecutive failures · next check {when(s.next_check)}</p><button disabled={adminBusy} onClick={()=>refresh(s.id)}>Schedule refresh</button></article>)}</section></div><h2 className="section-title">Recent fetch runs</h2><div className="table-wrap"><table><caption>Refresh status for connected sources</caption><thead><tr><th>Run / Source</th><th>Status</th><th>Jobs</th><th>Started</th><th>Error</th></tr></thead><tbody>{runs.map(r=><tr key={r.id}><td>#{r.id} / #{r.source_id}</td><td>{r.status}</td><td>{r.count}</td><td>{when(r.started_at)}</td><td>{r.error||'—'}</td></tr>)}</tbody></table></div></>}
  </main><footer><span>V—Index</span><span>Original sources. Visible evidence.</span><a href="/docs" target="_blank" rel="noopener noreferrer">API documentation ↗</a></footer></>;
}
