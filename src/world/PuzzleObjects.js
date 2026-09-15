// ECHOBOUND — Interactive Puzzle Objects
import * as THREE from 'three';
import { soundManager } from '../audio/SoundManager.js';

// ==========================================
// 1. PRESSURE PLATE
// ==========================================
export class PressurePlate {
  constructor(id, position, options = {}, scene) {
    this.id = id;
    this.type = 'pressure_plate';
    this.position = position.clone();
    this.radius = options.radius || 1.1;
    this.targetIds = options.targets || [];
    this.scene = scene;

    this.isPressed = false;
    this.pressDepth = 0.08;
    this.currentY = 0;

    this.group = new THREE.Group();
    this.group.position.copy(position);

    // Outer Stone Ring
    const baseGeo = new THREE.CylinderGeometry(this.radius + 0.25, this.radius + 0.35, 0.16, 24);
    const baseMat = new THREE.MeshStandardMaterial({
      color: 0x222a38,
      roughness: 0.85,
      metalness: 0.15
    });
    const baseMesh = new THREE.Mesh(baseGeo, baseMat);
    baseMesh.position.y = 0.08;
    baseMesh.receiveShadow = true;
    this.group.add(baseMesh);

    // Inner Movable Plate
    const plateGeo = new THREE.CylinderGeometry(this.radius, this.radius, 0.14, 24);
    this.plateMat = new THREE.MeshStandardMaterial({
      color: 0x2c3b52,
      roughness: 0.5,
      metalness: 0.3,
      emissive: 0x003344,
      emissiveIntensity: 0.2
    });
    this.plateMesh = new THREE.Mesh(plateGeo, this.plateMat);
    this.plateMesh.position.y = 0.12;
    this.plateMesh.receiveShadow = true;
    this.group.add(this.plateMesh);

    // Glowing Rune Mandala on plate surface
    const runeGeo = new THREE.RingGeometry(0.2, this.radius - 0.2, 24);
    runeGeo.rotateX(-Math.PI / 2);
    this.runeMat = new THREE.MeshBasicMaterial({
      color: 0x00f3ff,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.6
    });
    this.runeMesh = new THREE.Mesh(runeGeo, this.runeMat);
    this.runeMesh.position.y = 0.075;
    this.plateMesh.add(this.runeMesh);

    this.scene.add(this.group);
  }

  update(delta, entities) {
    // Entities: array of { position: Vector3 }
    let occupied = false;
    for (const ent of entities) {
      const dX = ent.position.x - this.position.x;
      const dZ = ent.position.z - this.position.z;
      const distSq = dX * dX + dZ * dZ;
      const distY = Math.abs(ent.position.y - this.position.y);

      if (distSq < this.radius * this.radius && distY < 1.4) {
        occupied = true;
        break;
      }
    }

    if (occupied !== this.isPressed) {
      this.isPressed = occupied;
      soundManager.playPressurePlate(this.isPressed);
    }

    // Smooth plate depression animation
    const targetY = this.isPressed ? (0.12 - this.pressDepth) : 0.12;
    this.plateMesh.position.y = THREE.MathUtils.lerp(this.plateMesh.position.y, targetY, delta * 14);

    // Emissive glow change
    const targetGlow = this.isPressed ? 1.0 : 0.4;
    this.runeMat.opacity = THREE.MathUtils.lerp(this.runeMat.opacity, targetGlow, delta * 12);
    this.runeMat.color.setHex(this.isPressed ? 0x00ffff : 0x00aacc);

    return this.isPressed;
  }
}

