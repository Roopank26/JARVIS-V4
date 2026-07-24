/* ============================================================
   JARVIS — Core app (state, transport, navigation, shell)
   Cinematic motion: FLIP navigation, magnetic buttons, cursor glow,
   dynamic lighting, card tilt, shared-element transitions
   ============================================================ */
"use strict";

const JARVIS = {
  ws: null,
  reconnectTimer: null,
  state: {
    theme: localStorage.getItem("jarvis-theme") || "dark",
    view: "chat",
    stages: {},
    plan: null,
    steps: [],
    tools: [],
    providers: {},
    metrics: {},
    conversations: [],
    notifications: [],
    agents: [],
    plugins: [],
    models: [],
    files: [],
    analytics: null,
  },
  handlers: {},
};
window.JARVIS = JARVIS;

// Reduced motion check
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const motionDuration = prefersReducedMotion ? '0.001ms' : 'var(--dur)';
const motionEasing = prefersReducedMotion ? 'linear' : 'var(--ease)';

/* ---------- Theme ---------- */
function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  localStorage.setItem("jarvis-theme", t);
  JARVIS.state.theme = t;
  window.dispatchEvent(new CustomEvent('themechange'));
}
function toggleTheme() {
  const newTheme = JARVIS.state.theme === "dark" ? "light" : "dark";
  document.body.style.transition = 'opacity 0.35s var(--ease)';
  document.body.style.opacity = '0.65';
  setTimeout(() => {
    applyTheme(newTheme);
    document.body.style.opacity = '1';
  }, 180);
}

/* ---------- Mouse tracking for dynamic lighting / tilt ---------- */
let mouseX = window.innerWidth / 2;
let mouseY = window.innerHeight / 2;
let cursorVisible = true;
let lightingThrottle = 0;
const LIGHTING_THROTTLE = 16;

document.addEventListener('mousemove', (e) => {
  mouseX = e.clientX;
  mouseY = e.clientY;
  cursorVisible = true;

  const root = document.documentElement;
  root.style.setProperty('--mx', mouseX + 'px');
  root.style.setProperty('--my', mouseY + 'px');

  const now = performance.now();
  if (now - lightingThrottle > LIGHTING_THROTTLE) {
    lightingThrottle = now;
    updateLighting(e);
  }
  updateTiltCards(e);
});

document.addEventListener('mouseleave', () => { cursorVisible = false; });
document.addEventListener('mouseenter', () => { cursorVisible = true; });

function updateLighting(e) {
  const search = document.getElementById("topbarSearch");
  if (search) {
    const r = search.getBoundingClientRect();
    search.style.setProperty('--sx', (e.clientX - r.left) + 'px');
    search.style.setProperty('--sy', (e.clientY - r.top) + 'px');
  }
  document.querySelectorAll(".nav-item").forEach(item => {
    const r = item.getBoundingClientRect();
    item.style.setProperty('--nx', (e.clientX - r.left) + 'px');
    item.style.setProperty('--ny', (e.clientY - r.top) + 'px');
  });
}

/* Tilt cards (subtle 3D rotation following cursor) */
const tiltCards = new Map();
const tiltObservers = new Map();
function updateTiltCards(e) {
  if (prefersReducedMotion) return;
  tiltCards.forEach((rect, el) => {
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const tiltX = ((y - cy) / cy) * -3.5;
    const tiltY = ((x - cx) / cx) * 3.5;
    el.style.setProperty('--tilt-x', tiltY + 'deg');
    el.style.setProperty('--tilt-y', tiltX + 'deg');
  });
}

function registerTiltCard(el) {
  if (prefersReducedMotion) return;
  if (tiltCards.has(el)) return;
  const rect = el.getBoundingClientRect();
  tiltCards.set(el, rect);
  const ro = new ResizeObserver(() => {
    if (!tiltCards.has(el)) { ro.disconnect(); return; }
    tiltCards.set(el, el.getBoundingClientRect());
  });
  ro.observe(el);
  tiltObservers.set(el, ro);
}

/* ---------- Magnetic hover ---------- */
const magneticInstances = new WeakMap();
function initMagnetic(selector) {
  if (prefersReducedMotion) return;
  document.querySelectorAll(selector).forEach(el => {
    if (magneticInstances.has(el)) return;
    const onMove = (e) => {
      const r = el.getBoundingClientRect();
      const x = e.clientX - r.left - r.width / 2;
      const y = e.clientY - r.top - r.height / 2;
      el.style.transform = `translate(${x * 0.22}px, ${y * 0.22}px)`;
    };
    const onLeave = () => { el.style.transform = 'translate(0, 0)'; };
    el.addEventListener('mousemove', onMove);
    el.addEventListener('mouseleave', onLeave);
    magneticInstances.set(el, { onMove, onLeave });
  });
}

