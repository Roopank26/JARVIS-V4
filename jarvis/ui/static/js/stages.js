/* ============================================================
   JARVIS — Reasoning stage visualizer
   Cinematic stage transitions with glow and energy
   ==================================== */
"use strict";

const STAGES = [
  { id: "thinking", label: "Thinking", ico: "◌" },
  { id: "planning", label: "Planning", ico: "▤" },
  { id: "searching_memory", label: "Searching Memory", ico: "✶" },
  { id: "searching_knowledge", label: "Searching Knowledge", ico: "✸" },
  { id: "selecting_tools", label: "Selecting Tools", ico: "⚙" },
  { id: "executing", label: "Executing", ico: "↻" },
  { id: "observing", label: "Observing", ico: "◉" },
  { id: "generating", label: "Generating Response", ico: "✦" },
  { id: "complete", label: "Completed", ico: "✓" },
];
const STAGE_MAP = {
  thinking: "thinking", planning: "planning",
  searching_memory: "searching_memory", searching_knowledge: "searching_knowledge",
  selecting_tools: "selecting_tools", executing: "executing", observing: "observing",
  generating: "generating", complete: "complete",
};
const STAGE_LABEL = Object.fromEntries(STAGES.map(s => [s.id, s.label]));

let activeStage = null;

function renderStages() {
  const box = document.getElementById("stages");
  if (!box) return;
  const newHTML = STAGES.map((s, i) => {
    const state = JARVIS.state.stages[s.id] || "";
    const cls = state === "active" ? "active" : state === "done" ? "done" : "";
    return `<div class="stage ${cls}" data-stage="${s.id}" style="animation: fadeIn 0.4s var(--ease) ${i * 38}ms backwards"><span class="s-ico">${s.ico}</span>${s.label}</div>`;
  }).join("");

  if (box.innerHTML !== newHTML) {
    box.innerHTML = newHTML;
  }
}

function setStageRaw(id, status) {
  if (!STAGE_MAP[id]) return;
  const mapped = STAGE_MAP[id];
  JARVIS.state.stages[mapped] = status;
  if (status === "active") {
    Object.keys(JARVIS.state.stages).forEach(k => {
      if (JARVIS.state.stages[k] === "active" && k !== mapped) JARVIS.state.stages[k] = "done";
    });
    activeStage = mapped;
    const sec = document.querySelector(".ai-core-section");
    if (sec) {
      sec.classList.remove("thinking", "listening", "speaking");
      sec.classList.add("thinking");
    }
    const st = document.getElementById("aiCoreStatus");
    if (st) {
      st.textContent = STAGE_LABEL[mapped] + "…";
      st.style.animation = "none";
      st.offsetHeight;
      st.style.animation = "fadeIn 0.35s var(--ease)";
    }
  } else if (status === "done") {
    const sec = document.querySelector(".ai-core-section");
    if (sec) sec.classList.remove("thinking");
  }
  renderStages();
}

function onStage(id) {
  if (id === "complete") {
    Object.keys(JARVIS.state.stages).forEach(k => { if (k !== "complete") JARVIS.state.stages[k] = "done"; });
    JARVIS.state.stages.complete = "done";
    const sec = document.querySelector(".ai-core-section"); if (sec) sec.classList.remove("thinking");
    const st = document.getElementById("aiCoreStatus"); if (st) st.textContent = "Online · Ready";
    if (typeof sending !== "undefined") sending = false;
    setAiCoreState("idle");
  } else {
    setStageRaw(id, "active");
    setAiCoreState("thinking");
  }
  renderRightAgents();
}

function resetStages() {
  JARVIS.state.stages = {};
  JARVIS.state.plan = null;
  JARVIS.state.steps = [];
  renderStages();
}

function renderRightAgents() {
  const box = document.getElementById("execAgents");
  if (!box) return;
  const busy = activeStage && activeStage !== "complete";
  const agents = JARVIS.state.agents.length ? JARVIS.state.agents : ["Planner", "Memory", "Tool", "Voice"];
  box.innerHTML = agents.slice(0, 5).map(a => {
    const name = typeof a === "string" ? a : (a.name || a.role || "Agent");
    return `<span class="ea ${busy ? "busy" : ""}">${esc(name)}</span>`;
  }).join("");
}
