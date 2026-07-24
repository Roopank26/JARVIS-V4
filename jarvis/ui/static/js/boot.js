/* ============================================================
   JARVIS — Boot
   Cinematic initialization sequence
   ==================================== */
(function () {
  "use strict";

  function boot() {
    if (typeof initShell === "function") initShell();

    /* Set initial AI Core state */
    setTimeout(() => setAiCoreState("idle"), 400);

    // Kick off first data loads
    renderRightPanel();
    loadAgents();
    loadTasks();
    if (typeof loadActivity === "function") loadActivity();

    // Periodic status refresh (drives dashboard + right panel + metrics)
    setInterval(async () => {
      const d = await api("/api/status");
      if (d) { renderStatus(d); }
    }, 2500);

    // Welcome
    setTimeout(() => showToast("JARVIS online", "AI Operating System ready. Press Ctrl+Shift+P to search.", "ok"), 700);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
