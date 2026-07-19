// ---- View switching ----
const titles = {chat:"AI Core",dashboard:"Dashboard",tools:"Tools",tasks:"Tasks",timeline:"Execution",activity:"Activity"};
document.querySelectorAll('.nav-item').forEach(el=>{
  el.onclick = ()=>{
    document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
    document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
    el.classList.add('active');
    const v = el.dataset.view;
    document.getElementById('view-'+v).classList.add('active');
    document.getElementById('viewTitle').textContent = titles[v] || 'AI Core';
    if(v==='dashboard') loadMetrics();
    if(v==='dashboard') loadProviders();
    if(v==='tools') loadTools();
    if(v==='tasks') loadTasks();
    if(v==='activity') loadActivity();
  };
});
document.getElementById('btnTheme').onclick = ()=>{ state.theme = state.theme==='dark'?'light':'dark'; applyTheme(state.theme); };

// ---- Chat events ----
document.getElementById('sendBtn').onclick=sendChat;
document.getElementById('chatInput').addEventListener('keydown', e=>{ if(e.key==='Enter') sendChat(); });

// ---- Tools events ----
document.getElementById('toolSearch').oninput=loadTools;
document.getElementById('toolCat').onchange=loadTools;

// ---- Palette events ----
document.getElementById('palInput').oninput=searchPalette;
document.getElementById('palInput').addEventListener('keydown', e=>{
  if(e.key==='ArrowDown'){ palSel=Math.min(palSel+1,palItems.length-1); renderPalette(); e.preventDefault(); }
  if(e.key==='ArrowUp'){ palSel=Math.max(palSel-1,0); renderPalette(); e.preventDefault(); }
  if(e.key==='Enter'){ if(palItems[palSel]) runPalette(palItems[palSel]); }
  if(e.key==='Escape') closePalette();
});
overlay.onclick=(e)=>{ if(e.target===overlay) closePalette(); };
document.getElementById('btnPalette').onclick=openPalette;

// ---- Global shortcuts ----
document.addEventListener('keydown', e=>{
  if(e.ctrlKey && e.shiftKey && (e.key==='P'||e.key==='p')){ e.preventDefault(); openPalette(); }
});

// ---- Boot ----
connect();
loadMetrics();
setInterval(()=>{ if(currentView()==='dashboard'){ loadMetrics(); loadProviders(); } }, 4000);
