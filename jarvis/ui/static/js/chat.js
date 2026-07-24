/* ============================================================
   JARVIS — Chat experience
   Cinematic streaming, markdown, syntax highlight, suggestions, voice
   Word-by-word reveal, AI Core reactive states, energy waves
   ==================================== */
"use strict";

let chatBuilt = false;
let streamingMsg = null;
let conversation = [];
let suggestionTimer = null;
let attachments = [];
let isStreaming = false;

function buildChat() {
  if (chatBuilt) return;
  chatBuilt = true;
  const v = document.getElementById("view-chat");
  v.innerHTML = `
    <div class="chat-container">
      <div class="chat-side">
        <div class="card" style="padding:14px">
          <div class="section-title" style="margin-bottom:10px">Conversations</div>
          <div class="composer-toolbar" style="padding:0">
            <span class="ct" id="newChat">＋ New</span>
            <span class="ct" id="pinToggle">📌 Pin</span>
            <span class="ct" id="searchChat">🔍</span>
          </div>
          <div class="chat-list" id="chatList" style="margin-top:10px;max-height:200px"></div>
        </div>
        <div class="card" style="padding:16px;flex:1;overflow:auto;display:flex;flex-direction:column;align-items:center">
          <div class="section-title" style="margin-bottom:10px;align-self:flex-start">AI Core</div>
          <div class="ai-core-section" id="aiCoreSection">
            <div class="ai-core-canvas">
              <div class="ai-core-ring"></div><div class="ai-core-ring"></div>
              <div class="ai-core-ring"></div><div class="ai-core-ring"></div>
              <div class="ai-core-orbit"></div>
              <div class="ai-core-orbit"></div>
              <div class="ai-core-center" id="aiCoreCenter">◈</div>
            </div>
            <div class="ai-core-label">AI Core</div>
            <div class="ai-core-status" id="aiCoreStatus">Online · Ready</div>
            <div class="exec-agents" id="execAgents"></div>
          </div>
        </div>
      </div>
      <div class="card chat-card" style="display:flex;flex-direction:column;padding:0;overflow:hidden;position:relative">
        <div class="stages" id="stages" style="padding:16px 16px 0"></div>
        <div class="messages" id="messages" style="padding:16px"></div>
        <div class="sugg-box" id="suggBox"></div>
        <div class="attach-tray" id="attachTray"></div>
        <div class="composer-area" style="padding:14px 16px 16px">
          <div class="composer-toolbar">
            <span class="ct" id="attachBtn">📎 Attach</span>
            <span class="ct" id="voiceBtn">🎤 Voice</span>
            <span class="ct" id="exportChat">⤓ Export</span>
          </div>
          <div class="composer-inner">
            <div class="composer-input-wrap">
              <textarea id="chatInput" class="composer-input" rows="1" placeholder="Ask JARVIS anything…  (Ctrl+Shift+P for commands)" autocomplete="off"></textarea>
            </div>
            <div class="composer-actions">
              <button class="btn primary" id="sendBtn">Send ↵</button>
              <button class="btn sm danger" id="stopBtn" style="display:none">■ Stop</button>
            </div>
          </div>
        </div>
        <div class="drop-zone" id="dropZone"><div class="drop-inner">⬇ Drop files to attach</div></div>
        <input type="file" id="fileInput" multiple style="display:none" />
      </div>
    </div>`;

  renderStages();
  const input = document.getElementById("chatInput");
  const send = () => sendChat();
  document.getElementById("sendBtn").onclick = send;
  const stopBtn = document.getElementById("stopBtn");
  if (stopBtn) stopBtn.onclick = () => {
    if (streamingMsg) { finalizeStream(); sendWS("interrupt", {}); showToast("Stopped", "Generation interrupted", "warn"); }
    sending = false;
    setAiCoreState("idle");
  };
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });
  input.addEventListener("input", () => {
    input.style.height = "auto"; input.style.height = Math.min(160, input.scrollHeight) + "px";
    if (suggestionTimer) clearTimeout(suggestionTimer);
    suggestionTimer = setTimeout(maybeSuggest, 600);
  });
  document.getElementById("voiceBtn").onclick = () => { input.focus(); sendWS("voice_toggle", {}); };
  document.getElementById("attachBtn").onclick = () => document.getElementById("fileInput").click();
  document.getElementById("fileInput").onchange = (e) => { handleFiles(e.target.files); e.target.value = ""; };
  const card = document.querySelector("#view-chat .chat-card");
  if (card) {
    card.addEventListener("dragover", (e) => { e.preventDefault(); card.classList.add("drag-over"); });
    card.addEventListener("dragleave", () => card.classList.remove("drag-over"));
    card.addEventListener("drop", (e) => { e.preventDefault(); card.classList.remove("drag-over"); handleFiles(e.dataTransfer.files); });
    card.style.animation = 'none';
    card.offsetHeight;
    card.style.animation = 'scaleInElastic 0.7s var(--ease-spring)';
  }
  function handleFiles(files) {
    if (!files || !files.length) return;
    Array.from(files).forEach(f => {
      const reader = new FileReader();
      reader.onload = () => attachments.push({ name: f.name, size: f.size, type: f.type, dataUrl: reader.result });
      reader.readAsDataURL(f);
    });
    renderAttachments();
  }
  function removeAttachment(i) { attachments.splice(i, 1); renderAttachments(); }
  function renderAttachments() {
    const tray = document.getElementById("attachTray"); if (!tray) return;
    if (!attachments.length) { tray.innerHTML = ""; return; }
    tray.innerHTML = attachments.map((a, i) => `<div class="att-chip"><span class="att-name">${esc(a.name)}</span><span class="att-size">${(a.size/1024).toFixed(1)} KB</span><span class="att-rm" data-i="${i}">✕</span></div>`).join("");
    tray.querySelectorAll(".att-rm").forEach(b => b.onclick = () => removeAttachment(+b.dataset.i));
  }
  document.getElementById("newChat").onclick = () => { conversation = []; document.getElementById("messages").innerHTML = ""; resetStages(); renderSuggestions(); setAiCoreState("idle"); };
  document.getElementById("exportChat").onclick = exportChat;
  renderSuggestions();
}

