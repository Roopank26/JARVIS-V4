// ECHOBOUND — Holographic Modern UI Manager
import { soundManager } from '../audio/SoundManager.js';

export class UIManager {
  constructor(callbacks = {}) {
    this.callbacks = callbacks;
    this.memoryPercent = 20;

    this.container = document.getElementById('ui-root');
    this.initDOM();
  }

  initDOM() {
    this.container.innerHTML = `
      <!-- TOP HUD -->
      <div id="hud-top" class="hud-layer">
        <!-- Top Left: Echo Status -->
        <div class="hud-capsule" id="echo-capsule">
          <div class="echo-icon-ring">
            <svg viewBox="0 0 24 24" class="svg-icon">
              <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2" fill="none" opacity="0.4"/>
              <path d="M12 3 A9 9 0 0 1 21 12" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round"/>
              <circle cx="12" cy="12" r="4" fill="currentColor"/>
            </svg>
          </div>
          <div class="echo-text-group">
            <span class="hud-label">TIME ECHOES</span>
            <span class="hud-value" id="hud-echo-count">0 / 1</span>
          </div>
          <div class="echo-slots" id="echo-slots-indicator">
            <span class="slot-dot active"></span>
          </div>
        </div>

        <!-- Top Center: World & Level Title -->
        <div class="hud-center-title" id="hud-title-capsule">
          <span class="world-subtitle" id="hud-world-name">WORLD 1 — FLOATING ISLANDS</span>
          <span class="level-title" id="hud-level-title">Awakening</span>
        </div>

        <!-- Top Right: Memory Sync Progress -->
        <div class="hud-capsule" id="memory-capsule">
          <div class="echo-text-group text-right">
            <span class="hud-label">MEMORY SYNCHRONIZED</span>
            <span class="hud-value" id="hud-memory-val">20%</span>
          </div>
          <div class="memory-ring-wrap">
            <svg class="progress-ring" width="38" height="38">
              <circle class="progress-ring__circle-bg" stroke="rgba(255,255,255,0.15)" stroke-width="3" fill="transparent" r="16" cx="19" cy="19"/>
              <circle id="memory-progress-circle" class="progress-ring__circle" stroke="#00f3ff" stroke-width="3" fill="transparent" r="16" cx="19" cy="19"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- CENTER HUD: RECORDING & REPLAY STATUS -->
      <div id="hud-center-status">
        <!-- Recording capsule -->
        <div id="recording-badge" class="status-badge pulse-red hidden">
          <span class="rec-dot"></span>
          <span class="badge-text" id="rec-status-text">RECORDING 00:00 / 00:25</span>
          <div class="rec-progress-bar">
            <div id="rec-fill" class="fill"></div>
          </div>
        </div>

        <!-- Echo Replay Capsule -->
        <div id="replay-badge" class="status-badge pulse-cyan hidden">
          <span class="echo-pulse-icon">✦</span>
          <span class="badge-text" id="replay-status-text">ECHO 1 REPLAYING</span>
          <div class="rec-progress-bar">
            <div id="replay-fill" class="fill cyan-fill"></div>
          </div>
        </div>
      </div>

      <!-- IN-WORLD INTERACTION PROMPT -->
      <div id="floating-prompt" class="floating-prompt hidden">
        <span class="key-badge" id="prompt-key">E</span>
        <span class="prompt-text" id="prompt-label">ACTIVATE</span>
      </div>

      <!-- BOTTOM CONTROLS HINT BAR -->
      <div id="hud-bottom" class="hud-layer">
        <div class="controls-hint-bar">
          <div class="hint-item"><span class="k">W A S D</span> Move</div>
          <div class="hint-item"><span class="k">SPACE</span> Jump</div>
          <div class="hint-item"><span class="k">SHIFT</span> Sprint</div>
          <div class="hint-item highlight-cyan"><span class="k">R</span> Commit Echo / Rewind</div>
          <div class="hint-item"><span class="k">C</span> Reset Echoes</div>
          <div class="hint-item"><span class="k">E</span> Interact</div>
          <div class="hint-item"><span class="k">ESC</span> Pause</div>
        </div>
      </div>

      <!-- NARRATIVE / LORE DIALOGUE POPUP -->
      <div id="dialogue-overlay" class="dialogue-overlay hidden">
        <div class="dialogue-card">
          <div class="dialogue-portrait">
            <div class="avatar-glow"></div>
            <div class="avatar-rune">✦</div>
          </div>
          <div class="dialogue-content">
            <div class="dialogue-speaker" id="dialogue-speaker">MEMORY RESONANCE</div>
            <div class="dialogue-text" id="dialogue-text">...</div>
            <div class="dialogue-footer">
              <span class="dialogue-continue-hint">Press [E] or Click to Continue</span>
            </div>
          </div>
        </div>
      </div>

      <!-- MAIN MENU OVERLAY -->
      <div id="main-menu" class="menu-overlay">
        <div class="menu-backdrop-art" style="background-image: url('/assets/echobound_keyart.png');"></div>
        <div class="menu-glass-panel">
          <div class="menu-hero-thumb">
            <img src="/assets/echobound_keyart.png" alt="Echobound Neo and Echo Key Art" class="hero-img">
          </div>
          <div class="game-logo-wrapper">
            <h1 class="game-title">ECHOBOUND</h1>
            <div class="game-subtitle">THE WORLD THAT REMEMBERS YOU</div>
            <div class="game-version">V1.0 • POLISHED EDITION</div>
          </div>

          <div class="menu-buttons">
            <button id="btn-start" class="menu-btn primary-glow">
              <span class="btn-icon">▶</span>
              <span class="btn-text">START JOURNEY</span>
            </button>
            <button id="btn-level-select" class="menu-btn">
              <span class="btn-icon">❖</span>
              <span class="btn-text">LEVEL SELECT</span>
            </button>
            <button id="btn-settings" class="menu-btn">
              <span class="btn-icon">⚙</span>
              <span class="btn-text">SETTINGS</span>
            </button>
            <button id="btn-lore" class="menu-btn">
              <span class="btn-icon">📜</span>
              <span class="btn-text">CONTROLS & LORE</span>
            </button>
          </div>

          <div class="menu-footer">
            <div class="feature-pills">
              <span class="pill">3D Time Echoes</span>
              <span class="pill">Surreal Floating World</span>
              <span class="pill">Original Chibi Neo</span>
              <span class="pill">Interactive Audio</span>
            </div>
          </div>
        </div>
      </div>

      <!-- PAUSE MENU OVERLAY -->
      <div id="pause-menu" class="menu-overlay hidden">
        <div class="menu-glass-panel pause-panel">
          <h2 class="menu-header">TIME SUSPENDED</h2>
          <div class="menu-buttons">
            <button id="btn-resume" class="menu-btn primary-glow">RESUME</button>
            <button id="btn-restart-level" class="menu-btn">RESTART CHECKPOINT</button>
            <button id="btn-pause-select" class="menu-btn">LEVEL SELECT</button>
            <button id="btn-pause-settings" class="menu-btn">SETTINGS</button>
            <button id="btn-main-menu" class="menu-btn danger">MAIN MENU</button>
          </div>
        </div>
      </div>

      <!-- LEVEL SELECT MODAL -->
      <div id="level-select-modal" class="menu-overlay hidden">
        <div class="menu-glass-panel level-select-panel">
          <div class="modal-header">
            <h2>SELECT WORLD & LEVEL</h2>
            <button id="btn-close-level-select" class="btn-close">✕</button>
          </div>
          <div class="worlds-grid" id="worlds-grid"></div>
        </div>
      </div>

      <!-- SETTINGS MODAL -->
      <div id="settings-modal" class="menu-overlay hidden">
        <div class="menu-glass-panel settings-panel">
          <div class="modal-header">
            <h2>AUDIO & DISPLAY SETTINGS</h2>
            <button id="btn-close-settings" class="btn-close">✕</button>
          </div>

          <div class="settings-rows">
            <div class="setting-item">
              <label>Master Volume</label>
              <input type="range" id="vol-master" min="0" max="100" value="80" class="styled-slider">
              <span id="vol-master-val" class="setting-val">80%</span>
            </div>
            <div class="setting-item">
              <label>Music Volume</label>
              <input type="range" id="vol-music" min="0" max="100" value="60" class="styled-slider">
              <span id="vol-music-val" class="setting-val">60%</span>
            </div>
            <div class="setting-item">
              <label>SFX Volume</label>
              <input type="range" id="vol-sfx" min="0" max="100" value="85" class="styled-slider">
              <span id="vol-sfx-val" class="setting-val">85%</span>
            </div>
            <div class="setting-item">
              <label>Camera Sensitivity</label>
              <input type="range" id="cam-sens" min="20" max="200" value="100" class="styled-slider">
              <span id="cam-sens-val" class="setting-val">1.0x</span>
            </div>
            <div class="setting-item">
              <label>Visual Quality</label>
              <button id="btn-toggle-particles" class="toggle-btn active">Particles: High</button>
            </div>
          </div>
        </div>
      </div>

      <!-- LORE & CONTROLS MODAL -->
      <div id="lore-modal" class="menu-overlay hidden">
        <div class="menu-glass-panel lore-panel">
          <div class="modal-header">
            <h2>CONTROLS & TIME ECHO LORE</h2>
            <button id="btn-close-lore" class="btn-close">✕</button>
          </div>
          <div class="lore-body">
            <h3>✦ THE UNIQUE ECHO MECHANIC</h3>
            <p>You control <strong>NEO</strong>, an anime chibi traveler adrift across floating surreal dream islands. The world preserves your past actions.</p>
            <p>Walk to a switch or pressure plate. Press <span class="highlight">[R]</span> to commit the action into a glowing holographic <strong>Echo</strong> and rewind to start. The Echo will flawlessly re-enact your journey while you take a new path!</p>

            <h3>✦ KEYBOARD CONTROLS</h3>
            <ul class="controls-list">
              <li><strong>W, A, S, D</strong> — Move NEO in third-person view</li>
              <li><strong>SPACE</strong> — Jump (air control enabled)</li>
              <li><strong>SHIFT</strong> — Sprint</li>
              <li><strong>R</strong> — Commit Echo & Rewind Timeline</li>
              <li><strong>C</strong> — Clear Active Echoes</li>
              <li><strong>E</strong> — Interact with switches & memory crystals</li>
              <li><strong>Mouse Drag</strong> — Orbit camera & look around</li>
              <li><strong>Mouse Scroll</strong> — Zoom in/out</li>
              <li><strong>ESC</strong> — Pause Menu</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- LEVEL COMPLETE BANNER -->
      <div id="level-complete-banner" class="level-complete-banner hidden">
        <div class="complete-card">
          <div class="complete-rune">✧ ✧ ✧</div>
          <h2 class="complete-title">PUZZLE RESOLVED</h2>
          <p class="complete-subtitle">Portal to the next memory is open!</p>
        </div>
      </div>

      <!-- ENDING SCREEN -->
      <div id="ending-screen" class="menu-overlay ending-screen hidden">
        <div class="menu-glass-panel ending-panel">
          <div class="ending-thumb">
            <img src="/assets/echobound_ending.png" alt="Neo and The First Echo Finale" class="ending-img">
          </div>
          <div class="ending-header">
            <span class="ending-tag">FINALE OF ECHOBOUND</span>
            <h1 class="ending-title">THE WORLD THAT REMEMBERS YOU</h1>
          </div>
          <div class="ending-text">
            <p class="quote">"You were never alone. Every step you took through this shattered reality was guided by the first version of yourself that dreamed of reaching this place."</p>
            <p class="final-revelation">The First Echo smiles and steps into the celestial dawn. All echoes across the timeline dissolve into peaceful starlight.</p>
          </div>
          <div class="ending-stats">
            <div class="stat-card">
              <span class="stat-num" id="stat-puzzles">18</span>
              <span class="stat-label">Puzzles Resolved</span>
            </div>
            <div class="stat-card">
              <span class="stat-num" id="stat-echoes">24</span>
              <span class="stat-label">Echoes Summoned</span>
            </div>
            <div class="stat-card">
              <span class="stat-num">100%</span>
              <span class="stat-label">Memory Restored</span>
            </div>
          </div>
          <div class="ending-actions">
            <button id="btn-ending-menu" class="menu-btn primary-glow">RETURN TO TITLE</button>
            <button id="btn-ending-level-select" class="menu-btn">LEVEL SELECT / FREE PLAY</button>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
    this.updateMemoryProgress(20);
  }

  bindEvents() {
    // Buttons
    document.getElementById('btn-start').addEventListener('click', () => {
      this.hideMainMenu();
      soundManager.ensureContext();
      if (this.callbacks.onStartGame) this.callbacks.onStartGame();
    });

    document.getElementById('btn-level-select').addEventListener('click', () => {
      this.showLevelSelect();
    });

    document.getElementById('btn-pause-select').addEventListener('click', () => {
      this.hidePauseMenu();
      this.showLevelSelect();
    });

    document.getElementById('btn-close-level-select').addEventListener('click', () => {
      this.hideLevelSelect();
    });

    document.getElementById('btn-settings').addEventListener('click', () => {
      this.showSettings();
    });

    document.getElementById('btn-pause-settings').addEventListener('click', () => {
      this.showSettings();
    });

    document.getElementById('btn-close-settings').addEventListener('click', () => {
      this.hideSettings();
    });

    document.getElementById('btn-lore').addEventListener('click', () => {
      this.showLore();
    });

    document.getElementById('btn-close-lore').addEventListener('click', () => {
      this.hideLore();
    });

    document.getElementById('btn-resume').addEventListener('click', () => {
      this.hidePauseMenu();
    });

    document.getElementById('btn-restart-level').addEventListener('click', () => {
      this.hidePauseMenu();
      if (this.callbacks.onRestartLevel) this.callbacks.onRestartLevel();
    });

    document.getElementById('btn-main-menu').addEventListener('click', () => {
      this.hidePauseMenu();
      this.showMainMenu();
      if (this.callbacks.onReturnToMenu) this.callbacks.onReturnToMenu();
    });

    // Dialogue overlay click to close
    document.getElementById('dialogue-overlay').addEventListener('click', () => {
      this.hideDialogue();
    });

    // Ending buttons
    document.getElementById('btn-ending-menu').addEventListener('click', () => {
      document.getElementById('ending-screen').classList.add('hidden');
      this.showMainMenu();
      if (this.callbacks.onReturnToMenu) this.callbacks.onReturnToMenu();
    });

    document.getElementById('btn-ending-level-select').addEventListener('click', () => {
      document.getElementById('ending-screen').classList.add('hidden');
      this.showLevelSelect();
    });

    // Settings Sliders
    const volMaster = document.getElementById('vol-master');
    volMaster.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      document.getElementById('vol-master-val').textContent = `${val}%`;
      soundManager.setMasterVolume(val / 100);
    });

    const volMusic = document.getElementById('vol-music');
    volMusic.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      document.getElementById('vol-music-val').textContent = `${val}%`;
      soundManager.setMusicVolume(val / 100);
    });

    const volSfx = document.getElementById('vol-sfx');
    volSfx.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      document.getElementById('vol-sfx-val').textContent = `${val}%`;
      soundManager.setSfxVolume(val / 100);
    });

    const camSens = document.getElementById('cam-sens');
    camSens.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      document.getElementById('cam-sens-val').textContent = `${(val / 100).toFixed(1)}x`;
      if (this.callbacks.onCameraSensitivityChange) {
        this.callbacks.onCameraSensitivityChange(val / 100);
      }
    });

    // ESC Key for Pause Menu
    window.addEventListener('keydown', (e) => {
      if (e.code === 'Escape') {
        const pauseMenu = document.getElementById('pause-menu');
        const mainMenu = document.getElementById('main-menu');
        if (!mainMenu.classList.contains('hidden')) return;

        if (pauseMenu.classList.contains('hidden')) {
          this.showPauseMenu();
        } else {
          this.hidePauseMenu();
        }
      }
    });
  }

  showMainMenu() {
    document.getElementById('main-menu').classList.remove('hidden');
    document.getElementById('hud-top').classList.add('hidden');
    document.getElementById('hud-bottom').classList.add('hidden');
  }

  hideMainMenu() {
    document.getElementById('main-menu').classList.add('hidden');
    document.getElementById('hud-top').classList.remove('hidden');
    document.getElementById('hud-bottom').classList.remove('hidden');
  }

  showPauseMenu() {
    document.getElementById('pause-menu').classList.remove('hidden');
  }

  hidePauseMenu() {
    document.getElementById('pause-menu').classList.add('hidden');
  }

  showSettings() {
    document.getElementById('settings-modal').classList.remove('hidden');
  }

  hideSettings() {
    document.getElementById('settings-modal').classList.add('hidden');
  }

  showLore() {
    document.getElementById('lore-modal').classList.remove('hidden');
  }

  hideLore() {
    document.getElementById('lore-modal').classList.add('hidden');
  }

  showLevelSelect() {
    document.getElementById('level-select-modal').classList.remove('hidden');
  }

  hideLevelSelect() {
    document.getElementById('level-select-modal').classList.add('hidden');
  }

  populateLevelSelect(worlds, levels, currentLevelId) {
    const grid = document.getElementById('worlds-grid');
    grid.innerHTML = '';

    worlds.forEach(w => {
      const worldCard = document.createElement('div');
      worldCard.className = 'world-select-card';
      worldCard.innerHTML = `
        <div class="world-card-header">
          <span class="world-card-num">WORLD ${w.worldIndex}</span>
          <span class="world-card-name">${w.name.split('—')[1] || w.name}</span>
        </div>
        <div class="world-levels-list" id="levels-w${w.worldIndex}"></div>
      `;
      grid.appendChild(worldCard);

      const list = worldCard.querySelector(`#levels-w${w.worldIndex}`);
      const worldLevels = levels.filter(l => l.worldIndex === w.worldIndex);
      worldLevels.forEach(lvl => {
        const btn = document.createElement('button');
        btn.className = `level-pill-btn ${lvl.id === currentLevelId ? 'active' : ''}`;
        btn.textContent = `Lvl ${lvl.levelNumber}: ${lvl.title}`;
        btn.addEventListener('click', () => {
          this.hideLevelSelect();
          this.hidePauseMenu();
          this.hideMainMenu();
          if (this.callbacks.onSelectLevel) {
            this.callbacks.onSelectLevel(lvl.id);
          }
        });
        list.appendChild(btn);
      });
    });
  }

  updateHUD(levelData, echoInfo) {
    document.getElementById('hud-world-name').textContent = `WORLD ${levelData.worldIndex} — ${levelData.title.toUpperCase()}`;
    document.getElementById('hud-level-title').textContent = levelData.subtitle;

    // Echo count
    const echoElem = document.getElementById('hud-echo-count');
    if (levelData.maxEchoes === 0) {
      echoElem.textContent = "LOCKED";
    } else {
      echoElem.textContent = `${echoInfo.activeEchoCount} / ${levelData.maxEchoes}`;
    }

    // Slots
    const slots = document.getElementById('echo-slots-indicator');
    slots.innerHTML = '';
    for (let i = 0; i < (levelData.maxEchoes || 1); i++) {
      const dot = document.createElement('span');
      dot.className = `slot-dot ${i < echoInfo.activeEchoCount ? 'active filled' : ''}`;
      slots.appendChild(dot);
    }
  }

  updateTimelineStatus(recordSec, maxSec, isRecording, replaySec, hasEchoes) {
    const recBadge = document.getElementById('recording-badge');
    const replayBadge = document.getElementById('replay-badge');

    if (isRecording) {
      recBadge.classList.remove('hidden');
      const cur = Math.floor(recordSec);
      const mx = Math.floor(maxSec);
      document.getElementById('rec-status-text').textContent = `RECORDING ● 00:${cur < 10 ? '0' + cur : cur} / 00:${mx}`;
      const fillPct = Math.min(100, (recordSec / maxSec) * 100);
      document.getElementById('rec-fill').style.width = `${fillPct}%`;
    } else {
      recBadge.classList.add('hidden');
    }

    if (hasEchoes) {
      replayBadge.classList.remove('hidden');
      const rSec = Math.floor(replaySec);
      document.getElementById('replay-status-text').textContent = `ECHOES SYNCED ✦ 00:${rSec < 10 ? '0' + rSec : rSec}`;
    } else {
      replayBadge.classList.add('hidden');
    }
  }

  showInteractionPrompt(text, key = 'E') {
    const prompt = document.getElementById('floating-prompt');
    document.getElementById('prompt-label').textContent = text;
    document.getElementById('prompt-key').textContent = key;
    prompt.classList.remove('hidden');
  }

  hideInteractionPrompt() {
    document.getElementById('floating-prompt').classList.add('hidden');
  }

  showDialogue(text, speaker = 'MEMORY RESONANCE') {
    const overlay = document.getElementById('dialogue-overlay');
    document.getElementById('dialogue-speaker').textContent = speaker;
    document.getElementById('dialogue-text').textContent = text;
    overlay.classList.remove('hidden');
  }

  hideDialogue() {
    document.getElementById('dialogue-overlay').classList.add('hidden');
  }

  showLevelCompleteBanner() {
    const banner = document.getElementById('level-complete-banner');
    banner.classList.remove('hidden');
    setTimeout(() => {
      banner.classList.add('hidden');
    }, 2400);
  }

  showEndingScreen(stats = {}) {
    document.getElementById('hud-top').classList.add('hidden');
    document.getElementById('hud-bottom').classList.add('hidden');
    document.getElementById('stat-puzzles').textContent = stats.puzzlesSolved || '18';
    document.getElementById('stat-echoes').textContent = stats.echoesCreated || '24';
    document.getElementById('ending-screen').classList.remove('hidden');
  }

  updateMemoryProgress(percent) {
    this.memoryPercent = Math.min(100, Math.max(0, percent));
    document.getElementById('hud-memory-val').textContent = `${Math.round(this.memoryPercent)}%`;

    const circle = document.getElementById('memory-progress-circle');
    if (circle) {
      const radius = circle.r.baseVal.value;
      const circumference = radius * 2 * Math.PI;
      circle.style.strokeDasharray = `${circumference} ${circumference}`;
      const offset = circumference - (this.memoryPercent / 100) * circumference;
      circle.style.strokeDashoffset = offset;
    }
  }
}
