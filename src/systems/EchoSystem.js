// ECHOBOUND — Echo System & Timeline Coordinator
import * as THREE from 'three';
import { EchoModel } from '../character/EchoModel.js';
import { soundManager } from '../audio/SoundManager.js';

export class EchoSystem {
  constructor(scene, particleManager) {
    this.scene = scene;
    this.particleManager = particleManager;

    this.maxEchoes = 1;
    this.activeEchoes = [];

    this.isRecording = true;
    this.recordDuration = 0;
    this.maxRecordDuration = 25.0; // seconds

    this.currentRecording = [];
    this.recordSampleTimer = 0;
    this.sampleRate = 1 / 30; // 30Hz recording keyframes

    this.replayTime = 0;
    this.initialPosition = new THREE.Vector3(0, 0, 0);
    this.initialRotationY = 0;

    this.onEchoCreatedCallback = null;
    this.onEchoesResetCallback = null;
  }

  setMaxEchoes(count) {
    this.maxEchoes = count;
  }

  setAnchor(position, rotY = 0) {
    this.initialPosition.copy(position);
    this.initialRotationY = rotY;
    this.resetRecording();
  }

  resetRecording() {
    this.currentRecording = [];
    this.recordDuration = 0;
    this.recordSampleTimer = 0;
    this.isRecording = true;
  }

  recordFrame(delta, neoState, actionEvent = null) {
    if (!this.isRecording) return;

    this.recordDuration += delta;
    this.recordSampleTimer += delta;

    if (this.recordSampleTimer >= this.sampleRate || actionEvent) {
      this.recordSampleTimer = 0;
      this.currentRecording.push({
        time: this.recordDuration,
        pos: neoState.position.clone(),
        rotY: neoState.rotationY,
        isMoving: neoState.isMoving,
        isRunning: neoState.isRunning,
        isJumping: neoState.isJumping,
        isFalling: neoState.isFalling,
        action: actionEvent
      });
    }

    // Auto-loop / cap if record duration exceeds max
    if (this.recordDuration >= this.maxRecordDuration) {
      // Don't auto-stop, just hold the last keyframe
    }
  }

  // Create an Echo from current recording and rewind player
  commitEchoAndRewind(neoController) {
    if (this.currentRecording.length < 10) {
      console.log("Recording too short to commit echo.");
      return false;
    }

    // If max echoes reached, remove the oldest echo
    if (this.activeEchoes.length >= this.maxEchoes) {
      const oldest = this.activeEchoes.shift();
      oldest.destroy();
    }

    const echoId = this.activeEchoes.length + 1;
    const newEcho = new EchoModel(
      echoId,
      [...this.currentRecording],
      this.particleManager,
      this.scene
    );
    this.activeEchoes.push(newEcho);

    // Rewind player to anchor position
    neoController.teleport(this.initialPosition, this.initialRotationY);

    // Rewind timeline so all echoes and player replay in sync
    this.replayTime = 0;
    this.resetRecording();

    if (this.onEchoCreatedCallback) {
      this.onEchoCreatedCallback(this.activeEchoes.length, this.maxEchoes);
    }

    return true;
  }

  // Clear all active echoes
  clearEchoes() {
    this.activeEchoes.forEach(e => e.destroy());
    this.activeEchoes = [];
    this.replayTime = 0;
    this.resetRecording();

    if (this.onEchoesResetCallback) {
      this.onEchoesResetCallback(0, this.maxEchoes);
    }
  }

  update(delta, puzzleObjects = []) {
    this.replayTime += delta;

    // Update active echoes
    const activeEchoPositions = [];
    for (const echo of this.activeEchoes) {
      const sample = echo.update(this.replayTime, delta);
      if (sample) {
        activeEchoPositions.push(echo.getCurrentPosition());

        // Process recorded actions (like switch flips)
        if (sample.action && sample.action.type === 'switch_toggle') {
          const targetObj = puzzleObjects.find(p => p.id === sample.action.targetId);
          if (targetObj && typeof targetObj.onEchoInteract === 'function') {
            targetObj.onEchoInteract();
          }
        }
      }
    }

    return {
      activeEchoPositions,
      replayTime: this.replayTime,
      recordDuration: this.recordDuration,
      activeEchoCount: this.activeEchoes.length,
      maxEchoes: this.maxEchoes
    };
  }
}