/* ---------- Sending ---------- */
let sending = false;
function sendChat() {
  if (sending) return;
  const input = document.getElementById("chatInput");
  const text = input.value.trim();
  if (!text && !attachments.length) return;
  sending = true;
  input.value = ""; input.style.height = "auto";
  const payload = text;
  if (attachments.length) {
    const names = attachments.map(a => a.name).join(", ");
    onUserMessage((text ? text + "\n" : "") + `📎 Attached: ${names}`);
    attachments = []; renderAttachments();
  } else {
    onUserMessage(text);
  }
  resetStages();
  setStageRaw("thinking", "active");
  setAiCoreState("thinking");
  const wsOk = JARVIS.ws && JARVIS.ws.readyState === 1;
  if (wsOk) {
    sendWS("chat", { text: payload });
  } else {
    api("/api/chat", { method: "POST", body: JSON.stringify({ text: payload }) }).then(r => {
      sending = false;
      setAiCoreState("idle");
      if (r && r.response && streamingMsg == null) onAssistantMessage(r.response);
    }).catch(err => { console.warn("Chat send error", err); sending = false; setAiCoreState("idle"); });
  }
}

function onUserMessage(text) {
  buildChat();
  const last = conversation[conversation.length - 1];
  if (last && last.role === "user" && last.content === text) return;
  conversation.push({ role: "user", content: text });
  addMessage("user", text);
  const box = document.getElementById("suggBox"); if (box) box.innerHTML = "";
}

let assistantBuffer = "";
function onAssistantMessage(text) {
  buildChat();
  if (streamingMsg) { finalizeStream(); }
  const last = conversation[conversation.length - 1];
  if (last && last.role === "assistant" && last.content === text) return;
  assistantBuffer = "";
  conversation.push({ role: "assistant", content: text });
  addMessage("assistant", text);
  renderSuggestions();
  setAiCoreState("idle");
}
function maybeStream() {
  const stopBtn = document.getElementById("stopBtn");
  if (stopBtn) stopBtn.style.display = isStreaming ? "inline-flex" : "none";
}
function onToken(token) {
  buildChat();
  if (!streamingMsg) {
    streamingMsg = createStreamingMsg();
    assistantBuffer = "";
    isStreaming = true;
    maybeStream();
    setAiCoreState("thinking");
  }
  assistantBuffer += token;
  const html = renderMarkdown(assistantBuffer) + `<span class="typing"><span></span><span></span><span></span></span>`;
  streamingMsg.body.innerHTML = html;

  streamingMsg.body.querySelectorAll('p:not(.fade-applied), li:not(.fade-applied), blockquote:not(.fade-applied)').forEach((el, i) => {
    el.classList.add('fade-applied');
    el.style.animation = `wordFadeIn 0.3s var(--ease) ${i * 28}ms backwards`;
  });

  streamingMsg.el.scrollIntoView({ behavior: "smooth", block: "end" });
}
function finalizeStream() {
  if (!streamingMsg) return;
  assistantBuffer = assistantBuffer.trim();
  streamingMsg.body.innerHTML = renderMarkdown(assistantBuffer);
  streamingMsg.el.classList.remove("streaming-cursor");
  attachCodeButtons(streamingMsg.body);
  conversation.push({ role: "assistant", content: assistantBuffer });
  streamingMsg = null;
  isStreaming = false;
  maybeStream();
  renderSuggestions();
  setAiCoreState("idle");
}