/* ---------- Reconnect ---------- */
let _reconnectCount = 0;
function updateReconnectIndicator(show) {
  const el = document.getElementById("reconnectIndicator");
  if (!el) return;
  el.style.display = show ? "flex" : "none";
  el.textContent = show ? `Reconnecting… (${_reconnectCount})` : "";
}

/* ---------- Transport (WebSocket) ---------- */
function connect() {
  _reconnectCount = 0;
  updateReconnectIndicator(false);
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  JARVIS.ws = ws;
  ws.onopen = () => { _reconnectCount = 0; updateReconnectIndicator(false); };
  ws.onmessage = (e) => { try { handleEvent(JSON.parse(e.data)); } catch (err) { console.warn("WebSocket message error", err); } };
  ws.onclose = () => { _reconnectCount++; updateReconnectIndicator(true); JARVIS.reconnectTimer = setTimeout(connect, Math.min(1500 * _reconnectCount, 10000)); };
  ws.onerror = (e) => { try { ws.close(); } catch (err) { console.warn("WebSocket close error", err); } };
}
function sendWS(action, data) {
  if (JARVIS.ws && JARVIS.ws.readyState === 1) {
    JARVIS.ws.send(JSON.stringify(Object.assign({ action }, data)));
  }
}
async function api(path, opts) {
  try {
    const res = await fetch(path, Object.assign({ headers: { "Content-Type": "application/json" } }, opts));
    if (!res.ok) return null;
    return await res.json();
  } catch (_) { return null; }
}

/* ---------- AI Core state ---------- */
function setAiCoreState(state) {
  const sec = document.querySelector(".ai-core-section");
  if (sec) {
    sec.classList.remove("thinking", "listening", "speaking");
    if (state && state !== "idle") sec.classList.add(state);
  }
  const bg = window.__jarvisBg;
  if (bg && bg.setState) bg.setState(state);
}

/* ---------- Event routing ---------- */
function handleEvent(ev) {
  switch (ev.type) {
    case "status": renderStatus(ev.data); renderRightPanel(ev.data); break;
    case "stage":
      if (window.onStage) onStage(ev.data.stage);
      if (ev.data.stage === "thinking" || ev.data.stage === "planning") setAiCoreState("thinking");
      else if (ev.data.stage === "executing") setAiCoreState("executing");
      else if (ev.data.stage === "complete") setAiCoreState("idle");
      break;
    case "token": if (window.onToken) onToken(ev.data.token); break;
    case "user_message": if (window.onUserMessage) onUserMessage(ev.data.content); break;
    case "assistant_message": if (window.onAssistantMessage) onAssistantMessage(ev.data.content); break;
    case "plan": JARVIS.state.plan = ev.data.plan; if (window.onPlan) onPlan(ev.data.plan); setAiCoreState("thinking"); break;
    case "step": JARVIS.state.steps.push(ev.data); if (window.onStep) onStep(ev.data); setAiCoreState("executing"); break;
    case "tool":
      if (window.onTool) onTool(ev.data);
      const tName = ev.data.name || ev.data.tool || "";
      if (tName.includes("search")) setAiCoreState("searching");
      else if (tName.includes("image")) setAiCoreState("image_gen");
      else if (tName.includes("camera") || tName.includes("screenshot")) setAiCoreState("vision");
      else if (tName.includes("speak")) setAiCoreState("speaking");
      const capEl = document.getElementById("cap-selected");
      if (capEl) capEl.textContent = tName || "Executing";
      break;
    case "task": refreshTasks(); break;
    case "suggestion": showSuggestion(ev.data); break;
    case "error": pushNotification("err", ev.data.title || "Error", ev.data.reason || ""); setAiCoreState("error"); break;
    case "toast": pushNotification("info", ev.data.title || "Notice", ev.data.detail || ""); break;
    case "plugin": if (JARVIS.state.view === "plugins") loadPlugins(); break;
    case "activity": if (JARVIS.state.view === "activity") loadActivity(); break;
    case "voice_state":
      handleVoiceState(ev.data);
      const vs = ev.data.state || "";
      if (vs === "listening" || vs === "user_speaking") setAiCoreState("listening");
      else if (vs === "speaking" || vs === "tts_started" || vs === "playback_started") setAiCoreState("speaking");
      else if (vs === "idle" || vs === "stopped" || vs === "playback_finished") setAiCoreState("idle");
      break;
    case "voice_interrupt": handleVoiceState({ state: "listening" }); setAiCoreState("listening"); break;
    default: break;
  }
}