// ==========================================
// 2. MAGIC SWITCH / CRYSTAL SWITCH
// ==========================================
export class MagicSwitch {
  constructor(id, position, options = {}, scene) {
    this.id = id;
    this.type = 'switch';
    this.position = position.clone();
    this.radius = options.radius || 1.8; // Interaction radius
    this.isTimed = options.isTimed || false;
    this.timedDuration = options.duration || 6.0;
    this.timedTimer = 0;
    this.isEchoOnly = options.isEchoOnly || false;
    this.scene = scene;

    this.isActive = false;

    this.group = new THREE.Group();
    this.group.position.copy(position);

    // Stone Pedestal
    const pedGeo = new THREE.CylinderGeometry(0.35, 0.5, 0.9, 12);
    const pedMat = new THREE.MeshStandardMaterial({
      color: 0x1e2738,
      roughness: 0.8
    });
    const pedMesh = new THREE.Mesh(pedGeo, pedMat);
    pedMesh.position.y = 0.45;
    this.group.add(pedMesh);

    // Floating Crystal Core
    const crystalGeo = new THREE.OctahedronGeometry(0.3, 0);
    this.crystalMat = new THREE.MeshStandardMaterial({
      color: this.isEchoOnly ? 0xbf55ec : 0x00f3ff,
      emissive: this.isEchoOnly ? 0xbf55ec : 0x00f3ff,
      emissiveIntensity: 0.7,
      roughness: 0.15,
      metalness: 0.3,
      transparent: true,
      opacity: 0.85
    });
    this.crystalMesh = new THREE.Mesh(crystalGeo, this.crystalMat);
    this.crystalMesh.position.y = 1.25;
    this.group.add(this.crystalMesh);

    // Orbiting rings
    const ringGeo = new THREE.TorusGeometry(0.42, 0.025, 8, 24);
    const ringMat = new THREE.MeshBasicMaterial({
      color: this.isEchoOnly ? 0xbf55ec : 0x00f3ff,
      transparent: true,
      opacity: 0.8
    });
    this.ringMesh = new THREE.Mesh(ringGeo, ringMat);
    this.ringMesh.position.y = 1.25;
    this.group.add(this.ringMesh);

    this.scene.add(this.group);
  }

  canInteract(playerPos) {
    if (this.isEchoOnly) return false;
    return this.position.distanceTo(playerPos) <= this.radius;
  }

  toggle() {
    this.isActive = !this.isActive;
    if (this.isTimed && this.isActive) {
      this.timedTimer = this.timedDuration;
    }
    soundManager.playSwitchClick(this.isActive);
    return this.isActive;
  }

  onEchoInteract() {
    this.isActive = !this.isActive;
    soundManager.playSwitchClick(this.isActive);
  }

  update(delta) {
    // Crystal spin & float bob
    const t = performance.now() * 0.002;
    this.crystalMesh.rotation.y += delta * 2;
    this.crystalMesh.rotation.x = Math.sin(t) * 0.2;
    this.crystalMesh.position.y = 1.25 + Math.sin(t * 1.5) * 0.06;

    this.ringMesh.rotation.x += delta * 1.5;
    this.ringMesh.rotation.z += delta * 2.2;

    if (this.isTimed && this.isActive) {
      this.timedTimer -= delta;
      if (this.timedTimer <= 0) {
        this.isActive = false;
        soundManager.playSwitchClick(false);
      }
    }

    // Visual state
    const intensity = this.isActive ? 2.0 : 0.6;
    this.crystalMat.emissiveIntensity = THREE.MathUtils.lerp(
      this.crystalMat.emissiveIntensity,
      intensity,
      delta * 8
    );

    return this.isActive;
  }
}

