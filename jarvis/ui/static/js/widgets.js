/* ============================================================
   JARVIS — Widgets (sparklines, progress, context menu)
   Premium animated sparkline draw, smooth context menu
   ==================================== */
"use strict";

function sparkline(el, data, color) {
  if (!el) return;
  const old = el.querySelector('canvas');
  if (old) old.remove();

  const c = document.createElement('canvas');
  c.width = (el.clientWidth || 200) * (window.devicePixelRatio || 1);
  c.height = 36 * (window.devicePixelRatio || 1);
  c.style.width = "100%"; c.style.height = "36px";
  el.appendChild(c);
  const ctx = c.getContext("2d");
  const max = Math.max(...data, 1), pad = 3;
  const dpr = window.devicePixelRatio || 1;
  const pts = data.map((d, i) => [pad + (c.width/dpr - 2 * pad) * i / (data.length - 1 || 1), c.height/dpr - pad - (c.height/dpr - 2 * pad) * d / max]);

  ctx.beginPath();
  pts.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]));
  ctx.strokeStyle = color || getCss("--accent"); ctx.lineWidth = 2; ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(pts[0][0], c.height/dpr);
  pts.forEach(p => ctx.lineTo(p[0], p[1]));
  ctx.lineTo(pts[pts.length-1][0], c.height/dpr);
  ctx.closePath();
  const grad = ctx.createLinearGradient(0, 0, 0, c.height/dpr);
  const accent = color || getCss("--accent") || "#00e5ff";
  grad.addColorStop(0, accent + '30');
  grad.addColorStop(1, accent + '00');
  ctx.fillStyle = grad;
  ctx.fill();
}

function contextMenu(x, y, items) {
  closeContext();
  const m = document.createElement("div");
  m.className = "ctx-menu";
  m.style.left = x + "px"; m.style.top = y + "px";
  m.innerHTML = items.map((it, i) => it.sep ? `<div class="ctx-sep"></div>` : `<div class="ctx-item" data-i="${i}">${it.icon || ""} ${esc(it.label)}</div>`).join("");
  document.body.appendChild(m);
  m.querySelectorAll(".ctx-item").forEach(el => el.onclick = () => { closeContext(); items[+el.dataset.i].action && items[+el.dataset.i].action(); });

  m.querySelectorAll('.ctx-item').forEach((item, idx) => {
    item.style.opacity = '0';
    item.style.transform = 'translateY(-6px)';
    requestAnimationFrame(() => {
      item.style.transition = `opacity 0.22s var(--ease-spring) ${idx * 28}ms, transform 0.22s var(--ease-spring) ${idx * 28}ms`;
      item.style.opacity = '1';
      item.style.transform = 'translateY(0)';
    });
  });

  document.addEventListener("click", closeContext, { once: true });
}
function closeContext() { document.querySelectorAll(".ctx-menu").forEach(m => m.remove()); }

function getCss(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim() || "#00e5ff"; }
