const overlay=document.getElementById('overlay'); let palSel=0, palItems=[];
function openPalette(){ overlay.classList.add('show'); const i=document.getElementById('palInput'); i.value=''; i.focus(); searchPalette(); }
function closePalette(){ overlay.classList.remove('show'); }
async function searchPalette(){
  const q=document.getElementById('palInput').value;
  try{ const r=await fetch('/api/palette?q='+encodeURIComponent(q)); const d=await r.json(); palItems=d.items; palSel=0; renderPalette(); }catch(_){}
}
function renderPalette(){
  const box=document.getElementById('palResults'); box.innerHTML='';
  palItems.slice(0,30).forEach((it,idx)=>{
    const el=document.createElement('div'); el.className='pitem'+(idx===palSel?' sel':'');
    el.innerHTML=`<div class="ptitle">${it.title}</div><div class="pmeta"><span class="pcat">${it.category}</span><span>${it.subtitle||''}</span></div>`;
    el.onclick=()=>runPalette(it); el.onmouseenter=()=>{palSel=idx; renderPalette();};
    box.appendChild(el);
  });
}
function runPalette(it){ closePalette(); const a=it.action||''; if(a.startsWith('send:')){ document.getElementById('chatInput').value=a.slice(5); sendChat(); } else if(a.startsWith('model:')){ sendChat.call(); addMsg('user','switch to '+a.slice(6)); send('chat',{text:'switch to '+a.slice(6)}); } else { showToast(it.title, it.subtitle); } }
function showSuggestion(s){
  const box=document.getElementById('suggBox');
  const el=document.createElement('div'); el.className='sugg';
  el.innerHTML=`<div class="grow"><div class="stitle">${s.title}</div><div class="sdetail">${s.detail||''}</div></div>`;
  const b=mkBtn('Do it',()=>{ document.getElementById('chatInput').value=s.action; sendChat(); setTimeout(()=>el.remove(),300); });
  el.appendChild(b); box.appendChild(el);
  setTimeout(()=>el.remove(), 20000);
}
function showToast(title, detail, cls){
  const t=document.createElement('div'); t.className='toast '+(cls||'');
  t.innerHTML=`<div class="tt">${title}</div><div class="td">${detail||''}</div>`;
  document.getElementById('toasts').appendChild(t);
  setTimeout(()=>t.remove(), 6000);
}