// ==========================================
// 3. MAGIC DOOR / ANCIENT GATE
// ==========================================
export class MagicDoor {
  constructor(id, position, options = {}, scene) {
    this.id = id;
    this.type = 'door';
    this.position = position.clone();
    this.rotationY = options.rotationY || 0;
    this.width = options.width || 3.0;
    this.height = options.height || 4.0;
    this.requiredTriggerIds = options.requiredTriggers || [];
    this.scene = scene;

    this.isOpen = false;
    this.openProgress = 0; // 0 = closed, 1 = open

    this.group = new THREE.Group();
    this.group.position.copy(position);
    this.group.rotation.y = this.rotationY;

    // Stone Gate Frame (Left & Right Pillars + Archway)
    const pillarMat = new THREE.MeshStandardMaterial({
      color: 0x1f2636,
      roughness: 0.8
    });

    const leftPillar = new THREE.Mesh(new THREE.BoxGeometry(0.7, this.height + 0.6, 0.8), pillarMat);
    leftPillar.position.set(-this.width * 0.5 - 0.35, (this.height + 0.6) * 0.5, 0);
    this.group.add(leftPillar);

    const rightPillar = leftPillar.clone();
    rightPillar.position.x = this.width * 0.5 + 0.35;
    this.group.add(rightPillar);

    const arch = new THREE.Mesh(new THREE.BoxGeometry(this.width + 1.4, 0.7, 0.9), pillarMat);
    arch.position.set(0, this.height + 0.65, 0);
    this.group.add(arch);

    // Sliding Runic Door Slabs (Left and Right halves)
    const slabMat = new THREE.MeshStandardMaterial({
      color: 0x27344c,
      roughness: 0.6,
      metalness: 0.2
    });

    this.leftSlab = new THREE.Mesh(new THREE.BoxGeometry(this.width * 0.5, this.height, 0.35), slabMat);
    this.leftSlab.position.set(-this.width * 0.25, this.height * 0.5, 0);
    this.group.add(this.leftSlab);

    this.rightSlab = new THREE.Mesh(new THREE.BoxGeometry(this.width * 0.5, this.height, 0.35), slabMat);
    this.rightSlab.position.set(this.width * 0.25, this.height * 0.5, 0);
    this.group.add(this.rightSlab);

    // Glowing Runic Bars on slabs
    const runeBarMat = new THREE.MeshBasicMaterial({
      color: 0x00f3ff,
      transparent: true,
      opacity: 0.85
    });

    const runeL = new THREE.Mesh(new THREE.BoxGeometry(0.12, this.height * 0.75, 0.38), runeBarMat);
    this.leftSlab.add(runeL);

    const runeR = new THREE.Mesh(new THREE.BoxGeometry(0.12, this.height * 0.75, 0.38), runeBarMat);
    this.rightSlab.add(runeR);

    this.scene.add(this.group);
  }

  update(delta, triggerStates = {}) {
    // Check if all required triggers are active
    let allActive = this.requiredTriggerIds.length > 0;
    for (const trigId of this.requiredTriggerIds) {
      if (!triggerStates[trigId]) {
        allActive = false;
        break;
      }
    }

    if (allActive !== this.isOpen) {
      this.isOpen = allActive;
      if (this.isOpen) {
        soundManager.playDoorOpen();
      }
    }

    // Animate door slide
    const targetProgress = this.isOpen ? 1 : 0;
    this.openProgress = THREE.MathUtils.lerp(this.openProgress, targetProgress, delta * 5);

    // Slide slabs outward
    const offset = this.openProgress * (this.width * 0.48);
    this.leftSlab.position.x = -this.width * 0.25 - offset;
    this.rightSlab.position.x = this.width * 0.25 + offset;
  }

  // Solid obstacle collision check when door is closed
  checkCollision(pos, radius = 0.4) {
    if (this.openProgress > 0.75) return null; // open enough to pass

    // Transform pos into door local coordinate space
    const localPos = this.group.worldToLocal(pos.clone());

    const halfW = this.width * 0.5;
    const halfD = 0.5;

    if (
      Math.abs(localPos.x) < halfW + radius &&
      Math.abs(localPos.z) < halfD + radius &&
      localPos.y > 0 && localPos.y < this.height
    ) {
      // Push back along z axis
      const sign = localPos.z > 0 ? 1 : -1;
      localPos.z = sign * (halfD + radius);
      return this.group.localToWorld(localPos);
    }
    return null;
  }
}

// ==========================================
// 4. MOVING PLATFORM
// ==========================================
export class MovingPlatform {
  constructor(id, startPos, endPos, options = {}, scene) {
    this.id = id;
    this.type = 'moving_platform';
    this.startPos = startPos.clone();
    this.endPos = endPos.clone();
    this.speed = options.speed || 1.8;
    this.width = options.width || 3.2;
    this.depth = options.depth || 3.2;
    this.requiresTrigger = options.requiresTrigger || false;
    this.triggerId = options.triggerId || null;
    this.scene = scene;

    this.progress = 0;
    this.direction = 1;
    this.currentPosition = startPos.clone();
    this.velocity = new THREE.Vector3();

    this.mesh = this.createMesh();
    this.mesh.position.copy(startPos);
    this.scene.add(this.mesh);
  }