/* ---------- Message DOM ---------- */
function addMessage(role, text, animate = true) {
  const box = document.getElementById("messages");
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  if (!animate) el.style.animation = 'none';
  el.innerHTML = `
    <div class="msg-avatar">${role === "user" ? "👤" : "◈"}</div>
    <div class="msg-bubble">${renderMarkdown(text)}</div>`;
  box.appendChild(el);
  const body = el.querySelector(".msg-bubble");
  attachCodeButtons(body);
  addMsgActions(el, role, text);
  box.scrollTo({ top: box.scrollHeight, behavior: 'smooth' });
  return { el, body };
}
function createStreamingMsg() {
  const box = document.getElementById("messages");
  const el = document.createElement("div");
  el.className = "msg assistant streaming-cursor";
  el.innerHTML = `<div class="msg-avatar">◈</div><div class="msg-bubble"></div>`;
  box.appendChild(el);
  return { el, body: el.querySelector(".msg-bubble") };
}

function addMsgActions(el, role, text) {
  const bubble = el.querySelector(".msg-bubble");
  const actions = document.createElement("div");
  actions.className = "msg-actions";
  actions.innerHTML = `<span class="ma" data-a="copy">Copy</span>` +
    (role === "assistant" ? `<span class="ma" data-a="react">👍</span><span class="ma" data-a="react2">👎</span><span class="ma" data-a="regen">Regenerate</span>` : `<span class="ma" data-a="edit">Edit</span>`);
  bubble.after(actions);
  actions.querySelectorAll(".ma").forEach(a => a.onclick = () => {
    const kind = a.dataset.a;
    if (kind === "copy") { navigator.clipboard.writeText(text); showToast("Copied", "Message copied to clipboard", "ok"); }
    else if (kind === "edit") editMessage(el, text);
    else if (kind === "regen") { resetStages(); setStageRaw("thinking", "active"); sendWS("chat", { text: "regenerate your previous answer" }); setAiCoreState("thinking"); }
    else if (kind.startsWith("react")) showToast("Reaction", "Thanks for the feedback!", "ok");
  });
}
function editMessage(el, text) {
  const bubble = el.querySelector(".msg-bubble");
  const ta = document.createElement("textarea");
  ta.className = "composer-input"; ta.value = text; ta.style.minHeight = "80px"; ta.style.width = "100%";
  bubble.replaceWith(ta);
  const save = document.createElement("div");
  save.className = "msg-actions"; save.innerHTML = `<span class="ma" data-a="save">Save</span><span class="ma" data-a="cancel">Cancel</span>`;
  ta.after(save);
  save.querySelector('[data-a="save"]').onclick = () => {
    const nv = ta.value.trim();
    conversation = conversation.filter(m => m.content !== text);
    conversation.push({ role: "user", content: nv });
    ta.replaceWith(Object.assign(document.createElement("div"), { className: "msg-bubble", innerHTML: renderMarkdown(nv) }));
    save.remove();
    resetStages(); setStageRaw("thinking", "active"); sendWS("chat", { text: nv }); setAiCoreState("thinking");
  };
  save.querySelector('[data-a="cancel"]').onclick = () => { ta.replaceWith(bubble); save.remove(); };
}

