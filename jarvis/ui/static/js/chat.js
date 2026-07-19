const messagesEl = document.getElementById('messages');
let streamingEl=null, streamingBuf='';
function addMsg(role, content){
  const el=document.createElement('div'); el.className='msg '+role;
  const who=document.createElement('div'); who.className='who'; who.textContent= role==='user'?'You':'JARVIS';
  const body=document.createElement('div'); body.textContent=content;
  el.appendChild(who); el.appendChild(body); messagesEl.appendChild(el);
  messagesEl.scrollTop=messagesEl.scrollHeight; return el;
}
function appendToken(tok){
  if(!streamingEl){
    streamingEl=document.createElement('div'); streamingEl.className='msg assistant';
    const who=document.createElement('div'); who.className='who'; who.textContent='JARVIS';
    const body=document.createElement('div'); streamingEl.appendChild(who); streamingEl.appendChild(body);
    streamingEl._body=body; messagesEl.appendChild(streamingEl);
  }
  streamingBuf+=tok;
  streamingEl._body.textContent=streamingBuf;
  messagesEl.scrollTop=messagesEl.scrollHeight;
}
function finalizeMsg(content){
  if(streamingEl){ streamingEl._body.textContent=content||streamingBuf; streamingEl=null; streamingBuf=''; return; }
  addMsg('assistant', content);
}
function showTyping(){ const el=addMsg('assistant',''); el.innerHTML='<div class="who">JARVIS</div><div class="typing"><span></span><span></span><span></span></div>'; return el; }

async function sendChat(){
  const input=document.getElementById('chatInput'); const text=input.value.trim();
  if(!text) return;
  addMsg('user', text); input.value='';
  state.stages={}; state.plan=null; state.steps=[];
  send('chat', {text});
}
