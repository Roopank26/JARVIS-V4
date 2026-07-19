const STAGES = ["thinking","planning","selecting_tools","executing","observing","generating","complete"];
const STAGE_LABEL = {thinking:"Thinking",planning:"Planning",selecting_tools:"Selecting tools",executing:"Executing",observing:"Observing results",generating:"Generating response",complete:"Complete"};
let state = { stages:{}, plan:null, steps:[], tools:[], theme: localStorage.getItem('jarvis-theme')||'dark' };
let ws = null;

function applyTheme(t){ document.documentElement.setAttribute('data-theme', t); localStorage.setItem('jarvis-theme', t); }
applyTheme(state.theme);

function connect(){
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = (e)=>{ try { handleEvent(JSON.parse(e.data)); } catch(_){} };
  ws.onclose = ()=> setTimeout(connect, 1500);
}
function send(action, data){ if(ws && ws.readyState===1) ws.send(JSON.stringify({action, ...data})); }

function handleEvent(ev){
  switch(ev.type){
    case 'status': renderStatus(ev.data); break;
    case 'stage': setStage(ev.data.stage); break;
    case 'token': appendToken(ev.data.token); break;
    case 'user_message': addMsg('user', ev.data.content); break;
    case 'assistant_message': finalizeMsg(ev.data.content); break;
    case 'plan': state.plan = ev.data.plan; renderTimeline(); break;
    case 'step': state.steps.push(ev.data); renderTimeline(); break;
    case 'tool': handleTool(ev.data); break;
    case 'task': loadTasks(); break;
    case 'suggestion': showSuggestion(ev.data); break;
    case 'error': showToast(ev.data.title, ev.data.reason, 'err'); break;
    case 'toast': showToast(ev.data.title, ev.data.detail); break;
    case 'plugin': if(currentView()==='tools') loadTools(); break;
    case 'activity': if(currentView()==='activity') loadActivity(); break;
  }
}
function currentView(){ const a=document.querySelector('.view.active'); return a?a.id.replace('view-',''):'chat'; }