  createMesh() {
    const group = new THREE.Group();

    // Stone Slab
    const slabGeo = new THREE.BoxGeometry(this.width, 0.4, this.depth);
    const slabMat = new THREE.MeshStandardMaterial({
      color: 0x222b3d,
      roughness: 0.7,
      metalness: 0.2
    });
    const slab = new THREE.Mesh(slabGeo, slabMat);
    slab.receiveShadow = true;
    group.add(slab);

    // Glowing propulsion runes beneath
    const runeGeo = new THREE.RingGeometry(0.3, this.width * 0.35, 16);
    runeGeo.rotateX(Math.PI / 2);
    const runeMat = new THREE.MeshBasicMaterial({
      color: 0x00f3ff,
      transparent: true,
      opacity: 0.85,
      side: THREE.DoubleSide
    });
    const rune = new THREE.Mesh(runeGeo, runeMat);
    rune.position.y = -0.21;
    group.add(rune);

    return group;
  }

  update(delta, triggerStates = {}) {
    if (this.requiresTrigger && this.triggerId && !triggerStates[this.triggerId]) {
      this.velocity.set(0, 0, 0);
      return this.currentPosition;
    }

    const prevPos = this.currentPosition.clone();
    this.progress += this.direction * (this.speed / this.startPos.distanceTo(this.endPos)) * delta;

    if (this.progress >= 1) {
      this.progress = 1;
      this.direction = -1;
    } else if (this.progress <= 0) {
      this.progress = 0;
      this.direction = 1;
    }

    // Ease in out
    const smoothT = THREE.MathUtils.smoothstep(this.progress, 0, 1);
    this.currentPosition.lerpVectors(this.startPos, this.endPos, smoothT);
    this.mesh.position.copy(this.currentPosition);

    this.velocity.subVectors(this.currentPosition, prevPos).divideScalar(delta || 1);
    return this.currentPosition;
  }

  // Check if entity is standing on top of moving platform
  isEntityOnTop(pos) {
    const halfW = this.width * 0.5 + 0.1;
    const halfD = this.depth * 0.5 + 0.1;

    const dX = Math.abs(pos.x - this.currentPosition.x);
    const dZ = Math.abs(pos.z - this.currentPosition.z);
    const dY = pos.y - (this.currentPosition.y + 0.2);

    return dX <= halfW && dZ <= halfD && dY >= -0.2 && dY <= 0.45;
  }
}

