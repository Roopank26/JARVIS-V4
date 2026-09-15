// ECHOBOUND — NEO Character Model (Chibi Anime Stylized 3D Rig)
import * as THREE from 'three';

export class NeoModel {
  constructor(isEcho = false) {
    this.isEcho = isEcho;
    this.root = new THREE.Group();

    // Eye texture canvas for dynamic expressions
    this.eyeCanvas = document.createElement('canvas');
    this.eyeCanvas.width = 256;
    this.eyeCanvas.height = 128;
    this.eyeCtx = this.eyeCanvas.getContext('2d');
    this.eyeTexture = new THREE.CanvasTexture(this.eyeCanvas);
    this.eyeTexture.colorSpace = THREE.SRGBColorSpace;

    this.eyeMood = 'normal'; // 'normal', 'curious', 'happy', 'alert', 'glitch'
    this.blinkTimer = 0;
    this.isBlinking = false;
    this.blinkDuration = 0.14;

    this.animTime = 0;
    this.walkCycle = 0;
    this.squash = 1;

    // References to body parts for procedural animation
    this.parts = {};
    this.scarfSegments = [];

    this.buildCharacter();
    this.updateEyeCanvas();
  }

  buildCharacter() {
    const isE = this.isEcho;

    // Palette
    const palette = {
      skin: isE ? 0x66e5ff : 0xffdfd0,
      hair: isE ? 0x2299cc : 0x1a2138,
      hoodie: isE ? 0x114466 : 0x162035,
      hoodieAccent: isE ? 0x00f3ff : 0x243354,
      scarf: isE ? 0x00ffff : 0x00f3ff,
      backpack: isE ? 0x336688 : 0x63422d,
      backpackStrap: isE ? 0x224455 : 0x3d281a,
      shoesWhite: isE ? 0x88eeff : 0xf0f4f8,
      shoesCyan: isE ? 0x00f3ff : 0x00d8e6,
      gold: isE ? 0x88ffff : 0xffb703
    };

    // Base materials
    let skinMat, hairMat, hoodieMat, scarfMat, backpackMat, shoeMat, eyeMat;

    if (isE) {
      // Holographic Echo Material
      const echoColor = new THREE.Color(0x00e5ff);
      skinMat = new THREE.MeshStandardMaterial({
        color: echoColor,
        roughness: 0.1,
        metalness: 0.2,
        transparent: true,
        opacity: 0.65,
        emissive: 0x0088aa,
        emissiveIntensity: 0.6
      });
      hairMat = skinMat;
      hoodieMat = new THREE.MeshStandardMaterial({
        color: 0x114466,
        roughness: 0.2,
        transparent: true,
        opacity: 0.6,
        emissive: 0x004466,
        emissiveIntensity: 0.5
      });
      scarfMat = new THREE.MeshStandardMaterial({
        color: 0x00ffff,
        roughness: 0.1,
        transparent: true,
        opacity: 0.85,
        emissive: 0x00ffff,
        emissiveIntensity: 1.2
      });
      backpackMat = hoodieMat;
      shoeMat = scarfMat;
      eyeMat = new THREE.MeshBasicMaterial({
        map: this.eyeTexture,
        transparent: true,
        opacity: 0.95
      });
    } else {
      // NEO Real Traveler Material
      skinMat = new THREE.MeshStandardMaterial({
        color: palette.skin,
        roughness: 0.65,
        metalness: 0.05
      });
      hairMat = new THREE.MeshStandardMaterial({
        color: palette.hair,
        roughness: 0.5,
        metalness: 0.1
      });
      hoodieMat = new THREE.MeshStandardMaterial({
        color: palette.hoodie,
        roughness: 0.7,
        metalness: 0.1
      });
      scarfMat = new THREE.MeshStandardMaterial({
        color: palette.scarf,
        roughness: 0.2,
        metalness: 0.1,
        emissive: palette.scarf,
        emissiveIntensity: 0.85
      });
      backpackMat = new THREE.MeshStandardMaterial({
        color: palette.backpack,
        roughness: 0.75,
        metalness: 0.1
      });
      shoeMat = new THREE.MeshStandardMaterial({
        color: palette.shoesWhite,
        roughness: 0.4
      });
      eyeMat = new THREE.MeshBasicMaterial({
        map: this.eyeTexture,
        transparent: true
      });
    }

    // --- 1. TORSO & HOODIE ---
    const torsoGroup = new THREE.Group();
    torsoGroup.position.y = 0.62;
    this.root.add(torsoGroup);
    this.parts.torso = torsoGroup;

    // Torso mesh (cute stylized hoodie)
    const torsoGeo = new THREE.CylinderGeometry(0.24, 0.21, 0.44, 16);
    const torsoMesh = new THREE.Mesh(torsoGeo, hoodieMat);
    torsoMesh.castShadow = !isE;
    torsoGroup.add(torsoMesh);

    // Glowing Chest Rune Symbol
    const chestRuneGeo = new THREE.CircleGeometry(0.08, 16);
    const chestRuneMat = new THREE.MeshBasicMaterial({
      color: 0x00f3ff,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.95
    });
    const chestRune = new THREE.Mesh(chestRuneGeo, chestRuneMat);
    chestRune.position.set(0, 0.05, 0.22);
    torsoGroup.add(chestRune);
    this.parts.chestRune = chestRune;

    // Small glowing inner circle
    const chestCoreGeo = new THREE.CircleGeometry(0.035, 12);
    const chestCoreMat = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      side: THREE.DoubleSide
    });
    const chestCore = new THREE.Mesh(chestCoreGeo, chestCoreMat);
    chestCore.position.set(0, 0.05, 0.225);
    torsoGroup.add(chestCore);

    // Hood down cowl behind neck
    const hoodCowlGeo = new THREE.TorusGeometry(0.18, 0.08, 10, 16, Math.PI * 1.2);
    const hoodCowl = new THREE.Mesh(hoodCowlGeo, hoodieMat);
    hoodCowl.rotation.x = Math.PI * 0.45;
    hoodCowl.rotation.z = Math.PI * 0.9;
    hoodCowl.position.set(0, 0.16, -0.12);
    torsoGroup.add(hoodCowl);

    // --- 2. BACKPACK ---
    const backpackGroup = new THREE.Group();
    backpackGroup.position.set(0, 0.02, -0.22);
    torsoGroup.add(backpackGroup);

    const packGeo = new THREE.BoxGeometry(0.26, 0.28, 0.16);
    const packMesh = new THREE.Mesh(packGeo, backpackMat);
    packMesh.castShadow = !isE;
    backpackGroup.add(packMesh);

    // Bedroll on top of backpack
    const rollGeo = new THREE.CylinderGeometry(0.06, 0.06, 0.28, 12);
    const rollMat = new THREE.MeshStandardMaterial({
      color: isE ? 0x225577 : 0x2e4057,
      roughness: 0.8
    });
    const rollMesh = new THREE.Mesh(rollGeo, rollMat);
    rollMesh.rotation.z = Math.PI / 2;
    rollMesh.position.set(0, 0.17, 0);
    backpackGroup.add(rollMesh);

    // Metallic buckles
    const buckleMat = new THREE.MeshStandardMaterial({
      color: isE ? 0x66ffff : 0xd4af37,
      metalness: 0.8,
      roughness: 0.2
    });
    const buckle1 = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.04, 0.02), buckleMat);
    buckle1.position.set(-0.07, 0, -0.09);
    backpackGroup.add(buckle1);
    const buckle2 = buckle1.clone();
    buckle2.position.x = 0.07;
    backpackGroup.add(buckle2);

    // --- 3. HEAD & FACE ---
    const headGroup = new THREE.Group();
    headGroup.position.y = 0.32;
    torsoGroup.add(headGroup);
    this.parts.head = headGroup;

    // Chibi Head Base (slightly oversized cute proportions)
    const headGeo = new THREE.SphereGeometry(0.32, 24, 24);
    headGeo.scale(1, 0.95, 0.98);
    const headMesh = new THREE.Mesh(headGeo, skinMat);
    headMesh.castShadow = !isE;
    headGroup.add(headMesh);

    // Expressive Eyes Quad
    const eyeGeo = new THREE.PlaneGeometry(0.36, 0.18);
    const eyeMesh = new THREE.Mesh(eyeGeo, eyeMat);
    eyeMesh.position.set(0, 0.02, 0.315);
    headGroup.add(eyeMesh);
    this.parts.eyes = eyeMesh;

    // Stylized Anime Hair
    const hairGroup = new THREE.Group();
    headGroup.add(hairGroup);

    // Hair cap
    const hairCapGeo = new THREE.SphereGeometry(0.335, 18, 18, 0, Math.PI * 2, 0, Math.PI * 0.58);
    const hairCap = new THREE.Mesh(hairCapGeo, hairMat);
    hairCap.position.y = 0.02;
    hairCap.castShadow = !isE;
    hairGroup.add(hairCap);

    // Cute front bangs & side tufts
    const tuftGeo = new THREE.ConeGeometry(0.08, 0.24, 6);
    tuftGeo.rotateX(Math.PI * 0.6);

    const bangPositions = [
      { x: -0.14, y: 0.18, z: 0.24, rx: 0.3, rz: 0.4 },
      { x: -0.05, y: 0.22, z: 0.26, rx: 0.2, rz: 0.1 },
      { x: 0.06, y: 0.21, z: 0.26, rx: 0.25, rz: -0.15 },
      { x: 0.15, y: 0.17, z: 0.23, rx: 0.35, rz: -0.4 },
      // Side locks
      { x: -0.27, y: 0.04, z: 0.12, rx: 0.1, rz: 0.5 },
      { x: 0.27, y: 0.04, z: 0.12, rx: 0.1, rz: -0.5 },
      // Cute back spikes
      { x: 0, y: 0.18, z: -0.26, rx: -0.5, rz: 0 }
    ];

    bangPositions.forEach(p => {
      const tuft = new THREE.Mesh(tuftGeo, hairMat);
      tuft.position.set(p.x, p.y, p.z);
      tuft.rotation.set(p.rx, 0, p.rz);
      tuft.castShadow = !isE;
      hairGroup.add(tuft);
    });

    // --- 4. GLOWING CYAN SCARF ---
    const scarfNeckGeo = new THREE.TorusGeometry(0.24, 0.07, 12, 16);
    const scarfNeck = new THREE.Mesh(scarfNeckGeo, scarfMat);
    scarfNeck.rotation.x = Math.PI / 2;
    scarfNeck.position.set(0, 0.22, 0);
    torsoGroup.add(scarfNeck);

    // Trailing scarf ribbons (dynamic wave simulation)
    const scarfAnchor = new THREE.Group();
    scarfAnchor.position.set(0.12, 0.2, -0.18);
    torsoGroup.add(scarfAnchor);
    this.parts.scarfAnchor = scarfAnchor;

    const segmentCount = 5;
    let prevParent = scarfAnchor;
    for (let i = 0; i < segmentCount; i++) {
      const segWidth = 0.14 * (1 - i * 0.12);
      const segLength = 0.16;
      const segGeo = new THREE.BoxGeometry(segWidth, 0.04, segLength);
      const segMesh = new THREE.Mesh(segGeo, scarfMat);
      segMesh.position.set(0, -0.02, -segLength * 0.5);

      const pivot = new THREE.Group();
      if (i > 0) {
        pivot.position.set(0, 0, -segLength);
      }
      pivot.add(segMesh);
      prevParent.add(pivot);

      this.scarfSegments.push(pivot);
      prevParent = pivot;
    }

    // --- 5. ARMS & HANDS ---
    this.parts.leftArm = this.createArm(-1, hoodieMat, skinMat, isE);
    this.parts.rightArm = this.createArm(1, hoodieMat, skinMat, isE);
    torsoGroup.add(this.parts.leftArm);
    torsoGroup.add(this.parts.rightArm);

    // --- 6. LEGS & CYAN-WHITE SNEAKERS ---
    this.parts.leftLeg = this.createLeg(-1, hoodieMat, shoeMat, palette, isE);
    this.parts.rightLeg = this.createLeg(1, hoodieMat, shoeMat, palette, isE);
    this.root.add(this.parts.leftLeg);
    this.root.add(this.parts.rightLeg);

    // Position root so feet stand at ground y = 0
    this.root.position.y = 0;
  }

  createArm(side, sleeveMat, handMat, isEcho) {
    const shoulder = new THREE.Group();
    shoulder.position.set(side * 0.28, 0.14, 0);

    // Upper arm / sleeve
    const armGeo = new THREE.CylinderGeometry(0.065, 0.055, 0.22, 10);
    const armMesh = new THREE.Mesh(armGeo, sleeveMat);
    armMesh.position.y = -0.1;
    armMesh.castShadow = !isEcho;
    shoulder.add(armMesh);

    // Cute hand / mitten
    const handGeo = new THREE.SphereGeometry(0.06, 10, 10);
    const handMesh = new THREE.Mesh(handGeo, handMat);
    handMesh.position.y = -0.22;
    handMesh.castShadow = !isEcho;
    shoulder.add(handMesh);

    return shoulder;
  }

  createLeg(side, pantsMat, shoeMat, palette, isEcho) {
    const hip = new THREE.Group();
    hip.position.set(side * 0.12, 0.42, 0);

    // Leg mesh
    const legGeo = new THREE.CylinderGeometry(0.07, 0.06, 0.26, 12);
    const legMesh = new THREE.Mesh(legGeo, pantsMat);
    legMesh.position.y = -0.12;
    legMesh.castShadow = !isEcho;
    hip.add(legMesh);

    // Sneaker Group
    const footGroup = new THREE.Group();
    footGroup.position.set(0, -0.26, 0.04);
    hip.add(footGroup);

    // White Sneaker body
    const shoeGeo = new THREE.BoxGeometry(0.13, 0.11, 0.22);
    const shoeMesh = new THREE.Mesh(shoeGeo, shoeMat);
    shoeMesh.position.y = 0.05;
    shoeMesh.castShadow = !isEcho;
    footGroup.add(shoeMesh);

    // Cyan sole trim & accent
    const soleGeo = new THREE.BoxGeometry(0.14, 0.04, 0.24);
    const soleMat = new THREE.MeshStandardMaterial({
      color: palette.shoesCyan,
      emissive: palette.shoesCyan,
      emissiveIntensity: isEcho ? 0.9 : 0.6,
      roughness: 0.3
    });
    const soleMesh = new THREE.Mesh(soleGeo, soleMat);
    soleMesh.position.y = -0.01;
    footGroup.add(soleMesh);

    return hip;
  }

  setEyeMood(mood) {
    if (this.eyeMood !== mood) {
      this.eyeMood = mood;
      this.updateEyeCanvas();
    }
  }

  updateEyeCanvas() {
    const ctx = this.eyeCtx;
    const w = this.eyeCanvas.width;
    const h = this.eyeCanvas.height;

    ctx.clearRect(0, 0, w, h);

    if (this.isBlinking) {
      // Draw closed anime eyes (cute sleeping/blinking line ^_^)
      ctx.strokeStyle = this.isEcho ? '#00f3ff' : '#141a29';
      ctx.lineWidth = 6;
      ctx.lineCap = 'round';

      // Left eye closed
      ctx.beginPath();
      ctx.arc(w * 0.3, h * 0.55, 24, Math.PI * 0.15, Math.PI * 0.85);
      ctx.stroke();

      // Right eye closed
      ctx.beginPath();
      ctx.arc(w * 0.7, h * 0.55, 24, Math.PI * 0.15, Math.PI * 0.85);
      ctx.stroke();
    } else {
      // Draw open expressive anime eyes
      this.drawSingleEye(ctx, w * 0.3, h * 0.5, false);
      this.drawSingleEye(ctx, w * 0.7, h * 0.5, true);
    }

    // Cute blush marks on cheeks
    ctx.fillStyle = this.isEcho ? 'rgba(0, 243, 255, 0.25)' : 'rgba(255, 120, 150, 0.35)';
    ctx.beginPath();
    ctx.ellipse(w * 0.22, h * 0.82, 16, 8, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.beginPath();
    ctx.ellipse(w * 0.78, h * 0.82, 16, 8, 0, 0, Math.PI * 2);
    ctx.fill();

    this.eyeTexture.needsUpdate = true;
  }

  drawSingleEye(ctx, cx, cy, isRight) {
    const isE = this.isEcho;
    const mood = this.eyeMood;

    if (mood === 'happy') {
      // Curved happy eyes ^_^
      ctx.strokeStyle = isE ? '#00ffff' : '#141a29';
      ctx.lineWidth = 7;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.arc(cx, cy + 10, 26, Math.PI * 1.15, Math.PI * 1.85);
      ctx.stroke();
      return;
    }

    // Outer Sclera / eye background
    ctx.fillStyle = isE ? '#b3f7ff' : '#ffffff';
    ctx.beginPath();
    ctx.ellipse(cx, cy, 32, 42, 0, 0, Math.PI * 2);
    ctx.fill();

    // Iris (Cyan/Cosmic gradient with starry anime reflection)
    const irisGrad = ctx.createLinearGradient(cx, cy - 35, cx, cy + 35);
    if (isE) {
      irisGrad.addColorStop(0, '#00e5ff');
      irisGrad.addColorStop(1, '#9d4edd');
    } else {
      irisGrad.addColorStop(0, '#00b4d8');
      irisGrad.addColorStop(0.6, '#0077b6');
      irisGrad.addColorStop(1, '#023e8a');
    }

    const irisRadiusX = mood === 'curious' ? 26 : (mood === 'alert' ? 18 : 22);
    const irisRadiusY = mood === 'curious' ? 34 : (mood === 'alert' ? 24 : 30);

    ctx.fillStyle = irisGrad;
    ctx.beginPath();
    ctx.ellipse(cx, cy, irisRadiusX, irisRadiusY, 0, 0, Math.PI * 2);
    ctx.fill();

    // Pupil
    ctx.fillStyle = isE ? '#ffffff' : '#03071e';
    ctx.beginPath();
    ctx.arc(cx, cy, mood === 'curious' ? 14 : (mood === 'alert' ? 7 : 10), 0, Math.PI * 2);
    ctx.fill();

    // Anime Eye Highlights / Starlight glints
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(cx - 8, cy - 12, 8, 0, Math.PI * 2);
    ctx.fill();

    ctx.beginPath();
    ctx.arc(cx + 9, cy + 8, 4.5, 0, Math.PI * 2);
    ctx.fill();

    // Glitch effect on eyes when mood === 'glitch'
    if (mood === 'glitch') {
      ctx.fillStyle = 'rgba(255, 0, 255, 0.7)';
      ctx.fillRect(cx - 30, cy - 5, 60, 4);
      ctx.fillStyle = 'rgba(0, 255, 255, 0.7)';
      ctx.fillRect(cx - 25, cy + 8, 50, 3);
    }

    // Top Eyelash Outline
    ctx.strokeStyle = isE ? '#00f3ff' : '#141a29';
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.arc(cx, cy - 4, 32, Math.PI * 1.15, Math.PI * 1.85);
    ctx.stroke();
  }

  update(delta, state = {}) {
    this.animTime += delta;

    const {
      isMoving = false,
      isRunning = false,
      isJumping = false,
      isFalling = false,
      speed = 0,
      mood = null
    } = state;

    if (mood && mood !== this.eyeMood) {
      this.setEyeMood(mood);
    }

    // Eye blinking timer
    this.blinkTimer += delta;
    if (!this.isBlinking && this.blinkTimer > 3.2 + Math.random() * 2.5) {
      this.isBlinking = true;
      this.blinkTimer = 0;
      this.updateEyeCanvas();
    } else if (this.isBlinking && this.blinkTimer > this.blinkDuration) {
      this.isBlinking = false;
      this.blinkTimer = 0;
      this.updateEyeCanvas();
    }

    // Chest Rune pulsing
    if (this.parts.chestRune) {
      const pulse = 0.8 + Math.sin(this.animTime * 3) * 0.2;
      this.parts.chestRune.material.opacity = pulse;
    }

    // Locomotion Animation
    if (isJumping || isFalling) {
      // In air pose
      this.parts.leftLeg.rotation.x = THREE.MathUtils.lerp(this.parts.leftLeg.rotation.x, -0.4, delta * 12);
      this.parts.rightLeg.rotation.x = THREE.MathUtils.lerp(this.parts.rightLeg.rotation.x, 0.3, delta * 12);
      this.parts.leftArm.rotation.x = THREE.MathUtils.lerp(this.parts.leftArm.rotation.x, -0.6, delta * 12);
      this.parts.rightArm.rotation.x = THREE.MathUtils.lerp(this.parts.rightArm.rotation.x, -0.6, delta * 12);
      this.parts.torso.position.y = THREE.MathUtils.lerp(this.parts.torso.position.y, 0.68, delta * 10);

      // Scarf streams upward
      this.scarfSegments.forEach((seg, i) => {
        seg.rotation.x = THREE.MathUtils.lerp(seg.rotation.x, 0.35 + i * 0.1, delta * 10);
        seg.rotation.y = Math.sin(this.animTime * 6 + i) * 0.1;
      });
    } else if (isMoving) {
      // Walk / Run cycle
      const cycleFreq = isRunning ? 14 : 9;
      this.walkCycle += delta * cycleFreq;

      const legAngle = Math.sin(this.walkCycle) * (isRunning ? 0.85 : 0.55);
      const armAngle = -Math.sin(this.walkCycle) * (isRunning ? 0.9 : 0.6);

      this.parts.leftLeg.rotation.x = legAngle;
      this.parts.rightLeg.rotation.x = -legAngle;

      this.parts.leftArm.rotation.x = armAngle;
      this.parts.rightArm.rotation.x = -armAngle;

      // Torso bobbing & forward tilt
      const bob = Math.abs(Math.cos(this.walkCycle)) * 0.05;
      this.parts.torso.position.y = 0.62 + bob;
      this.parts.torso.rotation.x = isRunning ? 0.18 : 0.08;

      // Scarf streaming back dynamically
      const trailStrength = isRunning ? -0.55 : -0.3;
      this.scarfSegments.forEach((seg, i) => {
        const wave = Math.sin(this.walkCycle * 0.8 - i * 0.8) * 0.18;
        seg.rotation.x = THREE.MathUtils.lerp(seg.rotation.x, trailStrength + wave, delta * 12);
        seg.rotation.y = Math.cos(this.walkCycle * 0.5 - i * 0.5) * 0.12;
      });
    } else {
      // Idle Breathing
      const breath = Math.sin(this.animTime * 2.2);
      this.parts.torso.position.y = 0.62 + breath * 0.015;
      this.parts.torso.rotation.x = THREE.MathUtils.lerp(this.parts.torso.rotation.x, 0, delta * 8);

      this.parts.leftLeg.rotation.x = THREE.MathUtils.lerp(this.parts.leftLeg.rotation.x, 0, delta * 8);
      this.parts.rightLeg.rotation.x = THREE.MathUtils.lerp(this.parts.rightLeg.rotation.x, 0, delta * 8);

      this.parts.leftArm.rotation.x = THREE.MathUtils.lerp(this.parts.leftArm.rotation.x, 0, delta * 8);
      this.parts.rightArm.rotation.x = THREE.MathUtils.lerp(this.parts.rightArm.rotation.x, 0, delta * 8);

      // Scarf gentle breeze fluttering
      this.scarfSegments.forEach((seg, i) => {
        const flutter = Math.sin(this.animTime * 3.5 + i * 0.9) * 0.12;
        seg.rotation.x = THREE.MathUtils.lerp(seg.rotation.x, -0.15 + flutter, delta * 6);
        seg.rotation.y = Math.cos(this.animTime * 2 + i * 0.6) * 0.08;
      });
    }
  }
}
