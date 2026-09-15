// ECHOBOUND — Echo Model & Replay Controller
import * as THREE from 'three';
import { NeoModel } from './NeoModel.js';
import { soundManager } from '../audio/SoundManager.js';

export class EchoModel {
  constructor(id, recording, particleManager, scene) {
    this.id = id;
    this.recording = recording; // Array of keyframe objects
    this.particleManager = particleManager;
    this.scene = scene;

    this.neo = new NeoModel(true);
    this.root = this.neo.root;

    // Faint glowing aura underneath
    const auraGeo = new THREE.RingGeometry(0.1, 0.45, 24);
    auraGeo.rotateX(-Math.PI / 2);
    const auraMat = new THREE.MeshBasicMaterial({
      color: 0x00f3ff,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.4
    });
    this.aura = new THREE.Mesh(auraGeo, auraMat);
    this.aura.position.y = 0.02;
    this.root.add(this.aura);

    this.scene.add(this.root);

    this.duration = recording.length > 0 ? recording[recording.length - 1].time : 0;
    this.currentTime = 0;
    this.isReplaying = true;
    this.isFormed = false;
    this.summonTimer = 0;
    this.summonDuration = 0.5;

    // Trails spawn timer
    this.trailTimer = 0;

    // Initial position
    if (recording.length > 0) {
      this.root.position.copy(recording[0].pos);
      this.root.rotation.y = recording[0].rotY;
    }

    // Set initial scale to 0 for spawn animation
    this.root.scale.set(0.01, 0.01, 0.01);
    this.particleManager.spawnEchoSummonBurst(this.root.position);
    soundManager.playEchoSummon();
  }

  // Sample recorded keyframes with linear interpolation
  sample(time) {
    const rec = this.recording;
    if (rec.length === 0) return null;
    if (time <= rec[0].time) return rec[0];
    if (time >= rec[rec.length - 1].time) return rec[rec.length - 1];

    // Binary or linear search
    let idx = 0;
    for (let i = 0; i < rec.length - 1; i++) {
      if (time >= rec[i].time && time <= rec[i + 1].time) {
        idx = i;
        break;
      }
    }

    const k1 = rec[idx];
    const k2 = rec[idx + 1];
    const range = k2.time - k1.time;
    const factor = range > 0.0001 ? (time - k1.time) / range : 0;

    // Interpolate position
    const pos = new THREE.Vector3().lerpVectors(k1.pos, k2.pos, factor);

    // Shortest angular difference for rotation
    let dRot = k2.rotY - k1.rotY;
    while (dRot < -Math.PI) dRot += Math.PI * 2;
    while (dRot > Math.PI) dRot -= Math.PI * 2;
    const rotY = k1.rotY + dRot * factor;

    return {
      pos,
      rotY,
      isMoving: factor > 0.5 ? k2.isMoving : k1.isMoving,
      isRunning: factor > 0.5 ? k2.isRunning : k1.isRunning,
      isJumping: factor > 0.5 ? k2.isJumping : k1.isJumping,
      isFalling: factor > 0.5 ? k2.isFalling : k1.isFalling,
      action: k1.action || k2.action
    };
  }

  update(time, delta) {
    this.currentTime = time;

    // 1. Summoning Animation
    if (!this.isFormed) {
      this.summonTimer += delta;
      const progress = Math.min(1, this.summonTimer / this.summonDuration);
      const ease = 1 - Math.pow(1 - progress, 3);
      this.root.scale.set(ease, ease, ease);

      if (progress >= 1) {
        this.isFormed = true;
        this.root.scale.set(1, 1, 1);
      }
    }

    // 2. Playback position & animation
    const sample = this.sample(time);
    if (sample) {
      this.root.position.copy(sample.pos);
      this.root.rotation.y = sample.rotY;

      // Update character animation rig
      this.neo.update(delta, {
        isMoving: sample.isMoving,
        isRunning: sample.isRunning,
        isJumping: sample.isJumping,
        isFalling: sample.isFalling,
        mood: 'curious'
      });

      // Spawn light trails while moving
      if (sample.isMoving) {
        this.trailTimer += delta;
        if (this.trailTimer > 0.06) {
          this.trailTimer = 0;
          this.particleManager.spawnTrail(this.root.position, 0x00f3ff, 0.28);
          // Also spawn slight violet accent trail
          if (Math.random() > 0.5) {
            this.particleManager.spawnTrail(
              new THREE.Vector3(
                this.root.position.x,
                this.root.position.y + 0.4,
                this.root.position.z
              ),
              0xbf55ec,
              0.22
            );
          }
        }
      }
    }

    // Aura ring rotation
    if (this.aura) {
      this.aura.rotation.z += delta * 2;
      this.aura.material.opacity = 0.3 + Math.sin(time * 5) * 0.15;
    }

    return sample;
  }

  getCurrentPosition() {
    return this.root.position;
  }

  destroy() {
    this.particleManager.spawnEchoSummonBurst(this.root.position);
    soundManager.playEchoDissolve();
    this.scene.remove(this.root);
  }
}