// ==========================================
// 5. DISAPPEARING / HARD-LIGHT BRIDGE
// ==========================================
export class DisappearingBridge {
  constructor(id, position, options = {}, scene) {
    this.id = id;
    this.type = 'bridge';
    this.position = position.clone();
    this.width = options.width || 2.4;
    this.length = options.length || 6.0;
    this.rotationY = options.rotationY || 0;
    this.triggerId = options.triggerId || null;
    this.invert = options.invert || false; // active when trigger is false
    this.scene = scene;

    this.isSolid = false;
    this.opacity = 0;

    this.group = new THREE.Group();
    this.group.position.copy(position);
    this.group.rotation.y = this.rotationY;

    // Glowing Hex Grid Bridge Mesh
    const geo = new THREE.BoxGeometry(this.width, 0.15, this.length);
    this.mat = new THREE.MeshStandardMaterial({
      color: 0x00f3ff,
      emissive: 0x00f3ff,
      emissiveIntensity: 0.9,
      roughness: 0.1,
      metalness: 0.5,
      transparent: true,
      opacity: 0.15
    });
    this.mesh = new THREE.Mesh(geo, this.mat);
    this.group.add(this.mesh);

    // Glowing edge strips
    const edgeGeo = new THREE.BoxGeometry(0.12, 0.2, this.length);
    const edgeMat = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.3
    });
    const edgeL = new THREE.Mesh(edgeGeo, edgeMat);
    edgeL.position.x = -this.width * 0.5;
    this.group.add(edgeL);

    const edgeR = new THREE.Mesh(edgeGeo, edgeMat);
    edgeR.position.x = this.width * 0.5;
    this.group.add(edgeR);

    this.scene.add(this.group);
  }

  update(delta, triggerStates = {}) {
    let active = this.triggerId ? !!triggerStates[this.triggerId] : true;
    if (this.invert) active = !active;

    if (active !== this.isSolid) {
      this.isSolid = active;
      if (this.isSolid) {
        soundManager.playBridgeActivate();
      } else {
        soundManager.playBridgeDeactivate();
      }
    }

    const targetOp = this.isSolid ? 0.75 : 0.08;
    this.opacity = THREE.MathUtils.lerp(this.opacity, targetOp, delta * 8);
    this.mat.opacity = this.opacity;

    return this.isSolid;
  }

  isEntityOnBridge(pos) {
    if (!this.isSolid || this.opacity < 0.4) return false;

    const localPos = this.group.worldToLocal(pos.clone());
    const halfW = this.width * 0.5;
    const halfL = this.length * 0.5;

    return (
      Math.abs(localPos.x) <= halfW &&
      Math.abs(localPos.z) <= halfL &&
      localPos.y >= -0.2 &&
      localPos.y <= 0.6
    );
  }
}

// ==========================================
// 6. MEMORY CRYSTAL (Story Fragment)
// ==========================================
export class MemoryCrystal {
  constructor(id, position, loreText, scene) {
    this.id = id;
    this.type = 'memory_crystal';
    this.position = position.clone();
    this.loreText = loreText;
    this.scene = scene;
    this.isDiscovered = false;

    this.group = new THREE.Group();
    this.group.position.copy(position);

    // Glowing Rhombus Crystal
    const crystalGeo = new THREE.OctahedronGeometry(0.5, 0);
    crystalGeo.scale(1, 1.6, 1);
    this.mat = new THREE.MeshStandardMaterial({
      color: 0x9d4edd,
      emissive: 0xbf55ec,
      emissiveIntensity: 1.0,
      roughness: 0.1,
      metalness: 0.4,
      transparent: true,
      opacity: 0.9
    });
    this.mesh = new THREE.Mesh(crystalGeo, this.mat);
    this.mesh.position.y = 1.0;
    this.group.add(this.mesh);

    // Orbiting magical light rings
    const ringGeo = new THREE.TorusGeometry(0.7, 0.02, 8, 32);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x00f3ff,
      transparent: true,
      opacity: 0.85
    });
    this.ring = new THREE.Mesh(ringGeo, ringMat);
    this.ring.position.y = 1.0;
    this.group.add(this.ring);

    this.scene.add(this.group);
  }

  canInteract(playerPos) {
    return this.position.distanceTo(playerPos) < 2.2;
  }

  collect() {
    this.isDiscovered = true;
    soundManager.playMemoryCrystal();
    return this.loreText;
  }

  update(delta) {
    const t = performance.now() * 0.0018;
    this.mesh.rotation.y += delta * 1.5;
    this.mesh.position.y = 1.0 + Math.sin(t * 2) * 0.12;

    this.ring.rotation.x += delta * 1.8;
    this.ring.rotation.y += delta * 1.2;

    const pulse = 0.8 + Math.sin(t * 3) * 0.3;
    this.mat.emissiveIntensity = pulse;
  }
}

