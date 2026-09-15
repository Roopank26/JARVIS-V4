// ECHOBOUND — Smooth Third-Person Camera with Cinematic Sequences & Collision Dampening
import * as THREE from 'three';

export class CameraController {
  constructor(camera, domElement) {
    this.camera = camera;
    this.domElement = domElement;

    // Follow target
    this.target = new THREE.Vector3(0, 1, 0);

    // Orbit parameters
    this.yaw = 0;
    this.pitch = 0.28; // radians (~16 degrees)
    this.minPitch = -0.15;
    this.maxPitch = 1.25;

    this.distance = 6.5;
    this.targetDistance = 6.5;
    this.minDistance = 3.0;
    this.maxDistance = 14.0;

    this.sensitivity = 0.0024;
    this.smoothSpeed = 7.5;

    // Camera shake / trauma
    this.trauma = 0;

    // Walking head bob
    this.bobTime = 0;

    // Cinematic state
    this.isCinematic = false;
    this.cinematicTarget = new THREE.Vector3();
    this.cinematicCamPos = new THREE.Vector3();
    this.cinematicDuration = 0;
    this.cinematicTimer = 0;
    this.cinematicOnComplete = null;

    // Mouse drag tracking
    this.isMouseDown = false;
    this.prevMouseX = 0;
    this.prevMouseY = 0;

    this.initControls();
  }

  initControls() {
    // Mouse drag orbiting
    window.addEventListener('mousedown', (e) => {
      if (e.target.tagName === 'BUTTON' || e.target.closest('.hud-interactive')) return;
      this.isMouseDown = true;
      this.prevMouseX = e.clientX;
      this.prevMouseY = e.clientY;
    });

    window.addEventListener('mouseup', () => {
      this.isMouseDown = false;
    });

    window.addEventListener('mousemove', (e) => {
      if (!this.isMouseDown || this.isCinematic) return;
      const dx = e.clientX - this.prevMouseX;
      const dy = e.clientY - this.prevMouseY;

      this.yaw -= dx * this.sensitivity;
      this.pitch += dy * this.sensitivity;
      this.pitch = Math.max(this.minPitch, Math.min(this.maxPitch, this.pitch));

      this.prevMouseX = e.clientX;
      this.prevMouseY = e.clientY;
    });

    // Mouse scroll zoom
    window.addEventListener('wheel', (e) => {
      if (this.isCinematic) return;
      this.targetDistance += e.deltaY * 0.005;
      this.targetDistance = Math.max(this.minDistance, Math.min(this.maxDistance, this.targetDistance));
    }, { passive: true });
  }

  setSensitivity(val) {
    this.sensitivity = 0.001 + val * 0.003;
  }

  addTrauma(amount = 0.4) {
    this.trauma = Math.min(1.0, this.trauma + amount);
  }

  playCinematic(camPos, lookAtPos, duration = 3.5, onComplete = null) {
    this.isCinematic = true;
    this.cinematicCamPos.copy(camPos);
    this.cinematicTarget.copy(lookAtPos);
    this.cinematicDuration = duration;
    this.cinematicTimer = 0;
    this.cinematicOnComplete = onComplete;
  }

  update(delta, playerPos, playerRotationY, isMoving = false, isRunning = false) {
    // 1. Cinematic mode
    if (this.isCinematic) {
      this.cinematicTimer += delta;
      const t = Math.min(1, this.cinematicTimer / this.cinematicDuration);
      const ease = THREE.MathUtils.smoothstep(t, 0, 1);

      this.camera.position.lerp(this.cinematicCamPos, delta * 3.5);
      this.target.lerp(this.cinematicTarget, delta * 4);
      this.camera.lookAt(this.target);

      if (t >= 1) {
        this.isCinematic = false;
        if (this.cinematicOnComplete) this.cinematicOnComplete();
      }
      return;
    }

    // 2. Normal Follow Mode
    this.distance = THREE.MathUtils.lerp(this.distance, this.targetDistance, delta * 8);

    // Follow player smoothly
    const lookTarget = new THREE.Vector3(playerPos.x, playerPos.y + 0.85, playerPos.z);
    this.target.lerp(lookTarget, delta * this.smoothSpeed);

    // Walking sway / bob
    let bobY = 0;
    let bobX = 0;
    if (isMoving) {
      this.bobTime += delta * (isRunning ? 12 : 7);
      bobY = Math.sin(this.bobTime) * 0.04;
      bobX = Math.cos(this.bobTime * 0.5) * 0.03;
    } else {
      this.bobTime = 0;
    }

    // Spherical position offset
    const cosPitch = Math.cos(this.pitch);
    const sinPitch = Math.sin(this.pitch);
    const sinYaw = Math.sin(this.yaw);
    const cosYaw = Math.cos(this.yaw);

    const desiredCamPos = new THREE.Vector3(
      this.target.x + this.distance * sinYaw * cosPitch + bobX,
      this.target.y + this.distance * sinPitch + bobY,
      this.target.z + this.distance * cosYaw * cosPitch
    );

    // Screen shake / trauma decay
    if (this.trauma > 0) {
      const shakeMag = this.trauma * this.trauma * 0.25;
      desiredCamPos.x += (Math.random() - 0.5) * shakeMag;
      desiredCamPos.y += (Math.random() - 0.5) * shakeMag;
      desiredCamPos.z += (Math.random() - 0.5) * shakeMag;
      this.trauma = Math.max(0, this.trauma - delta * 1.5);
    }

    this.camera.position.lerp(desiredCamPos, delta * this.smoothSpeed);
    this.camera.lookAt(this.target);
  }
}
