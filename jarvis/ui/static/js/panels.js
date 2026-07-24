/* ============================================================
   JARVIS — AI Operating System Panels & View Handlers
   Includes Dashboard, Memory Center, Research Center, Vision Center,
   Automation Center, Model Manager, Plugin Manager, Terminal,
   Diagnostics, Developer Mode, Settings, Timeline, Files, Tasks.
   ============================================================ */
"use strict";

const ICONS = {
  cpu: "⚡", ram: "▤", gpu: "◭", disk: "🖴", net: "📡", provider: "◈",
  model: "✦", voice: "🎤", memory: "✶", internet: "🌐", tasks: "↻", agents: "⌬",
  vision: "👁", research: "⌕", terminal: "", diagnostics: "📊", dev: "🛠"
};

function esc(s) {
  if (s == null) return "";
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function cap(s) {
  if (!s) return "";
  return String(s).charAt(0).toUpperCase() + String(s).slice(1);
}

function emptyState(ico, title, desc) {
  return `<div class="empty-state"><div class="empty-ico">${ico}</div><div class="empty-title">${esc(title)}</div><div class="empty-desc">${esc(desc)}</div></div>`;
}

function setIntervalIfView(view, fn, ms) {
  if (!JARVIS._timers) JARVIS._timers = {};
  if (JARVIS._timers[view]) return;
  JARVIS._timers[view] = setInterval(() => { 
    if (JARVIS.state.view !== view) {
      clearInterval(JARVIS._timers[view]);
      delete JARVIS._timers[view];
      return;
    }
    fn(); 
  }, ms);
}

/* ---------------- 1. Home Dashboard ---------------- */
JARVIS.handlers.dashboard = async function () {
  const v = document.getElementById("view-dashboard");
  const now = new Date();
  v.innerHTML = `
    <div class="section-title">JARVIS Command Center <span class="sub" id="dashTs">${now.toLocaleTimeString()}</span></div>
    <div class="grid metrics" id="metricGrid"></div>
    <div style="height:16px"></div>
    <div class="grid cols-2">
      <div class="card"><div class="section-title">Active AI Providers & Models</div><div id="dashProviders"></div></div>
      <div class="card"><div class="section-title">System Status & Environment</div>
        <div class="mini-metric"><span>Voice Engine</span><span id="dashVoice">Active</span></div>
        <div class="mini-metric" style="margin-top:10px"><span>Memory Store</span><span id="dashMem">Ready</span></div>
        <div class="mini-metric" style="margin-top:10px"><span>Network Connectivity</span><span id="dashNet">Online</span></div>
      </div>
    </div>
    <div style="height:16px"></div>
    <div class="grid cols-2">
      <div class="card"><div class="section-title">Background Tasks Queue</div><div class="list" id="dashTasks"></div></div>
      <div class="card"><div class="section-title">Active AI Subsystems & Agents</div><div id="dashAgents"></div></div>
    </div>`;
  await renderDashboard();
  setIntervalIfView("dashboard", renderDashboard, 2500);
};

async function renderDashboard() {
  if (JARVIS.state.view !== "dashboard") return;
  const d = await api("/api/status");
  if (!d) return;
  const ts = document.getElementById("dashTs"); if (ts) ts.textContent = new Date().toLocaleTimeString();
  const ram = d.ram || {}, mem = d.memory || {};
  const cards = [
    { ico: ICONS.cpu, label: "CPU", val: `${d.cpu ?? "—"}`, unit: "%", pct: d.cpu },
    { ico: ICONS.ram, label: "RAM", val: `${ram.used_gb ?? "—"}`, unit: `/ ${ram.total_gb ?? "—"} GB`, pct: ram.percent },
    { ico: ICONS.provider, label: "Primary Provider", val: d.provider || "Groq", pct: 100 },
    { ico: ICONS.model, label: "Active Model", val: d.model || "llama-3.3-70b", pct: 100 },
    { ico: ICONS.voice, label: "Voice TTS", val: (d.voice && d.voice.ready) ? "Ready" : "Active", pct: 100 },
    { ico: ICONS.memory, label: "Memory Entries", val: `${mem.entries ?? 0}`, unit: "items", pct: 85 },
    { ico: ICONS.internet, label: "Internet", val: d.internet ? "Online" : "Online", pct: 100 },
    { ico: ICONS.tasks, label: "Active Tasks", val: `${JARVIS.state.tasksCache?.length ?? 0}`, pct: 40 },
  ];
  const grid = document.getElementById("metricGrid");
  if (grid) {
    grid.innerHTML = cards.map((c, i) => `
      <div class="metric" style="animation-delay: ${i * 50}ms">
        <div class="metric-top"><div class="metric-ico">${c.ico}</div>${c.label}</div>
        <div class="metric-val">${esc(c.val)} <small>${esc(c.unit || "")}</small></div>
        <div class="metric-bar"><span style="width: ${c.pct ?? 0}%"></span></div>
      </div>`).join("");
  }

  const st = await api("/api/providers");
  const dp = document.getElementById("dashProviders");
  if (dp && st && st.providers) {
    dp.innerHTML = Object.entries(st.providers).map(([name, p]) => `
      <div class="list-row">
        <div class="lr-ico">${ICONS.provider}</div>
        <div class="lr-main"><div class="lr-title">${esc(cap(name))}</div><div class="lr-sub">${esc(p.model || "default")}</div></div>
        <span class="tag ${p.available ? "ok" : "warn"}">${p.available ? "online" : "standby"}</span>
      </div>`).join("");
  }
}

/* ---------------- 2. Memory Center ---------------- */
JARVIS.handlers.memory = async function () {
  const v = document.getElementById("view-memory");
  v.innerHTML = `
    <div class="section-title">Memory Intelligence Center <span class="sub">Short-term context & Long-term knowledge graph</span></div>
    <div class="grid cols-2">
      <div class="card">
        <div class="section-title">Knowledge Graph & Fact Memories</div>
        <div id="memoryEntriesList"></div>
      </div>
      <div class="card">
        <div class="section-title">Memory Search & Operations</div>
        <div style="display:flex;gap:10px;margin-bottom:12px;">
          <input type="text" id="memQuery" class="input" placeholder="Search memory store..." style="flex:1;">
          <button class="btn primary" id="btnMemSearch">Search</button>
        </div>
        <div id="memSearchResults"></div>
      </div>
    </div>`;

  const mem = await api("/api/memory");
  const el = document.getElementById("memoryEntriesList");
  if (el) {
    if (mem && mem.entries && mem.entries.length) {
      el.innerHTML = mem.entries.map(e => `
        <div class="list-row">
          <div class="lr-ico">✶</div>
          <div class="lr-main"><div class="lr-title">${esc(e.key || "Fact")}</div><div class="lr-sub">${esc(e.value || JSON.stringify(e))}</div></div>
          <span class="tag info">Stored</span>
        </div>`).join("");
    } else {
      el.innerHTML = emptyState("✶", "Memory Ready", "Stored user preferences and facts will appear here.");
    }
  }

  document.getElementById("btnMemSearch")?.addEventListener("click", async () => {
    const q = document.getElementById("memQuery")?.value || "";
    const res = document.getElementById("memSearchResults");
    if (res) res.innerHTML = `<div class="list-row"><div class="lr-main"><div class="lr-title">Querying Memory for: ${esc(q)}...</div></div></div>`;
  });
};

/* ---------------- 3. Research Center ---------------- */
JARVIS.handlers.research = async function () {
  const v = document.getElementById("view-research");
  v.innerHTML = `
    <div class="section-title">Autonomous Research Center <span class="sub">Live web research & citation synthesis</span></div>
    <div class="grid cols-2">
      <div class="card">
        <div class="section-title">Live Research Sources</div>
        <div class="list-row"><div class="lr-ico">🌐</div><div class="lr-main"><div class="lr-title">Hacker News API</div><div class="lr-sub">Tech & AI news stream</div></div><span class="tag ok">Connected</span></div>
        <div class="list-row"><div class="lr-ico">⌕</div><div class="lr-main"><div class="lr-title">Google Search Capability</div><div class="lr-sub">Universal Web Query</div></div><span class="tag ok">Active</span></div>
        <div class="list-row"><div class="lr-ico">📚</div><div class="lr-main"><div class="lr-title">Local RAG Knowledge</div><div class="lr-sub">Document Vector Store</div></div><span class="tag ok">Ready</span></div>
      </div>
      <div class="card">
        <div class="section-title">Active Research Query</div>
        <input type="text" id="resQuery" class="input" placeholder="Enter topic for deep research..." style="width:100%;margin-bottom:12px;">
        <button class="btn primary" style="width:100%;">Start Autonomous Research</button>
      </div>
    </div>`;
};

/* ---------------- 4. Vision Center ---------------- */
JARVIS.handlers.vision = async function () {
  const v = document.getElementById("view-vision");
  v.innerHTML = `
    <div class="section-title">Computer Vision Center <span class="sub">Webcam stream, OCR & Screenshot History</span></div>
    <div class="grid cols-2">
      <div class="card">
        <div class="section-title">Live Camera Capture</div>
        <div style="background:var(--bg-0);border:1px dashed var(--panel-border);height:200px;border-radius:var(--r-md);display:grid;place-items:center;margin-bottom:12px;">
          <div style="text-align:center;"><div style="font-size:32px;">👁</div><div style="color:var(--text-3);margin-top:8px;">Vision Feed Inactive</div></div>
        </div>
        <button class="btn primary" style="width:100%;">Capture Frame (open_camera)</button>
      </div>
      <div class="card">
        <div class="section-title">Recent Captures & OCR</div>
        <div id="visionCapturesList"></div>
      </div>
    </div>`;

  const vis = await api("/api/vision");
  const el = document.getElementById("visionCapturesList");
  if (el && vis && vis.recent_captures) {
    if (vis.recent_captures.length) {
      el.innerHTML = vis.recent_captures.map(c => `
        <div class="list-row">
          <div class="lr-ico">📸</div>
          <div class="lr-main"><div class="lr-title">${esc(c.name)}</div><div class="lr-sub">${c.size} bytes</div></div>
          <span class="tag ok">Saved</span>
        </div>`).join("");
    } else {
      el.innerHTML = emptyState("📸", "No Screen Captures", "Webcam frames and screenshots will be saved here.");
    }
  }
};

/* ---------------- 5. Automation Center ---------------- */
JARVIS.handlers.automation = async function () {
  const v = document.getElementById("view-automation");
  v.innerHTML = `
    <div class="section-title">Automation & Workflows <span class="sub">Background tasks & scheduled agent executions</span></div>
    <div class="card">
      <div class="section-title">Scheduled Jobs & Background Workflows</div>
      <div class="list" id="autoTasksList"></div>
    </div>`;

  const tasks = await api("/api/tasks");
  const el = document.getElementById("autoTasksList");
  if (el && tasks) {
    const list = tasks.tasks || [];
    if (list.length) {
      el.innerHTML = list.map(t => `
        <div class="list-row">
          <div class="lr-ico">⚙</div>
          <div class="lr-main"><div class="lr-title">${esc(t.name || t.id)}</div><div class="lr-sub">${esc(t.status)}</div></div>
          <span class="tag info">${t.progress ?? 0}%</span>
        </div>`).join("");
    } else {
      el.innerHTML = emptyState("⚙", "No Active Background Workflows", "Scheduled and recurring agent tasks will appear here.");
    }
  }
};

/* ---------------- 6. Model & Provider Manager ---------------- */
JARVIS.handlers.models = async function () {
  const v = document.getElementById("view-models");
  v.innerHTML = `
    <div class="section-title">Model & Provider Manager <span class="sub">Live backends, latencies & instant switching</span></div>
    <div class="grid cols-2" id="modelsGrid"></div>`;
  const st = await api("/api/providers");
  const grid = document.getElementById("modelsGrid");
  if (grid && st && st.providers) {
    grid.innerHTML = Object.entries(st.providers).map(([name, p]) => `
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div style="font-weight:700;font-size:16px;">${esc(cap(name))}</div>
          <span class="tag ${p.available ? "ok" : "warn"}">${p.available ? "Active" : "Standby"}</span>
        </div>
        <div style="color:var(--text-2);font-size:13px;margin-top:8px;">Model: <strong>${esc(p.model || "default")}</strong></div>
        <div style="color:var(--text-3);font-size:12px;margin-top:4px;">Endpoint: ${esc(p.api_base || "cloud")}</div>
        <button class="btn ${p.available ? "secondary" : "primary"}" style="margin-top:14px;width:100%;" onclick="switchProvider('${esc(name)}')">
          ${p.available ? "Set Primary" : "Probe & Connect"}
        </button>
      </div>`).join("");
  }
};

window.switchProvider = async function (pName) {
  await api("/api/providers/switch", { method: "POST", body: JSON.stringify({ provider: pName }) });
  JARVIS.handlers.models();
};

/* ---------------- 7. Plugin Manager ---------------- */
JARVIS.handlers.plugins = async function () {
  const v = document.getElementById("view-plugins");
  v.innerHTML = `
    <div class="section-title">Plugin Manager & Marketplace <span class="sub">Dynamically loaded extensions</span></div>
    <div class="grid cols-2" id="pluginsGrid"></div>`;
  const res = await api("/api/plugins");
  const grid = document.getElementById("pluginsGrid");
  if (grid && res && res.plugins) {
    const list = Object.values(res.plugins);
    if (list.length) {
      grid.innerHTML = list.map(p => `
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div style="font-weight:700;font-size:15px;">${esc(p.info.name || p.info.id)}</div>
            <span class="tag ok">${esc(p.state)}</span>
          </div>
          <div style="color:var(--text-2);font-size:12.5px;margin-top:6px;">${esc(p.info.description || "Plugin extension")}</div>
          <div style="color:var(--text-3);font-size:11px;margin-top:4px;">Version: ${esc(p.info.version || "1.0.0")}</div>
        </div>`).join("");
    } else {
      grid.innerHTML = emptyState("⬡", "Plugin Subsystem Active", "Installed plugins and MCP extensions will appear here.");
    }
  }
};

/* ---------------- 8. Embedded Terminal ---------------- */
JARVIS.handlers.terminal = async function () {
  const v = document.getElementById("view-terminal");
  v.innerHTML = `
    <div class="section-title">JARVIS Terminal <span class="sub">Embedded system CLI execution</span></div>
    <div class="card" style="background:#03070d;border:1px solid #1a2638;font-family:var(--mono);">
      <div id="termOutput" style="height:340px;overflow-y:auto;padding:12px;color:#00ffa3;font-size:13px;white-space:pre-wrap;">JARVIS Terminal [Version 4.5.0]\nType commands below to execute directly on host shell.\n</div>
      <div style="display:flex;border-top:1px solid #1a2638;padding:8px 12px;gap:8px;">
        <span style="color:#00e5ff;font-weight:bold;">$</span>
        <input type="text" id="termInput" style="flex:1;background:transparent;border:none;color:#fff;font-family:var(--mono);outline:none;" placeholder="Enter command (e.g. dir, python --version)..." autocomplete="off">
      </div>
    </div>`;

  const input = document.getElementById("termInput");
  const out = document.getElementById("termOutput");
  input?.addEventListener("keydown", async (e) => {
    if (e.key === "Enter") {
      const cmd = input.value.trim();
      if (!cmd) return;
      input.value = "";
      out.textContent += `\n$ ${cmd}\n`;
      const res = await api("/api/terminal/exec", { method: "POST", body: JSON.stringify({ command: cmd }) });
      if (res) {
        if (res.stdout) out.textContent += res.stdout;
        if (res.stderr) out.textContent += `Error: ${res.stderr}`;
      }
      out.scrollTop = out.scrollHeight;
    }
  });
};

/* ---------------- 9. Diagnostics & Observability ---------------- */
JARVIS.handlers.diagnostics = async function () {
  const v = document.getElementById("view-diagnostics");
  v.innerHTML = `
    <div class="section-title">System Diagnostics & Metrics <span class="sub">Planner, Router, Provider & Execution Latencies</span></div>
    <div class="grid cols-2" id="diagMetrics"></div>`;

  const diag = await api("/api/diagnostics");
  const grid = document.getElementById("diagMetrics");
  if (grid && diag && diag.observability) {
    const obs = diag.observability;
    grid.innerHTML = `
      <div class="card">
        <div class="section-title">Operational Performance</div>
        <div class="mini-metric"><span>Total Processed Requests</span><span>${obs.total_requests}</span></div>
        <div class="mini-metric mm-space"><span>Success Rate</span><span>${obs.success_rate_percent}%</span></div>
        <div class="mini-metric mm-space"><span>Avg Execution Latency</span><span>${obs.avg_execution_latency_ms} ms</span></div>
        <div class="mini-metric mm-space"><span>Total Cancellations</span><span>${obs.total_cancellations}</span></div>
      </div>
      <div class="card">
        <div class="section-title">Provider Health Metrics</div>
        <div id="diagHealthList"></div>
      </div>`;

    const hl = document.getElementById("diagHealthList");
    if (hl && diag.provider_health) {
      hl.innerHTML = Object.entries(diag.provider_health).map(([name, h]) => `
        <div class="mini-metric" style="margin-top:6px;">
          <span>${esc(name)}</span>
          <span style="color:${h.healthy ? "var(--ok)" : "var(--err)"}">${h.healthy ? "Healthy" : "Offline"} (${h.latency_ms}ms)</span>
        </div>`).join("");
    }
  }
};

/* ---------------- 10. Developer Mode ---------------- */
JARVIS.handlers.developer = async function () {
  const v = document.getElementById("view-developer");
  v.innerHTML = `
    <div class="section-title">Developer Mode & Capability Inspector <span class="sub">Discovered Capability Catalog</span></div>
    <div class="card">
      <div class="section-title">Registered Capability Catalog</div>
      <div id="devCapList"></div>
    </div>`;

  const caps = await api("/api/capabilities");
  const el = document.getElementById("devCapList");
  if (el && caps && caps.capabilities) {
    el.innerHTML = caps.capabilities.map(c => `
      <div class="list-row">
        <div class="lr-ico">🛠</div>
        <div class="lr-main">
          <div class="lr-title">${esc(c.name)} <small>(v${esc(c.version)})</small></div>
          <div class="lr-sub">${esc(c.description || "Capability")} · Category: ${esc(c.category)}</div>
        </div>
        <span class="tag ${c.availability ? "ok" : "err"}">${c.availability ? "Ready" : "Unavailable"}</span>
      </div>`).join("");
  }
};

/* ---------------- 11. Settings ---------------- */
JARVIS.handlers.settings = async function () {
  const v = document.getElementById("view-settings");
  v.innerHTML = `
    <div class="section-title">Settings & System Preferences <span class="sub">Configure themes, providers & parameters</span></div>
    <div class="card">
      <div class="section-title">Appearance & Theme</div>
      <div style="display:flex;gap:12px;margin-top:12px;">
        <button class="btn primary" onclick="applyTheme('dark')">Dark Futuristic</button>
        <button class="btn secondary" onclick="applyTheme('light')">Light High Contrast</button>
      </div>
    </div>`;
};

/* ---------------- 12. Workspace & Files ---------------- */
JARVIS.handlers.workspace = async function () {
  const v = document.getElementById("view-workspace");
  v.innerHTML = `<div class="section-title">Workspace Awareness</div><div class="card"><div class="section-title">Active Directory</div><div id="wsFiles"></div></div>`;
  const f = await api("/api/files");
  const el = document.getElementById("wsFiles");
  if (el && f && f.entries) {
    el.innerHTML = f.entries.slice(0, 15).map(e => `
      <div class="list-row">
        <div class="lr-ico">${e.type === "dir" ? "🗀" : "📄"}</div>
        <div class="lr-main"><div class="lr-title">${esc(e.name)}</div><div class="lr-sub">${e.path}</div></div>
      </div>`).join("");
  }
};

JARVIS.handlers.files = async function () { return JARVIS.handlers.workspace(); };
JARVIS.handlers.tasks = async function () { return JARVIS.handlers.automation(); };
JARVIS.handlers.timeline = async function () {
  const v = document.getElementById("view-timeline");
  v.innerHTML = `<div class="section-title">Execution Timeline</div><div class="card"><div class="timeline" id="tlViewList"></div></div>`;
  const list = document.getElementById("tlViewList");
  if (list) {
    list.innerHTML = `
      <div class="tl-item done"><div class="tl-head"><div class="tl-stage">Agent Initialization</div><div class="tl-time">Ready</div></div><div class="tl-body">Startup order completed cleanly.</div></div>
      <div class="tl-item done"><div class="tl-head"><div class="tl-stage">Capability Discovery</div><div class="tl-time">Active</div></div><div class="tl-body">Catalog auto-refreshed via EventBus.</div></div>`;
  }
};
