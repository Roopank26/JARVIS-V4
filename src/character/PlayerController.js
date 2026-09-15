// ECHOBOUND — Responsive Player Controller & Physics
import * as THREE from 'three';
import { NeoModel } from './NeoModel.js';
import { soundManager } from '../audio/SoundManager.js';

export class PlayerController {
  constructor(scene, particleManager, cameraController) {
    this.scene = scene;
    this.particleManager = particleManager;
    this.cameraController = cameraController;

    this.neo = new NeoModel(false);
    this.root = this.neo.root;
    this.scene.add(this.root);

    // Movement parameters
    this.position = new THREE.Vector3(0, 0, 0);
    this.velocity = new THREE.Vector3(0, 0, 0);
    this.rotationY = 0;

    this.walkSpeed = 4.6;
    this.runSpeed = 7.8;
    this.accel = 18.0;
    this.friction = 14.0;
    this.gravity = 20.0;
    this.jumpForce = 7.4;

    this.isGrounded = true;
    this.isJumping = false;
    this.isFalling = false;
    this.isRunning = false;
    this.isMoving = false;

    // Checkpoint
    this.checkpointPosition = new THREE.Vector3(0, 0, 0);
    this.checkpointRotationY = 0;

    // Gravity node inversion (World 4)
    this.gravityMultiplier = 1.0;

    // Footstep timer
    this.stepTimer = 0;

    // Key states
    this.keys = {
      forward: false,
      backward: false,
      left: false,
      right: false,
      jump: false,
      sprint: false,
      interact: false,
      echo: false,
      resetEcho: false
    };

    this.initInput();
  }

  initInput() {
    window.addEventListener('keydown', (e) => {
      const code = e.code;
      if (code === 'KeyW' || code === 'ArrowUp') this.keys.forward = true;
      if (code === 'KeyS' || code === 'ArrowDown') this.keys.backward = true;
      if (code === 'KeyA' || code === 'ArrowLeft') this.keys.left = true;
      if (code === 'KeyD' || code === 'ArrowRight') this.keys.right = true;
      if (code === 'Space') {
        if (!this.keys.jump && this.isGrounded) {
          this.doJump();
        }
        this.keys.jump = true;
      }
      if (code === 'ShiftLeft' || code === 'ShiftRight') this.keys.sprint = true;
      if (code === 'KeyE') this.keys.interact = true;
      if (code === 'KeyR') this.keys.echo = true;
      if (code === 'KeyC') this.keys.resetEcho = true;
    });

    window.addEventListener('keyup', (e) => {
      const code = e.code;
      if (code === 'KeyW' || code === 'ArrowUp') this.keys.forward = false;
      if (code === 'KeyS' || code === 'ArrowDown') this.keys.backward = false;
      if (code === 'KeyA' || code === 'ArrowLeft') this.keys.left = false;
      if (code === 'KeyD' || code === 'ArrowRight') this.keys.right = false;
      if (code === 'Space') this.keys.jump = false;
      if (code === 'ShiftLeft' || code === 'ShiftRight') this.keys.sprint = false;
      if (code === 'KeyE') this.keys.interact = false;
      if (code === 'KeyR') this.keys.echo = false;
      if (code === 'KeyC') this.keys.resetEcho = false;
    });
  }

  setCheckpoint(pos, rotY = 0) {
    this.checkpointPosition.copy(pos);
    this.checkpointRotationY = rotY;
  }

  teleport(pos, rotY = 0) {
    this.position.copy(pos);
    this.rotationY = rotY;
    this.velocity.set(0, 0, 0);
    this.root.position.copy(pos);
    this.root.rotation.y = rotY;
  }

  respawn() {
    this.particleManager.spawnEchoSummonBurst(this.position);
    soundManager.playRespawn();
    this.teleport(this.checkpointPosition, this.checkpointRotationY);
  }

  doJump() {
    this.velocity.y = this.jumpForce * this.gravityMultiplier;
    this.isGrounded = false;
    this.isJumping = true;
    this.particleManager.spawnFootstepPuff(this.position);
    soundManager.playJump();
  }

  setGravityInverted(inverted) {
    this.gravityMultiplier = inverted ? -1.0 : 1.0;
    this.root.rotation.z = inverted ? Math.PI : 0;
  }