/* ---------- Export / import ---------- */
function exportChat() {
  if (!conversation.length) { showToast("Export", "Nothing to export yet", "warn"); return; }
  const md = conversation.map(m => `**${m.role === "user" ? "You" : "JARVIS"}:**\n${m.content}`).join("\n\n---\n\n");
  const blob = new Blob([md], { type: "text/markdown" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `jarvis-chat-${Date.now()}.md`; a.click();
  showToast("Exported", "Conversation saved as Markdown", "ok");
}

/* ---------- Suggestions ---------- */
async function maybeSuggest() {
  const v = document.getElementById("chatInput");
  if (!v || v.value.trim().length < 3) return;
  const r = await api("/api/suggestions");
  if (r && r.suggestions) renderSuggestions(r.suggestions.slice(0, 4));
}
async function renderSuggestions(items) {
  const box = document.getElementById("suggBox");
  if (!box) return;
  if (!items) { box.innerHTML = ""; return; }
  box.innerHTML = items.map(s => `<span class="sugg" data-q="${esc(s.title || "")}">${esc(s.title || "")}</span>`).join("");
  box.querySelectorAll(".sugg").forEach(s => s.onclick = () => {
    const q = s.dataset.q;
    const inp = document.getElementById("chatInput");
    if (inp) { inp.value = q; inp.focus(); }
    sendChat();
  });
}
function showSuggestion(data) {
  renderSuggestions([{ title: data.title || "Suggestion" }]);
}

/* ---------- Markdown (lightweight, safe) ---------- */
function renderMarkdown(src) {
  if (!src) return "";
  src = esc(src);
  src = src.replace(/```(\w*)\n([\s\S]*?)```/g, (m, lang, code) =>
    `<pre data-lang="${lang || ""}"><button class="code-copy">Copy</button><code>${code.replace(/\n$/, "")}</code></pre>`);
  src = src.replace(/`([^`]+)`/g, '<code class="inline">$1</code>');
  src = src.replace(/^######\s+(.*)$/gm, "<h6>$1</h6>")
           .replace(/^#####\s+(.*)$/gm, "<h5>$1</h5>")
           .replace(/^####\s+(.*)$/gm, "<h4>$1</h4>")
           .replace(/^###\s+(.*)$/gm, "<h3>$1</h3>")
           .replace(/^##\s+(.*)$/gm, "<h2>$1</h2>")
           .replace(/^#\s+(.*)$/gm, "<h1>$1</h1>");
  src = src.replace(/(?:^\|.*\|\s*$\n?)+/gm, (block) => {
    const rows = block.trim().split("\n");
    if (rows.length < 2) return block;
    const cells = (r) => r.replace(/^\||\|$/g, "").split("|").map(c => `<td>${c.trim()}</td>`).join("");
    const head = `<tr>${cells(rows[0])}</tr>`;
    const body = rows.slice(2).map(r => `<tr>${cells(r)}</tr>`).join("");
    return `<table><thead>${head}</thead><tbody>${body}</tbody></table>`;
  });
  src = src.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
           .replace(/\*([^*]+)\*/g, "<em>$1</em>")
           .replace(/__([^_]+)__/g, "<u>$1</u>");
  src = src.replace(/^\s*[-*]\s+(.*)$/gm, "<li>$1</li>");
  src = src.replace(/(<li>[\s\S]*?<\/li>)+/g, (m) => `<ul>${m}</ul>`);
  src = src.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  src = src.replace(/^>\s+(.*)$/gm, "<blockquote>$1</blockquote>");
  src = src.split(/\n{2,}/).map(p => {
    if (/^\s*<(h\d|ul|ol|pre|table|blockquote)/.test(p)) return p;
    return `<p>${p.replace(/\n/g, "<br>")}</p>`;
  }).join("");
  return src;
}
function attachCodeButtons(scope) {
  scope.querySelectorAll(".code-copy").forEach(b => b.onclick = () => {
    const code = b.parentElement.querySelector("code").innerText;
    navigator.clipboard.writeText(code);
    b.textContent = "Copied ✓"; setTimeout(() => (b.textContent = "Copy"), 1400);
  });
}

/* ---------- Voice waveform ---------- */
let waveRAF = null;
let waveResizeHandler = null;
function initWaveform() {
  if (waveRAF) return;
  const c = document.getElementById("waveCanvas");
  if (!c) return;
  const ctx = c.getContext("2d");
  const resize = () => { c.width = c.offsetWidth * devicePixelRatio; c.height = c.offsetHeight * devicePixelRatio; };
  resize();
  waveResizeHandler = resize;
  window.addEventListener("resize", waveResizeHandler);
  const draw = () => {
    const orb = document.getElementById("voiceOrb");
    const active = orb && (orb.classList.contains("listening") || orb.classList.contains("speaking"));
    ctx.clearRect(0, 0, c.width, c.height);
    const cx = c.width / 2, cy = c.height / 2, n = 30, R = c.width * 0.34;
    const color = (orb && orb.classList.contains("speaking")) ? "#7c5cff" : "#00e5ff";
    const time = Date.now();
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2;
      const amp = active ? (Math.sin(time / 85 + i * 0.9) * 0.5 + 0.5) * 12 + 5 : 3;
      const x1 = cx + Math.cos(a) * R, y1 = cy + Math.sin(a) * R;
      const x2 = cx + Math.cos(a) * (R + amp), y2 = cy + Math.sin(a) * (R + amp);
      ctx.strokeStyle = color; ctx.globalAlpha = active ? 0.95 : 0.28; ctx.lineWidth = 2.2;
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
    }
    ctx.globalAlpha = 1;
    waveRAF = requestAnimationFrame(draw);
  };
  waveRAF = requestAnimationFrame(draw);
}

function stopWaveform() {
  if (waveRAF) { cancelAnimationFrame(waveRAF); waveRAF = null; }
  if (waveResizeHandler) { window.removeEventListener("resize", waveResizeHandler); waveResizeHandler = null; }
}

function stopGeneration() {
  if (streamingMsg) { finalizeStream(); sendWS("interrupt", {}); showToast("Stopped", "Generation interrupted", "warn"); }
  sending = false;
  setAiCoreState("idle");
}
window.stopGeneration = stopGeneration;

JARVIS.handlers.chat = () => { buildChat(); if (!waveRAF) initWaveform(); };
