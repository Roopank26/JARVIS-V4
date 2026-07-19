function setDot(id, ok){ const d=document.getElementById(id); d.className='dot '+(ok?'ok':(ok===false?'err':'')); }
function renderStatus(m){
  setDot('dotInternet', m.internet);
  setDot('dotVoice', m.voice && m.voice.ready);
  document.getElementById('pillModel').textContent = m.model || 'model';
  document.getElementById('pillProvider').textContent = m.provider || 'provider';
  if(currentView()==='dashboard') renderMetricCards(m);
  updateRightPanel(m);
}
function renderMetricCards(m){
  const g = document.getElementById('metricGrid');
  g.innerHTML = '';
  const cards = [
    {label:'CPU', value: m.cpu+'%', pct: m.cpu},
    {label:'RAM', value: (m.ram? m.ram.used_gb+' / '+m.ram.total_gb+' GB':'–'), pct: m.ram? m.ram.percent:0},
    {label:'Provider', value: (m.provider||'–').toUpperCase()},
    {label:'Model', value: (m.model||'–')},
    {label:'Voice', value: (m.voice&&m.voice.ready)?'Ready':'Off'},
    {label:'Memory', value: (m.memory? m.memory.entries+' entries':'–')},
  ];
  cards.forEach(c=>{
    const el=document.createElement('div'); el.className='card metric';
    el.innerHTML = `<div class="label">${c.label}</div><div class="value">${c.value}</div>` +
      (c.pct!=null?`<div class="bar"><span style="width:${c.pct}%"></span></div>`:'');
    g.appendChild(el);
  });
  const s = document.getElementById('secondaryGrid'); s.innerHTML='';
  const sec=[
    {label:'Internet', value: m.internet?'Connected':'Offline'},
    {label:'Platform', value: m.platform||'–'},
    {label:'Voice STT', value: m.voice?m.voice.stt:'–'},
    {label:'Voice TTS', value: m.voice?m.voice.tts:'–'},
  ];
  sec.forEach(c=>{ const el=document.createElement('div'); el.className='card metric'; el.innerHTML=`<div class="label">${c.label}</div><div class="value" style="font-size:17px">${c.value}</div>`; s.appendChild(el); });
}
async function loadProviders(){
  try{
    const r=await fetch('/api/providers');
    const d=await r.json();
    const list=document.getElementById('providerList');
    if(!list) return;
    list.innerHTML='';
    const order=['ollama','groq','openai','google','anthropic'];
    order.forEach(key=>{
      const p=d.providers&&d.providers[key];
      if(!p) return;
      const active=(d.primary===key);
      const row=document.createElement('div');
      row.className='row';
      row.innerHTML=`<div class="grow"><div style="font-weight:600">${key.toUpperCase()} ${active?'<span class="badge ok">ACTIVE</span>':''}</div>
        <div class="meta">${p.model||'–'} · ${p.available_models?p.available_models.length+' models':'0 models'} · ${p.available?'online':'offline'}</div></div>
        <span class="badge ${p.available?'ok':'fail'}">${p.available?'online':'offline'}</span>`;
      list.appendChild(row);
    });
  }catch(_){}
}
function renderMetricCards(m){
  const g = document.getElementById('metricGrid');
  g.innerHTML = '';
  const cards = [
    {label:'CPU', value: m.cpu+'%', pct: m.cpu},
    {label:'RAM', value: (m.ram? m.ram.used_gb+' / '+m.ram.total_gb+' GB':'–'), pct: m.ram? m.ram.percent:0},
    {label:'Provider', value: (m.provider||'–').toUpperCase()},
    {label:'Model', value: (m.model||'–')},
    {label:'Voice', value: (m.voice&&m.voice.ready)?'Ready':'Off'},
    {label:'Memory', value: (m.memory? m.memory.entries+' entries':'–')},
  ];
  cards.forEach(c=>{
    const el=document.createElement('div'); el.className='card metric';
    el.innerHTML = `<div class="label">${c.label}</div><div class="value">${c.value}</div>` +
      (c.pct!=null?`<div class="bar"><span style="width:${c.pct}%"></span></div>`:'');
    g.appendChild(el);
  });
  const s = document.getElementById('secondaryGrid'); s.innerHTML='';
  const sec=[
    {label:'Internet', value: m.internet?'Connected':'Offline'},
    {label:'Platform', value: m.platform||'–'},
    {label:'Voice STT', value: m.voice?m.voice.stt:'–'},
    {label:'Voice TTS', value: m.voice?m.voice.tts:'–'},
  ];
  sec.forEach(c=>{ const el=document.createElement('div'); el.className='card metric'; el.innerHTML=`<div class="label">${c.label}</div><div class="value" style="font-size:17px">${c.value}</div>`; s.appendChild(el); });
}
async function loadMetrics(){ try{ const r=await fetch('/api/status'); renderStatus(await r.json()); }catch(_){} }

function updateRightPanel(m){
  if(m.cpu != null){
    const cpuEl = document.getElementById('cpu-usage');
    const cpuBar = document.getElementById('cpu-bar');
    if(cpuEl) cpuEl.textContent = m.cpu + '%';
    if(cpuBar) cpuBar.style.width = m.cpu + '%';
  }
  if(m.ram){
    const ramEl = document.getElementById('ram-usage');
    const ramBar = document.getElementById('ram-bar');
    if(ramEl) ramEl.textContent = m.ram.used_gb + ' / ' + m.ram.total_gb + ' GB';
    if(ramBar) ramBar.style.width = m.ram.percent + '%';
  }
  if(m.memory){
    const memEl = document.getElementById('session-memory');
    const memBar = document.getElementById('session-bar');
    if(memEl) memEl.textContent = m.memory.entries + ' entries';
    if(memBar) memBar.style.width = Math.min(m.memory.entries * 2, 100) + '%';
  }
}