/* ---------- Status / metrics ---------- */
function renderStatus(d) {
  JARVIS.state.metrics = d;
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  const dot = (id, on) => {
    const el = document.getElementById(id);
    if (el) {
      const wasOn = el.classList.contains("on");
      el.classList.toggle("on", !!on);
      if (on && !wasOn) {
        el.style.animation = 'none';
        el.offsetHeight;
        el.style.animation = 'checkPop 0.5s var(--ease-bounce)';
      }
    }
  };

  set("pillModel", d.model || "—");
  set("pillProvider", d.provider || "—");
  dot("dotModel", !!d.model && d.model !== "none");
  dot("dotProvider", !!d.provider && d.provider !== "none");
  dot("dotInternet", !!d.internet);
  const vs = d.voice || {};
  dot("dotVoice", vs.ready === true || vs.tts === "ready" || vs.stt === "ready");

  const ram = d.ram || {};
  set("ram-usage", ram.used_gb != null ? `${ram.used_gb} / ${ram.total_gb} GB` : "—");
  bar("ram-bar", ram.percent);
  bar("cpu-bar", d.cpu);
  set("cpu-usage", d.cpu != null ? `${d.cpu}%` : "—");

  const gpu = d.gpu || {};
  set("gpu-usage", gpu.load != null ? `${gpu.load}%` : "—");
  bar("gpu-bar", gpu.load || 0);

  const mem = d.memory || {};
  set("session-memory", mem.entries != null ? `${mem.entries} entries` : "—");
  bar("session-bar", mem.entries != null ? Math.min(100, mem.entries) : 0);

  if (d.capabilities_count != null) {
    set("longterm-memory", `${d.capabilities_count} capabilities`);
    bar("longterm-bar", Math.min(100, d.capabilities_count * 5));
  }
  if (d.plugins_count != null) {
    set("vector-db", `${d.plugins_count} plugins`);
    bar("vector-bar", Math.min(100, d.plugins_count * 10));
  }
}


function bar(id, pct) {
  const el = document.getElementById(id);
  if (el) {
    const target = Math.max(0, Math.min(100, pct || 0));
    const current = parseFloat(el.style.width) || 0;
    if (Math.abs(current - target) > 1) {
      el.style.transition = 'width 0.9s var(--ease-spring)';
      el.style.width = `${target}%`;
    }
  }
}

/* ---------- Right panel ---------- */
async function renderRightPanel() {
  const st = await api("/api/providers");
  const wrap = document.getElementById("rpProviders");
  if (!wrap) return;
  if (!st || !st.providers) { wrap.innerHTML = `<div class="muted" style="font-size:12px">No provider data</div>`; return; }
  const icons = { airllm: "✦", ollama: "◉", groq: "⚡", openai: "◈", anthropic: "✶", google: "◆" };
  wrap.innerHTML = Object.values(st.providers).map(p => {
    const status = p.available ? (st.primary === p.provider ? "online" : "busy") : "offline";
    return `<div class="rp-item" data-provider="${esc(p.provider)}">
      <div class="rp-icon">${icons[p.provider] || "◆"}</div>
      <div class="rp-info"><div class="rp-name">${esc(cap(p.provider))}</div>
        <div class="rp-meta" id="${esc(p.provider)}-meta">${esc(p.current_model || "—")}</div></div>
      <div class="rp-status ${status}"></div>
    </div>`;
  }).join("");
}
function cap(s) { return (s || "").replace(/^\w/, c => c.toUpperCase()); }

/* ---------- Navigation with FLIP / shared-element ---------- */
const VIEW_TITLES = {
  chat: "AI Core & Chat",
  dashboard: "Home Dashboard",
  agents: "Multi-Agent System",
  workspace: "Workspace Awareness",
  memory: "Memory Intelligence Center",
  research: "Autonomous Research Center",
  vision: "Computer Vision Center",
  automation: "Automation & Background Jobs",
  tasks: "Tasks Queue",
  timeline: "Execution Timeline",
  files: "File Explorer",
  models: "Model & Provider Manager",
  plugins: "Plugin Manager & Marketplace",
  terminal: "JARVIS Interactive Terminal",
  diagnostics: "Diagnostics & Observability",
  developer: "Developer Mode & Capability Inspector",
  settings: "Settings & System Preferences",
};

