// ECHOBOUND — Generative Web Audio Sound & Music Engine

export class SoundManager {
  constructor() {
    this.ctx = null;
    this.masterGain = null;
    this.musicGain = null;
    this.sfxGain = null;

    this.masterVolume = 0.8;
    this.musicVolume = 0.6;
    this.sfxVolume = 0.8;

    this.currentWorld = 1;
    this.musicPlaying = false;
    this.ambientTimer = null;
    this.convolver = null;
    this.initialized = false;
  }

  init() {
    if (this.initialized) return;
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioContext();

      // Master output
      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.setValueAtTime(this.masterVolume, this.ctx.currentTime);
      this.masterGain.connect(this.ctx.destination);

      // Music sub-bus
      this.musicGain = this.ctx.createGain();
      this.musicGain.gain.setValueAtTime(this.musicVolume, this.ctx.currentTime);
      this.musicGain.connect(this.masterGain);

      // SFX sub-bus
      this.sfxGain = this.ctx.createGain();
      this.sfxGain.gain.setValueAtTime(this.sfxVolume, this.ctx.currentTime);
      this.sfxGain.connect(this.masterGain);

      // Algorithmic Reverb Impulse
      this.createReverb();

      this.initialized = true;
      if (this.ctx.state === 'suspended') {
        const resumeOnEvent = () => {
          if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
          }
          window.removeEventListener('click', resumeOnEvent);
          window.removeEventListener('keydown', resumeOnEvent);
        };
        window.addEventListener('click', resumeOnEvent);
        window.addEventListener('keydown', resumeOnEvent);
      }