  update(delta, collisionObjects = [], puzzleObjects = []) {
    // 1. Calculate input movement relative to camera
    const camYaw = this.cameraController.yaw;
    const forward = new THREE.Vector3(-Math.sin(camYaw), 0, -Math.cos(camYaw));
    const right = new THREE.Vector3(Math.cos(camYaw), 0, -Math.sin(camYaw));

    const moveDir = new THREE.Vector3();
    if (this.keys.forward) moveDir.add(forward);
    if (this.keys.backward) moveDir.sub(forward);
    if (this.keys.left) moveDir.sub(right);
    if (this.keys.right) moveDir.add(right);

    this.isMoving = moveDir.lengthSq() > 0.01;
    this.isRunning = this.isMoving && this.keys.sprint;

    const targetSpeed = this.isRunning ? this.runSpeed : this.walkSpeed;

    if (this.isMoving) {
      moveDir.normalize();
      // Target velocity
      const targetVelX = moveDir.x * targetSpeed;
      const targetVelZ = moveDir.z * targetSpeed;

      this.velocity.x = THREE.MathUtils.lerp(this.velocity.x, targetVelX, delta * this.accel);
      this.velocity.z = THREE.MathUtils.lerp(this.velocity.z, targetVelZ, delta * this.accel);

      // Rotate player smoothly to face travel direction
      const targetRotY = Math.atan2(moveDir.x, moveDir.z);
      let diff = targetRotY - this.rotationY;
      while (diff < -Math.PI) diff += Math.PI * 2;
      while (diff > Math.PI) diff -= Math.PI * 2;
      this.rotationY += diff * Math.min(1, delta * 14);
    } else {
      // Apply friction
      this.velocity.x = THREE.MathUtils.lerp(this.velocity.x, 0, delta * this.friction);
      this.velocity.z = THREE.MathUtils.lerp(this.velocity.z, 0, delta * this.friction);
    }

    // 2. Moving Platform passenger check
    let standingPlatform = null;
    for (const obj of puzzleObjects) {
      if (obj.type === 'moving_platform' && obj.isEntityOnTop(this.position)) {
        standingPlatform = obj;
        break;
      }
    }

    // 3. Gravity and Vertical Movement
    this.velocity.y -= this.gravity * this.gravityMultiplier * delta;

    // Apply horizontal motion
    this.position.x += this.velocity.x * delta;
    this.position.z += this.velocity.z * delta;

    if (standingPlatform) {
      this.position.x += standingPlatform.velocity.x * delta;
      this.position.z += standingPlatform.velocity.z * delta;
      this.position.y = standingPlatform.currentPosition.y + 0.2;
      this.velocity.y = 0;
      this.isGrounded = true;
      this.isJumping = false;
      this.isFalling = false;
    } else {
      this.position.y += this.velocity.y * delta;
    }

    // 4. Ground Collision Detection against Islands and Bridges
    let groundY = -999;
    const playerRadius = 0.35;

    // Check islands
    for (const isl of collisionObjects) {
      const b = isl.bounds;
      const dX = this.position.x - b.x;
      const dZ = this.position.z - b.z;
      const dist2D = Math.sqrt(dX * dX + dZ * dZ);

      if (dist2D <= b.radius + 0.2) {
        if (b.y > groundY && this.position.y >= b.y - 0.4) {
          groundY = b.y;
        }
      }
    }

    // Check disappearing hard-light bridges
    for (const obj of puzzleObjects) {
      if (obj.type === 'bridge' && obj.isEntityOnBridge(this.position)) {
        const bridgeTopY = obj.position.y + 0.08;
        if (bridgeTopY > groundY) {
          groundY = bridgeTopY;
        }
      }
    }

    // Resolve vertical ground collision
    if (!standingPlatform && this.position.y <= groundY + 0.05 && this.position.y >= groundY - 0.6) {
      this.position.y = groundY;
      if (this.velocity.y < -3.0) {
        soundManager.playLand();
        this.particleManager.spawnFootstepPuff(this.position);
      }
      this.velocity.y = 0;
      this.isGrounded = true;
      this.isJumping = false;
      this.isFalling = false;
    } else if (!standingPlatform) {
      this.isGrounded = false;
      this.isFalling = this.velocity.y < -1.0;
    }

    // 5. Door / Gate collision
    for (const obj of puzzleObjects) {
      if (obj.type === 'door') {
        const resolved = obj.checkCollision(this.position, playerRadius);
        if (resolved) {
          this.position.copy(resolved);
        }
      }
    }

    // 6. Void fall check (Respawn)
    if (this.position.y < -14) {
      this.respawn();
    }

    // 7. Footstep SFX and puffs
    if (this.isGrounded && this.isMoving) {
      const strideInterval = this.isRunning ? 0.28 : 0.42;
      this.stepTimer += delta;
      if (this.stepTimer >= strideInterval) {
        this.stepTimer = 0;
        soundManager.playFootstep();
        this.particleManager.spawnFootstepPuff(this.position);
      }
    } else {
      this.stepTimer = 0;
    }

    // 8. Update 3D Model
    this.root.position.copy(this.position);
    this.root.rotation.y = this.rotationY;

    this.neo.update(delta, {
      isMoving: this.isMoving,
      isRunning: this.isRunning,
      isJumping: this.isJumping,
      isFalling: this.isFalling,
      speed: this.velocity.length(),
      mood: this.isFalling ? 'alert' : (this.isMoving ? 'normal' : 'curious')
    });

    return {
      position: this.position,
      rotationY: this.rotationY,
      isMoving: this.isMoving,
      isRunning: this.isRunning,
      isJumping: this.isJumping,
      isFalling: this.isFalling,
      isGrounded: this.isGrounded
    };
  }
}