async function loadTools(){
  const q=document.getElementById('toolSearch').value;
  const cat=document.getElementById('toolCat').value;
  try{
    const r=await fetch('/api/tools?q='+encodeURIComponent(q)+'&category='+encodeURIComponent(cat));
    const d=await r.json();
    state.tools=d.tools;
    const grid=document.getElementById('toolGrid'); grid.innerHTML='';
    d.tools.forEach(t=>{
      const c=document.createElement('div'); c.className='tool-card';
      const fav = d.favorites.includes(t.name);
      c.innerHTML=`<div class="tname">${t.name}<span class="star ${fav?'on':''}" data-name="${t.name}">${fav?'★':'☆'}</span></div>
        <div class="tdesc">${t.description||''}</div>
        <div style="margin-top:8px"><span class="tag">${t.category}</span> ${t.source==='plugin'?'<span class="tag">plugin</span>':''}</div>`;
      grid.appendChild(c);
    });
    grid.querySelectorAll('.star').forEach(s=>s.onclick=()=>toggleFav(s.dataset.name));
    const sel=document.getElementById('toolCat');
    d.categories.forEach(catName=>{ if(![...sel.options].some(o=>o.value===catName)){ const o=document.createElement('option'); o.value=catName; o.textContent=catName; sel.appendChild(o);} });
    const chips=document.getElementById('toolChips');
    chips.innerHTML='';
    [['favorites', ()=>d.favorites],['recent', ()=>d.recent]].forEach(([label,get])=>{
      const ch=document.createElement('span'); ch.className='chip'; ch.textContent=label+': '+(get().length||0);
      chips.appendChild(ch);
    });
  }catch(_){}
}
function toggleFav(name){ fetch('/api/tools/favorite',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})}).then(loadTools); }

async function loadTasks(){
  try{
    const r=await fetch('/api/tasks'); const d=await r.json();
    const list=document.getElementById('taskList'); list.innerHTML='';
    if(!d.tasks.length){ list.innerHTML='<div class="empty">No background tasks yet.</div>'; return; }
    d.tasks.slice().reverse().forEach(t=>{
      const row=document.createElement('div'); row.className='row';
      const pct=Math.round((t.progress||0)*100);
      const badge = t.state==='running'?'run':(t.state==='completed'?'ok':(t.state==='failed'?'fail':''));
      row.innerHTML=`<div class="grow"><div style="font-weight:600">${t.name}</div>
        <div class="meta">${t.category} · ${Math.round(t.progress*100)}%${t.eta_seconds!=null?' · ETA '+Math.ceil(t.eta_seconds)+'s':''}</div>
        <div class="bar" style="margin-top:6px"><span style="width:${pct}%"></span></div></div>
        <span class="badge ${badge}">${t.state}</span>`;
      const act=document.createElement('div'); act.style.display='flex'; act.style.gap='6px';
      if(['running','queued'].includes(t.state)) act.appendChild(mkBtn('Pause',()=>taskAct(t.id,'pause')));
      if(t.state==='paused') act.appendChild(mkBtn('Resume',()=>taskAct(t.id,'resume')));
      if(['running','queued','paused'].includes(t.state)) act.appendChild(mkBtn('Cancel',()=>taskAct(t.id,'cancel')));
      row.appendChild(act); list.appendChild(row);
    });
  }catch(_){}
}
function mkBtn(label,fn){ const b=document.createElement('button'); b.className='btn ghost'; b.style.padding='7px 12px'; b.style.fontSize='12px'; b.textContent=label; b.onclick=fn; return b; }
function taskAct(id,a){ fetch('/api/tasks/'+id+'/'+a,{method:'POST'}).then(loadTasks); }

function renderTimeline(){
  const tl=document.getElementById('timeline'); if(!tl) return; tl.innerHTML='';
  const items=[];
  if(state.plan) state.plan.steps.forEach(s=>items.push({title:'Plan · '+s.description, cls:'ok', meta:s.tool}));
  state.steps.forEach(s=>items.push({title:(s.phase==='start'?'Running':'')+' '+s.description, cls: s.phase==='complete'?'ok':(s.phase==='error'?'err':''), meta:s.tool+(s.error?(' · '+s.error):'')}));
  if(!items.length){ tl.innerHTML='<div class="empty">No workflow yet. Send a request to see its timeline.</div>'; return; }
  items.forEach(it=>{ const el=document.createElement('div'); el.className='tl-item '+(it.cls||''); el.innerHTML=`<div style="font-weight:600">${it.title}</div>${it.meta?`<div class="meta">${it.meta}</div>`:''}`; tl.appendChild(el); });
}

let actFilter=null;
async function loadActivity(){
  try{
    const r=await fetch('/api/activity'+(actFilter?('?category='+actFilter):'')); const d=await r.json();
    const list=document.getElementById('actList'); list.innerHTML='';
    if(!d.activity.length){ list.innerHTML='<div class="empty">No activity recorded yet.</div>'; return; }
    d.activity.forEach(a=>{ const row=document.createElement('div'); row.className='row'; row.innerHTML=`<div class="grow"><div>${a.title}</div><div class="meta">${a.detail||''}</div></div><span class="badge">${a.category}</span>`; list.appendChild(row); });
    const cats=document.getElementById('actCats'); cats.innerHTML='';
    const mk=(label,val)=>{ const ch=document.createElement('span'); ch.className='chip'+(actFilter===val?' active':''); ch.textContent=label; ch.onclick=()=>{ actFilter=val; loadActivity(); }; cats.appendChild(ch); };
    mk('All',null); Object.entries(d.categories).forEach(([k,v])=>mk(k+' '+v,k));
  }catch(_){}
}