      this.startAmbientMusic();
    } catch (e) {
      console.warn("Web Audio API initialization failed:", e);
    }
  }

  ensureContext() {
    if (!this.initialized) {
      this.init();
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  createReverb() {
    const rate = this.ctx.sampleRate;
    const length = rate * 2.5;
    const decay = 2.0;
    const impulse = this.ctx.createBuffer(2, length, rate);
    const left = impulse.getChannelData(0);
    const right = impulse.getChannelData(1);

    for (let i = 0; i < length; i++) {
      const n = (1 - i / length) ** decay;
      left[i] = (Math.random() * 2 - 1) * n;
      right[i] = (Math.random() * 2 - 1) * n;
    }

    this.convolver = this.ctx.createConvolver();
    this.convolver.buffer = impulse;

    this.reverbGain = this.ctx.createGain();
    this.reverbGain.gain.setValueAtTime(0.4, this.ctx.currentTime);
    this.convolver.connect(this.reverbGain);
    this.reverbGain.connect(this.masterGain);
  }

  setMasterVolume(val) {
    this.masterVolume = Math.max(0, Math.min(1, val));
    if (this.masterGain) {
      this.masterGain.gain.setTargetAtTime(this.masterVolume, this.ctx.currentTime, 0.05);
    }
  }

  setMusicVolume(val) {
    this.musicVolume = Math.max(0, Math.min(1, val));
    if (this.musicGain) {
      this.musicGain.gain.setTargetAtTime(this.musicVolume, this.ctx.currentTime, 0.05);
    }
  }

  setSfxVolume(val) {
    this.sfxVolume = Math.max(0, Math.min(1, val));
    if (this.sfxGain) {
      this.sfxGain.gain.setTargetAtTime(this.sfxVolume, this.ctx.currentTime, 0.05);
    }
  }

  setWorldTheme(worldNumber) {
    this.currentWorld = worldNumber;
  }

  startAmbientMusic() {
    if (this.musicPlaying) return;
    this.musicPlaying = true;
    this.scheduleNextAmbientNote();
  }

  scheduleNextAmbientNote() {
    if (!this.musicPlaying) return;
    this.playAmbientChord();
    const nextInterval = 4000 + Math.random() * 3000;
    this.ambientTimer = setTimeout(() => {
      this.scheduleNextAmbientNote();
    }, nextInterval);
  }

  // Generates dreamy world-specific harmony
  playAmbientChord() {
    if (!this.ctx || this.ctx.state !== 'running') return;

    let baseFreqs = [];
    let timbre = 'sine';

    if (this.currentWorld === 1) {
      // Floating Islands: Bright, peaceful dream piano / harp (C, E, G, B, D)
      const roots = [261.63, 329.63, 392.00, 493.88, 587.33];
      const root = roots[Math.floor(Math.random() * roots.length)];
      baseFreqs = [root * 0.5, root, root * 1.5, root * 2];
      timbre = 'sine';
    } else if (this.currentWorld === 2) {
      // Crystal Forest: Shimmering minor 9th crystal bells (E, G, B, D#, F#)
      const roots = [329.63, 392.00, 493.88, 622.25, 739.99];
      const root = roots[Math.floor(Math.random() * roots.length)];
      baseFreqs = [root * 0.5, root, root * 1.5, root * 2.25];
      timbre = 'triangle';
    } else if (this.currentWorld === 3) {
      // Ancient Ruins: Somber ancient modal resonance (D, F, A, C)
      const roots = [293.66, 349.23, 440.00, 523.25];
      const root = roots[Math.floor(Math.random() * roots.length)];
      baseFreqs = [root * 0.5, root, root * 1.33, root * 2];
      timbre = 'triangle';
    } else if (this.currentWorld === 4) {
      // Broken Reality: Detuned glitched tones, mysterious intervals
      const roots = [277.18, 311.13, 415.30, 466.16];
      const root = roots[Math.floor(Math.random() * roots.length)];
      baseFreqs = [root * 0.5, root, root * 1.414, root * 2.05];
      timbre = 'sawtooth';
    } else if (this.currentWorld >= 5) {
      // Memory Void & Final Sanctuary: Deep cosmic space drone, lone piano note
      const roots = [220.00, 261.63, 329.63, 392.00];
      const root = roots[Math.floor(Math.random() * roots.length)];
      baseFreqs = [root * 0.25, root * 0.5, root * 1.5];
      timbre = 'sine';
    }

    baseFreqs.forEach((freq, idx) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      const filter = this.ctx.createBiquadFilter();

      osc.type = timbre;
      osc.frequency.setValueAtTime(freq, this.ctx.currentTime);

      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(timbre === 'sawtooth' ? 600 : 1200, this.ctx.currentTime);
      filter.Q.setValueAtTime(2, this.ctx.currentTime);

      const now = this.ctx.currentTime + idx * 0.08;
      const attack = 1.2 + idx * 0.3;
      const release = 3.5 + Math.random();

      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(0.04 / (idx + 1), now + attack);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + attack + release);

      osc.connect(filter);
      filter.connect(gain);
      gain.connect(this.musicGain);
      if (this.convolver) {
        gain.connect(this.convolver);
      }

      osc.start(now);
      osc.stop(now + attack + release + 0.1);
    });

    // Occasional twinkling high bell tone
    if (Math.random() > 0.4) {
      setTimeout(() => {
        this.playHighBell(baseFreqs[0] * 3);
      }, 800 + Math.random() * 1200);
    }
  }

  playHighBell(freq) {
    if (!this.ctx || this.ctx.state !== 'running') return;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq || 880, this.ctx.currentTime);

    const now = this.ctx.currentTime;
    gain.gain.setValueAtTime(0.03, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 1.8);

    osc.connect(gain);
    gain.connect(this.musicGain);
    if (this.convolver) gain.connect(this.convolver);

    osc.start(now);
    osc.stop(now + 1.9);
  }

  // SFX: Footstep
  playFootstep() {
    this.ensureContext();
    if (!this.ctx || this.ctx.state !== 'running') return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = 'sine';
    const pitch = 140 + Math.random() * 40;
    osc.frequency.setValueAtTime(pitch, now);
    osc.frequency.exponentialRampToValueAtTime(60, now + 0.08);

    gain.gain.setValueAtTime(0.06, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.08);

    osc.connect(gain);
    gain.connect(this.sfxGain);

    osc.start(now);
    osc.stop(now + 0.09);
  }

  // SFX: Jump
  playJump() {
    this.ensureContext();
    if (!this.ctx || this.ctx.state !== 'running') return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = 'triangle';
    osc.frequency.setValueAtTime(180, now);
    osc.frequency.exponentialRampToValueAtTime(420, now + 0.18);

    gain.gain.setValueAtTime(0.12, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.22);

    osc.connect(gain);
    gain.connect(this.sfxGain);

    osc.start(now);
    osc.stop(now + 0.23);
  }

  // SFX: Land
  playLand() {
    this.ensureContext();
    if (!this.ctx || this.ctx.state !== 'running') return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(120, now);
    osc.frequency.exponentialRampToValueAtTime(40, now + 0.12);

    gain.gain.setValueAtTime(0.14, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.15);

    osc.connect(gain);
    gain.connect(this.sfxGain);

    osc.start(now);
    osc.stop(now + 0.16);
  }

  // SFX: Echo Summon - "Unique reversed magical audio effect whenever an Echo appears"
  playEchoSummon() {
    this.ensureContext();
    if (!this.ctx || this.ctx.state !== 'running') return;
    const now = this.ctx.currentTime;

    // 1. Reversed frequency sweep (low to high crescendo)
    const sweep = this.ctx.createOscillator();
    const sweepGain = this.ctx.createGain();
    sweep.type = 'sine';
    sweep.frequency.setValueAtTime(120, now);
    sweep.frequency.exponentialRampToValueAtTime(960, now + 0.45);

    sweepGain.gain.setValueAtTime(0.001, now);
    sweepGain.gain.exponentialRampToValueAtTime(0.25, now + 0.42);
    sweepGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.55);

    sweep.connect(sweepGain);
    sweepGain.connect(this.sfxGain);
    if (this.convolver) sweepGain.connect(this.convolver);

    sweep.start(now);
    sweep.stop(now + 0.6);

    // 2. Harmonic bell burst at culmination
    setTimeout(() => {
      if (!this.ctx) return;
      const t = this.ctx.currentTime;
      [659.25, 880, 1174.66, 1760].forEach((f, i) => {
        const bell = this.ctx.createOscillator();
        const bellGain = this.ctx.createGain();
        bell.type = 'triangle';
        bell.frequency.setValueAtTime(f, t);

        bellGain.gain.setValueAtTime(0.15 / (i + 1), t);
        bellGain.gain.exponentialRampToValueAtTime(0.0001, t + 1.2);

        bell.connect(bellGain);
        bellGain.connect(this.sfxGain);
        if (this.convolver) bellGain.connect(this.convolver);

        bell.start(t);
        bell.stop(t + 1.3);
      });
    }, 420);
  }

  // SFX: Echo Dissolve
  playEchoDissolve() {
    this.ensureContext();
    if (!this.ctx || this.ctx.state !== 'running') return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, now);
    osc.frequency.exponentialRampToValueAtTime(220, now + 0.35);

    gain.gain.setValueAtTime(0.15, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.4);

    osc.connect(gain);
    gain.connect(this.sfxGain);
    if (this.convolver) gain.connect(this.convolver);

    osc.start(now);
    osc.stop(now + 0.42);
  }

  // SFX: Pressure Plate
  playPressurePlate(isPressed) {
    this.ensureContext();
    if (!this.ctx || this.ctx.state !== 'running') return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = isPressed ? 'triangle' : 'sine';
    const startF = isPressed ? 180 : 320;
    const endF = isPressed ? 90 : 220;

    osc.frequency.setValueAtTime(startF, now);
    osc.frequency.exponentialRampToValueAtTime(endF, now + 0.15);

    gain.gain.setValueAtTime(0.2, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.2);

    osc.connect(gain);
    gain.connect(this.sfxGain);

    osc.start(now);
    osc.stop(now + 0.22);
  }

  // SFX: Magic Switch
  playSwitchClick(active) {
    this.ensureContext();
    if (!this.ctx || this.ctx.state !== 'running') return;
    const now = this.ctx.currentTime;
    const freqs = active ? [523.25, 783.99, 1046.50] : [783.99, 523.25];

    freqs.forEach((f, i) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(f, now + i * 0.05);

      gain.gain.setValueAtTime(0.12, now + i * 0.05);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + i * 0.05 + 0.35);

      osc.connect(gain);
      gain.connect(this.sfxGain);
      if (this.convolver) gain.connect(this.convolver);

      osc.start(now + i * 0.05);
      osc.stop(now + i * 0.05 + 0.38);
    });
  }

  // SFX: Door Opening
  playDoorOpen() {
    this.ensureContext();
    if (!this.ctx || this.ctx.state !== 'running') return;
    const now = this.ctx.currentTime;

    // Rumble
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(55, now);
    osc.frequency.linearRampToValueAtTime(75, now + 0.8);

    gain.gain.setValueAtTime(0.18, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.9);

    osc.connect(gain);
    gain.connect(this.sfxGain);

    osc.start(now);
    osc.stop(now + 0.95);

    // Resonant chord
    setTimeout(() => {
      if (!this.ctx) return;
      const t = this.ctx.currentTime;
      [349.23, 440, 523.25].forEach((f) => {
        const o = this.ctx.createOscillator();
        const g = this.ctx.createGain();
        o.type = 'sine';
        o.frequency.setValueAtTime(f, t);
        g.gain.setValueAtTime(0.08, t);
        g.gain.exponentialRampToValueAtTime(0.0001, t + 0.8);
        o.connect(g);
        g.connect(this.sfxGain);
        if (this.convolver) g.connect(this.convolver);
        o.start(t);
        o.stop(t + 0.85);
      });
    }, 150);
  }

  // SFX: Memory Crystal Lore
  playMemoryCrystal() {
    this.ensureContext();
    if (!this.ctx || this.ctx.state !== 'running') return;
    const now = this.ctx.currentTime;
    const notes = [440, 554.37, 659.25, 830.61, 990];

    notes.forEach((freq, idx) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, now + idx * 0.08);

      gain.gain.setValueAtTime(0.12, now + idx * 0.08);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + idx * 0.08 + 1.5);

      osc.connect(gain);
      gain.connect(this.sfxGain);
      if (this.convolver) gain.connect(this.convolver);

      osc.start(now + idx * 0.08);
      osc.stop(now + idx * 0.08 + 1.6);
    });
  }

  // SFX: Gravity Inversion
  playGravityFlip() {
    this.ensureContext();
    if (!this.ctx || this.ctx.state !== 'running') return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(320, now);
    osc.frequency.exponentialRampToValueAtTime(60, now + 0.4);

    gain.gain.setValueAtTime(0.15, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.45);

    osc.connect(gain);
    gain.connect(this.sfxGain);
    if (this.convolver) gain.connect(this.convolver);

    osc.start(now);
    osc.stop(now + 0.5);
  }

  // SFX: Respawn / Fall Rewind
  playRespawn() {
    this.ensureContext();
    if (!this.ctx || this.ctx.state !== 'running') return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(110, now);
    osc.frequency.exponentialRampToValueAtTime(550, now + 0.5);

    gain.gain.setValueAtTime(0.12, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.55);

    osc.connect(gain);
    gain.connect(this.sfxGain);

    osc.start(now);
    osc.stop(now + 0.6);
  }

  // SFX: Level Solved / Portal Open
  playLevelComplete() {
    this.ensureContext();
    if (!this.ctx || this.ctx.state !== 'running') return;
    const now = this.ctx.currentTime;
    const melody = [523.25, 659.25, 783.99, 1046.50, 1318.51];

    melody.forEach((f, i) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(f, now + i * 0.12);

      gain.gain.setValueAtTime(0.15, now + i * 0.12);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + i * 0.12 + 1.2);

      osc.connect(gain);
      gain.connect(this.sfxGain);
      if (this.convolver) gain.connect(this.convolver);

      osc.start(now + i * 0.12);
      osc.stop(now + i * 0.12 + 1.3);
    });
  }
}

export const soundManager = new SoundManager();