let currentView = null;
let navFlipState = null;

function navigate(view) {
  if (view === currentView) return;
  const prev = currentView;
  currentView = view;
  JARVIS.state.view = view;

  if (prev === "analytics") cancelChartAnim();
  if (prev === "chat") stopWaveform();

  document.querySelectorAll(".nav-item").forEach(n => n.classList.toggle("active", n.dataset.view === view));

  const prevEl = document.getElementById("view-" + (prev || ""));
  if (prevEl) {
    const prevRects = captureFlipRects(prevEl);
    prevEl.classList.add("exiting");
    prevEl.classList.remove("active");

    tiltCards.forEach((rect, el) => {
      if (prevEl.contains(el)) {
        tiltCards.delete(el);
        const ro = tiltObservers.get(el);
        if (ro) { ro.disconnect(); tiltObservers.delete(el); }
      }
    });

    requestAnimationFrame(() => {
      const nextEl = document.getElementById("view-" + view);
      if (!nextEl) return;
      nextEl.classList.remove("exiting");
      nextEl.classList.add("active");
      const nextRects = captureFlipRects(nextEl);
      requestAnimationFrame(() => {
        prevEl.classList.remove("exiting");
        applyFlip(prevRects, nextRects, nextEl);
      });
    });
  } else {
    requestAnimationFrame(() => {
      const el = document.getElementById("view-" + view);
      if (el) {
        el.classList.remove("exiting");
        el.classList.add("active");
        staggerChildren(el);
      }
    });
  }

  const t = document.getElementById("viewTitle");
  if (t) {
    t.style.opacity = "0";
    t.style.transform = "translateY(-8px)";
    requestAnimationFrame(() => {
      t.textContent = VIEW_TITLES[view] || cap(view);
      t.style.transition = "opacity 0.28s var(--ease), transform 0.28s var(--ease)";
      t.style.opacity = "1";
      t.style.transform = "translateY(0)";
    });
  }
  document.body.classList.remove("nav-open");

  setTimeout(() => {
    document.querySelectorAll(".view.exiting").forEach(v => v.classList.remove("exiting"));
  }, 450);

  if (JARVIS.handlers[view]) JARVIS.handlers[view]();
}

function captureFlipRects(root) {
  const map = new Map();
  root.querySelectorAll('.card, .metric, .section-title, .tool-card, .list-row, .agent-card, .model-card, .chart-card, .stat, .plugin-card, .toolbar, .ai-core-section, .stages, .timeline').forEach(el => {
    map.set(el, el.getBoundingClientRect());
  });
  return map;
}

function applyFlip(prevMap, nextMap, root) {
  if (!root || !root.classList.contains('active')) return;
  root.querySelectorAll('.card, .metric, .section-title, .tool-card, .list-row, .agent-card, .model-card, .chart-card, .stat, .plugin-card, .toolbar, .ai-core-section, .stages, .timeline').forEach(el => {
    const p = prevMap.get(el);
    if (p && el.offsetParent !== null) {
      const n = el.getBoundingClientRect();
      const dx = p.left - n.left;
      const dy = p.top - n.top;
      const ds = p.width / (n.width || 1);
      if (Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5 || Math.abs(ds - 1) > 0.01) {
        el.style.transformOrigin = 'top left';
        el.style.transform = `translate(${dx}px, ${dy}px) scale(${ds})`;
        el.style.transition = 'none';
        requestAnimationFrame(() => {
          el.style.transition = 'transform 0.55s var(--ease-spring), opacity 0.45s var(--ease-spring)';
          el.style.transform = 'none';
          el.style.opacity = '1';
          setTimeout(() => { el.style.transition = ''; el.style.transform = ''; el.style.opacity = ''; }, 600);
        });
      }
    }
    el.style.animation = 'none';
    el.offsetHeight;
    el.style.animation = `staggerIn 0.55s var(--ease-spring) backwards`;
  });
  root.querySelectorAll('[data-tilt], .tool-card, .agent-card, .model-card, .list-row, .ws-pane').forEach(registerTiltCard);
}