// ==========================================
// 7. TELEPORT PORTAL / LEVEL EXIT PORTAL
// ==========================================
export class TeleportPortal {
  constructor(id, position, options = {}, scene) {
    this.id = id;
    this.type = 'portal';
    this.position = position.clone();
    this.isWorldExit = options.isWorldExit || false;
    this.isFinalPortal = options.isFinalPortal || false;
    this.destinationWorld = options.destinationWorld || null;
    this.destinationLevel = options.destinationLevel || null;
    this.scene = scene;

    this.group = new THREE.Group();
    this.group.position.copy(position);

    // Ancient Stone Portal Arch
    const archMat = new THREE.MeshStandardMaterial({
      color: 0x181e2b,
      roughness: 0.7
    });

    const portalTorusGeo = new THREE.TorusGeometry(1.6, 0.28, 12, 32);
    const portalArch = new THREE.Mesh(portalTorusGeo, archMat);
    portalArch.position.y = 1.6;
    this.group.add(portalArch);

    // Swirling Portal Disk / Vortex
    const diskGeo = new THREE.CircleGeometry(1.4, 32);
    this.portalMat = new THREE.MeshBasicMaterial({
      color: this.isWorldExit ? 0xffd166 : 0x00f3ff,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.85
    });
    this.portalDisk = new THREE.Mesh(diskGeo, this.portalMat);
    this.portalDisk.position.y = 1.6;
    this.group.add(this.portalDisk);

    // Outer swirling energy ring
    const energyRingGeo = new THREE.RingGeometry(1.4, 1.58, 32);
    const energyMat = new THREE.MeshBasicMaterial({
      color: 0xbf55ec,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.95
    });
    this.energyRing = new THREE.Mesh(energyRingGeo, energyMat);
    this.energyRing.position.y = 1.6;
    this.group.add(this.energyRing);

    this.scene.add(this.group);
  }

  isPlayerEntering(playerPos) {
    const dX = playerPos.x - this.position.x;
    const dZ = playerPos.z - this.position.z;
    const dist2D = Math.sqrt(dX * dX + dZ * dZ);
    const dY = Math.abs(playerPos.y - (this.position.y + 1.2));

    return dist2D < 1.3 && dY < 1.8;
  }

  update(delta) {
    this.energyRing.rotation.z += delta * 3.5;
    this.portalDisk.rotation.z -= delta * 1.5;

    const t = performance.now() * 0.003;
    this.portalMat.opacity = 0.75 + Math.sin(t * 3) * 0.2;
  }
}

// ==========================================
// 8. GRAVITY NODE (World 4 Broken Reality)
// ==========================================
export class GravityNode {
  constructor(id, position, options = {}, scene) {
    this.id = id;
    this.type = 'gravity_node';
    this.position = position.clone();
    this.radius = options.radius || 2.2;
    this.inverted = false;
    this.scene = scene;

    this.group = new THREE.Group();
    this.group.position.copy(position);

    // Inverted Pyramidal Anti-Gravity Node
    const nodeGeo = new THREE.ConeGeometry(0.6, 1.2, 4);
    nodeGeo.rotateX(Math.PI);
    this.mat = new THREE.MeshStandardMaterial({
      color: 0xbf55ec,
      emissive: 0x9d4edd,
      emissiveIntensity: 1.2,
      wireframe: false,
      roughness: 0.2
    });
    this.mesh = new THREE.Mesh(nodeGeo, this.mat);
    this.mesh.position.y = 1.2;
    this.group.add(this.mesh);

    // Gravity field boundary ring
    const ringGeo = new THREE.RingGeometry(this.radius - 0.1, this.radius, 32);
    ringGeo.rotateX(-Math.PI / 2);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0xbf55ec,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.6
    });
    this.fieldRing = new THREE.Mesh(ringGeo, ringMat);
    this.fieldRing.position.y = 0.05;
    this.group.add(this.fieldRing);

    this.scene.add(this.group);
  }

  canInteract(playerPos) {
    return this.position.distanceTo(playerPos) <= this.radius;
  }

  toggle() {
    this.inverted = !this.inverted;
    soundManager.playGravityFlip();
    return this.inverted;
  }

  update(delta) {
    this.mesh.rotation.y += delta * 2;
    const t = performance.now() * 0.002;
    this.mesh.position.y = 1.2 + Math.sin(t * 3) * 0.15;
    this.fieldRing.rotation.z += delta * 0.8;
  }
}
