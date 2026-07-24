/* ============================================================
   JARVIS — Ambient background (cinematic particle network)
   Animated grid, energy field, floating particles, neural lines,
   slow fog, radar sweep. Reacts to AI Core state.
   ============================================================ */
(function () {
  "use strict";
  const canvas = document.getElementById("bgCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  let w = 0, h = 0, dpr = Math.min(window.devicePixelRatio || 1, 2);
  let particles = [], raf = null, running = true;
  let gridAlpha = 0.035;
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function accent() {
    const v = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim();
    return v || "#00e5ff";
  }
  function accent2() {
    const v = getComputedStyle(document.documentElement).getPropertyValue("--accent-2").trim();
    return v || "#7c5cff";
  }
  function resize() {
    w = canvas.width = Math.floor(window.innerWidth * dpr);
    h = canvas.height = Math.floor(window.innerHeight * dpr);
  }
  function make() {
    const count = prefersReducedMotion ? 14 : Math.min(60, Math.floor((window.innerWidth * window.innerHeight) / 28000));
    particles = Array.from({ length: count }, () => ({
      x: Math.random() * w, y: Math.random() * h,
      vx: (Math.random() - 0.5) * (prefersReducedMotion ? 0.08 : 0.22) * dpr,
      vy: (Math.random() - 0.5) * (prefersReducedMotion ? 0.08 : 0.22) * dpr,
      r: (Math.random() * 1.6 + 0.8) * dpr,
      phase: Math.random() * Math.PI * 2,
      pulse: Math.random() * Math.PI * 2,
    }));
  }
  function step(ts) {
    if (!running) return;
    const col = accent();
    const col2 = accent2();
    ctx.clearRect(0, 0, w, h);
    const time = ts || 0;

    /* Animated grid */
    const gridSize = 60 * dpr;
    ctx.globalAlpha = gridAlpha;
    ctx.strokeStyle = col;
    ctx.lineWidth = 1 * dpr;
    const offsetX = (time * 0.005) % gridSize;
    const offsetY = (time * 0.008) % gridSize;
    for (let x = -gridSize + offsetX; x < w + gridSize; x += gridSize) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
    for (let y = -gridSize + offsetY; y < h + gridSize; y += gridSize) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }
    ctx.globalAlpha = 1;

    /* Slow aurora fog bands */
    if (!prefersReducedMotion) {
      const fogA = ctx.createLinearGradient(0, 0, w, h);
      fogA.addColorStop(0, 'transparent');
      fogA.addColorStop(0.5, col + '0a');
      fogA.addColorStop(1, 'transparent');
      ctx.globalAlpha = 0.18 + Math.sin(time * 0.00018) * 0.07;
      ctx.fillStyle = fogA;
      ctx.fillRect(0, 0, w, h);

      const fogB = ctx.createLinearGradient(w, 0, 0, h);
      fogB.addColorStop(0, 'transparent');
      fogB.addColorStop(0.5, col2 + '08');
      fogB.addColorStop(1, 'transparent');
      ctx.globalAlpha = 0.14 + Math.cos(time * 0.00022) * 0.06;
      ctx.fillStyle = fogB;
      ctx.fillRect(0, 0, w, h);
      ctx.globalAlpha = 1;
    }

    /* Radar sweep (subtle) */
    if (!prefersReducedMotion) {
      const cx = w * 0.5, cy = h * 0.5, maxR = Math.hypot(w, h) * 0.5;
      const angle = (time * 0.0004) % (Math.PI * 2);
      const grad = ctx.createConicalGradient ? null : ctx.createRadialGradient(cx, cy, 0, cx, cy, maxR);
      if (grad) {
        grad.addColorStop(0, 'transparent');
        grad.addColorStop(0.8, 'transparent');
        grad.addColorStop(1, col + '06');
      }
      ctx.globalAlpha = 0.06 + Math.sin(time * 0.001) * 0.02;
      ctx.fillStyle = grad || 'transparent';
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, maxR, angle, angle + 0.4);
      ctx.closePath();
      ctx.fill();
      ctx.globalAlpha = 1;
    }

    /* Neural-like subtle lines */
    if (!prefersReducedMotion && particles.length > 3) {
      ctx.globalAlpha = 0.035;
      ctx.strokeStyle = col;
      ctx.lineWidth = 1 * dpr;
      for (let k = 0; k < 3; k++) {
        const i = Math.floor(Math.random() * particles.length);
        const p = particles[i];
        const j = (i + Math.floor(particles.length / 4)) % particles.length;
        const q = particles[j];
        const dx = q.x - p.x, dy = q.y - p.y;
        const d = Math.hypot(dx, dy);
        if (d < w * 0.55) {
          ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
        }
      }
      ctx.globalAlpha = 1;
    }

    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > w) p.vx *= -1;
      if (p.y < 0 || p.y > h) p.vy *= -1;

      for (let j = i + 1; j < particles.length; j++) {
        const q = particles[j], dx = p.x - q.x, dy = p.y - q.y, d = Math.hypot(dx, dy);
        if (d < 130 * dpr) {
          const alpha = (1 - d / (130 * dpr)) * 0.14;
          ctx.globalAlpha = alpha;
          ctx.strokeStyle = d % 3 < 1 ? col2 : col;
          ctx.lineWidth = (1 - d / (130 * dpr)) * 1.4 * dpr;
          ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
        }
      }

      /* Subtle glow on particles */
      const glow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 3);
      glow.addColorStop(0, col + '38');
      glow.addColorStop(1, col + '00');
      ctx.globalAlpha = 0.35 + Math.sin(time * 0.0009 + p.phase) * 0.18;
      ctx.fillStyle = glow;
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r * 3, 0, Math.PI * 2); ctx.fill();

      /* Core */
      ctx.globalAlpha = 0.65;
      ctx.fillStyle = col;
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill();
    }
    ctx.globalAlpha = 1;
    raf = requestAnimationFrame(step);
  }
  function start() { if (!raf) { running = true; step(0); } }
  function stop() { running = false; if (raf) cancelAnimationFrame(raf); raf = null; }

  resize(); make(); start();
  window.addEventListener("resize", () => { resize(); make(); });
  document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));

  /* React to AI core state changes */
  function setState(state) {
    if (state === "thinking" || state === "listening" || state === "speaking") {
      gridAlpha = 0.065;
      particles.forEach(p => { p.vx *= 1.6; p.vy *= 1.6; });
    } else {
      gridAlpha = 0.035;
    }
  }
  window.__jarvisBg = { start, stop, setState };
})();