function staggerChildren(container) {
  const animatable = container.querySelectorAll('.card, .metric, .tool-card, .list-row, .section-title, .agent-card, .model-card, .chart-card, .stat, .plugin-card, .toolbar, .ai-core-section, .stages, .timeline');
  const staggerMs = 38;
  animatable.forEach((el, i) => {
    el.style.animation = 'none';
    el.offsetHeight;
    el.style.animation = `staggerIn 0.55s var(--ease-spring) ${i * staggerMs}ms backwards`;
    el.style.setProperty('--stagger-index', i);
    registerTiltCard(el);
  });
}

/* ---------- Toasts ---------- */
function showToast(title, msg, kind = "info") {
  const icons = { ok: "✓", err: "!", warn: "▲", info: "ℹ" };
  const wrap = document.getElementById("toasts");
  const t = document.createElement("div");
  t.className = `toast ${kind}`;
  t.innerHTML = `<div class="t-ico">${icons[kind] || "ℹ"}</div><div><div class="t-title">${esc(title)}</div>${msg ? `<div class="t-msg">${esc(msg)}</div>` : ""}</div>`;
  wrap.appendChild(t);
  requestAnimationFrame(() => {
    t.style.animation = 'none';
    t.offsetHeight;
    t.style.animation = `toastIn 0.55s var(--ease-spring)`;
    t.classList.add('ripple');
  });
  setTimeout(() => {
    t.classList.add("out");
    setTimeout(() => t.remove(), 400);
  }, 4500);
}

/* ---------- Notifications ---------- */
function pushNotification(kind, title, msg) {
  JARVIS.state.notifications.unshift({ kind, title, msg, ts: Date.now() });
  if (JARVIS.state.notifications.length > 40) JARVIS.state.notifications.pop();
  const c = document.getElementById("notifCount");
  if (c) {
    c.textContent = JARVIS.state.notifications.length;
    c.classList.remove("bump");
    void c.offsetWidth;
    c.classList.add("bump");
  }
  showToast(title, msg, kind);
  renderNotifications();
}
function renderNotifications() {
  const p = document.getElementById("notifPanel");
  if (!p) return;
  const items = JARVIS.state.notifications;
  if (!items.length) { p.innerHTML = `<div class="notif-head">Notifications <span class="muted" style="font-weight:400;font-size:12px;cursor:pointer" onclick="clearNotifications()">clear</span></div><div class="notif-empty">No notifications yet</div>`; return; }
  const icons = { ok: "✓", err: "!", warn: "▲", info: "ℹ", task: "↻", download: "↓" };
  p.innerHTML = `<div class="notif-head">Notifications <span class="muted" style="font-weight:400;font-size:12px;cursor:pointer" onclick="clearNotifications()">clear</span></div>` +
    items.map(n => `<div class="list-row"><div class="lr-ico" style="color:var(--${n.kind === "err" ? "err" : n.kind === "warn" ? "warn" : n.kind === "ok" ? "ok" : "info"})">${icons[n.kind] || "ℹ"}</div>
      <div class="lr-main"><div class="lr-title">${esc(n.title)}</div>${n.msg ? `<div class="lr-sub">${esc(n.msg)}</div>` : ""}</div></div>`).join("");
}
function clearNotifications() {
  JARVIS.state.notifications = [];
  const c = document.getElementById("notifCount"); if (c) c.textContent = "0";
  renderNotifications();
}

/* ---------- Voice state ---------- */
function handleVoiceState(d) {
  const orb = document.getElementById("voiceOrb");
  if (!orb) return;
  const s = d.state || "";
  const wasListening = orb.classList.contains("listening");
  const wasSpeaking = orb.classList.contains("speaking");

  orb.classList.toggle("listening", s === "listening" || s === "user_speaking");
  orb.classList.toggle("speaking", s === "speaking" || s === "tts_started" || s === "playback_started");

  if ((orb.classList.contains("listening") && !wasListening) ||
      (orb.classList.contains("speaking") && !wasSpeaking)) {
    orb.style.animation = 'none';
    orb.offsetHeight;
    orb.style.animation = `scaleInElastic 0.55s var(--ease-spring)`;
  }

  const glyph = orb.querySelector('.voice-glyph');
  if (glyph) {
    if (s === "speaking" || s === "tts_started" || s === "playback_started") {
      glyph.textContent = "🎙";
      glyph.style.animation = "glowPulse 1.6s var(--ease) infinite";
    } else if (s === "listening" || s === "user_speaking") {
      glyph.textContent = "🎤";
      glyph.style.animation = "breathe 2.2s var(--ease) infinite";
    } else {
      glyph.textContent = "◉";
      glyph.style.animation = "none";
    }
  }

  const active = orb.classList.contains("listening") || orb.classList.contains("speaking");
  if (active && !window.JARVIS._waveActive) {
    window.JARVIS._waveActive = true;
    if (typeof initWaveform === 'function' && !window.JARVIS._waveInited) {
      initWaveform();
      window.JARVIS._waveInited = true;
    }
  } else if (!active) {
    window.JARVIS._waveActive = false;
    if (typeof stopWaveform === 'function') stopWaveform();
  }
}

/* ---------- Utils ---------- */
function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function loadPersistedSettings() {
  try {
    const accent = localStorage.getItem("jarvis-accent");
    if (accent) document.documentElement.style.setProperty("--accent", accent);
    const theme = localStorage.getItem("jarvis-theme");
    if (theme) applyTheme(theme);
  } catch (e) { /* no-op */ }
}
function fmtTime(ts) {
  const d = new Date(ts * 1000 || ts);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
function emptyState(ico, title, sub) {
  return `<div class="empty-state"><div class="es-ico">${ico}</div><div class="es-title">${esc(title)}</div><div class="es-sub">${esc(sub)}</div></div>`;
}
function refreshTasks() { if (JARVIS.state.view === "tasks") loadTasks(); }

/* ---------- Boot wiring ---------- */
function initShell() {
  loadPersistedSettings();
  applyTheme(JARVIS.state.theme);
  document.getElementById("btnTheme").onclick = toggleTheme;
  document.getElementById("btnPalette").onclick = () => openPalette();
  document.getElementById("topbarSearch").onclick = () => openPalette();
  document.querySelectorAll(".nav-item").forEach(n => {
    n.addEventListener('click', function(e) {
      navigate(this.dataset.view);
      const ripple = document.createElement('span');
      ripple.style.cssText = `position:absolute;background:var(--accent-glow);border-radius:50%;pointer-events:none;animation:rippleOut 0.65s var(--ease-out) forwards;`;
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = (e.clientX - rect.left - size/2) + 'px';
      ripple.style.top = (e.clientY - rect.top - size/2) + 'px';
      this.style.position = 'relative';
      this.style.overflow = 'hidden';
      this.appendChild(ripple);
      setTimeout(() => ripple.remove(), 700);
    });
  });
  document.getElementById("btnSidebar").onclick = () => document.body.classList.toggle("nav-open");

  const np = document.getElementById("notifPanel");
  document.getElementById("btnNotif").onclick = (e) => { e.stopPropagation(); np.classList.toggle("open"); };
  document.addEventListener("click", (e) => { if (!np.contains(e.target) && e.target.id !== "btnNotif") np.classList.remove("open"); });

  const orb = document.getElementById("voiceOrb");
  if (orb) {
    orb.onmousedown = () => { orb.classList.add("listening"); sendWS("voice_ptt", { on: true }); };
    orb.onmouseup = orb.onmouseleave = () => { orb.classList.remove("listening"); sendWS("voice_ptt", { on: false }); };
    for (let i = 1; i <= 3; i++) {
      const ring = document.createElement('span');
      ring.className = 'voice-ring';
      ring.style.animationDelay = (i * 0.65) + 's';
      orb.appendChild(ring);
    }
  }

  document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
      const ripple = document.createElement('span');
      ripple.style.cssText = `position:absolute;background:rgba(255,255,255,0.28);border-radius:50%;pointer-events:none;animation:rippleOut 0.6s var(--ease-out) forwards;`;
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = (e.clientX - rect.left - size/2) + 'px';
      ripple.style.top = (e.clientY - rect.top - size/2) + 'px';
      this.appendChild(ripple);
      setTimeout(() => ripple.remove(), 650);
    });
  });

  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "P" || e.key === "p")) { e.preventDefault(); openPalette(); }
    else if (e.key === "Escape") {
      closePalette(); document.body.classList.remove("nav-open"); const np = document.getElementById("notifPanel"); if (np) np.classList.remove("open");
      if (typeof window.stopGeneration === "function") window.stopGeneration();
    }
  });

  initMagnetic('.icon-btn, .notif-fab, .voice-orb, .btn.primary, .nav-item');

  connect();
  navigate("chat");
}
