// ECHOBOUND — World Builder (Floating Islands, Waterfalls, Ruins, Crystals, Clouds, Sky)
import * as THREE from 'three';

export class WorldBuilder {
  constructor(scene) {
    this.scene = scene;
    this.islandMeshes = [];
    this.waterfalls = [];
    this.crystals = [];
    this.floatingRocks = [];
    this.distantEchoes = [];

    // Shared materials
    this.grassMat = new THREE.MeshStandardMaterial({
      color: 0x38b000,
      roughness: 0.85,
      metalness: 0.05
    });

    this.rockMat = new THREE.MeshStandardMaterial({
      color: 0x222a38,
      roughness: 0.9,
      metalness: 0.1
    });

    this.ancientStoneMat = new THREE.MeshStandardMaterial({
      color: 0x2b384e,
      roughness: 0.75,
      metalness: 0.15
    });

    this.cyanCrystalMat = new THREE.MeshStandardMaterial({
      color: 0x00f3ff,
      emissive: 0x00c4d6,
      emissiveIntensity: 0.85,
      roughness: 0.15,
      metalness: 0.3,
      transparent: true,
      opacity: 0.9
    });

    this.violetCrystalMat = new THREE.MeshStandardMaterial({
      color: 0x9d4edd,
      emissive: 0xbf55ec,
      emissiveIntensity: 0.9,
      roughness: 0.15,
      metalness: 0.3,
      transparent: true,
      opacity: 0.9
    });

    this.waterMat = new THREE.MeshStandardMaterial({
      color: 0x00f3ff,
      emissive: 0x0088aa,
      emissiveIntensity: 0.6,
      roughness: 0.1,
      metalness: 0.1,
      transparent: true,
      opacity: 0.8
    });

    this.cloudMat = new THREE.MeshBasicMaterial({
      color: 0xccddff,
      transparent: true,
      opacity: 0.45,
      depthWrite: false
    });
  }

  // Set world theme palette
  applyWorldTheme(worldNum) {
    if (worldNum === 1) {
      // World 1: Bright magical floating islands
      this.grassMat.color.setHex(0x38b000);
      this.rockMat.color.setHex(0x283344);
      this.scene.fog = new THREE.FogExp2(0x18243b, 0.012);
    } else if (worldNum === 2) {
      // World 2: Crystal Forest
      this.grassMat.color.setHex(0x1b4332);
      this.rockMat.color.setHex(0x161e2e);
      this.scene.fog = new THREE.FogExp2(0x140d24, 0.015);
    } else if (worldNum === 3) {
      // World 3: Ancient Ruins
      this.grassMat.color.setHex(0x2d6a4f);
      this.rockMat.color.setHex(0x202b3c);
      this.scene.fog = new THREE.FogExp2(0x1a2133, 0.014);
    } else if (worldNum === 4) {
      // World 4: Broken Reality
      this.grassMat.color.setHex(0x3d0066);
      this.rockMat.color.setHex(0x190028);
      this.scene.fog = new THREE.FogExp2(0x1b002c, 0.018);
    } else if (worldNum >= 5) {
      // World 5 & Final Sanctuary: The Memory Void
      this.grassMat.color.setHex(0x0d1b2a);
      this.rockMat.color.setHex(0x080f18);
      this.scene.fog = new THREE.FogExp2(0x050814, 0.012);
    }
  }

  // Create a stylized floating island
  createFloatingIsland(x, y, z, width = 12, depth = 12, height = 5) {
    const group = new THREE.Group();
    group.position.set(x, y, z);

    // Island Top: Lush Grass Surface (beveled cylinder or rounded box)
    const topGeo = new THREE.CylinderGeometry(width * 0.5, width * 0.52, 0.6, 20);
    const topMesh = new THREE.Mesh(topGeo, this.grassMat);
    topMesh.position.y = 0;
    topMesh.receiveShadow = true;
    group.add(topMesh);

    // Island Bottom: Rocky inverted cone / stalactite underbelly
    const botGeo = new THREE.ConeGeometry(width * 0.52, height, 16);
    botGeo.rotateX(Math.PI);
    const botMesh = new THREE.Mesh(botGeo, this.rockMat);
    botMesh.position.y = -height * 0.5;
    group.add(botMesh);

    // Small hanging stalactites around rim
    const stalactiteGeo = new THREE.ConeGeometry(0.3, 1.6, 6);
    stalactiteGeo.rotateX(Math.PI);
    for (let i = 0; i < 5; i++) {
      const angle = (i / 5) * Math.PI * 2 + Math.random() * 0.4;
      const rad = width * 0.42;
      const stal = new THREE.Mesh(stalactiteGeo, this.rockMat);
      stal.position.set(Math.cos(angle) * rad, -0.6, Math.sin(angle) * rad);
      stal.scale.set(0.8 + Math.random() * 0.6, 0.8 + Math.random() * 0.6, 0.8 + Math.random() * 0.6);
      group.add(stal);
    }

    // Add glowing wild flowers on the surface
    for (let f = 0; f < 8; f++) {
      const flowerGeo = new THREE.SphereGeometry(0.12, 6, 6);
      const isViolet = Math.random() > 0.5;
      const flowerMat = new THREE.MeshBasicMaterial({
        color: isViolet ? 0xbf55ec : 0x00f3ff
      });
      const flower = new THREE.Mesh(flowerGeo, flowerMat);
      const r = (width * 0.4) * Math.sqrt(Math.random());
      const th = Math.random() * Math.PI * 2;
      flower.position.set(Math.cos(th) * r, 0.35, Math.sin(th) * r);
      group.add(flower);
    }

    this.scene.add(group);
    this.islandMeshes.push(group);

    return {
      group,
      bounds: {
        x: x,
        y: y,
        z: z,
        radius: width * 0.5
      }
    };
  }

  // Create a stylized cascading waterfall flowing off an island into the void
  createWaterfall(x, y, z, width = 2.0, height = 14) {
    const group = new THREE.Group();
    group.position.set(x, y, z);

    const sheetGeo = new THREE.PlaneGeometry(width, height, 4, 16);
    const sheet = new THREE.Mesh(sheetGeo, this.waterMat);
    sheet.position.set(0, -height * 0.5, 0);
    group.add(sheet);

    // Foam mist at bottom
    const foamGeo = new THREE.SphereGeometry(width * 0.8, 8, 8);
    const foam = new THREE.Mesh(foamGeo, this.cloudMat);
    foam.position.set(0, -height, 0);
    foam.scale.set(1.5, 0.6, 1.5);
    group.add(foam);

    this.scene.add(group);
    this.waterfalls.push({ sheet, height, time: Math.random() * 10 });
    return group;
  }

  // Create giant glowing crystals (landmarks)
  createGiantCrystal(x, y, z, scale = 1.0, isViolet = false) {
    const group = new THREE.Group();
    group.position.set(x, y, z);

    const crystalGeo = new THREE.ConeGeometry(0.8 * scale, 3.6 * scale, 6);
    const mat = isViolet ? this.violetCrystalMat : this.cyanCrystalMat;
    const crystal = new THREE.Mesh(crystalGeo, mat);
    crystal.position.y = 1.8 * scale;
    crystal.rotation.z = (Math.random() - 0.5) * 0.3;
    crystal.rotation.x = (Math.random() - 0.5) * 0.3;
    crystal.castShadow = true;
    group.add(crystal);

    // Secondary smaller crystal beside it
    const subGeo = new THREE.ConeGeometry(0.45 * scale, 2.2 * scale, 6);
    const sub = new THREE.Mesh(subGeo, mat);
    sub.position.set(0.6 * scale, 1.1 * scale, 0.4 * scale);
    sub.rotation.z = 0.3;
    group.add(sub);

    // Point Light for dramatic glow
    const light = new THREE.PointLight(isViolet ? 0xbf55ec : 0x00f3ff, 1.2, 12);
    light.position.set(0, 2.0 * scale, 0);
    group.add(light);

    this.scene.add(group);
    this.crystals.push({ group, mat, isViolet });
    return group;
  }

  // Create ancient stone ruins (pillars, arches)
  createAncientArch(x, y, z, rotationY = 0) {
    const group = new THREE.Group();
    group.position.set(x, y, z);
    group.rotation.y = rotationY;

    // Left & Right pillars
    const pilGeo = new THREE.BoxGeometry(0.8, 4.5, 0.8);
    const leftPil = new THREE.Mesh(pilGeo, this.ancientStoneMat);
    leftPil.position.set(-2.0, 2.25, 0);
    group.add(leftPil);

    const rightPil = new THREE.Mesh(pilGeo, this.ancientStoneMat);
    rightPil.position.set(2.0, 2.25, 0);
    group.add(rightPil);

    // Arch beam
    const beamGeo = new THREE.BoxGeometry(5.2, 0.7, 0.9);
    const beam = new THREE.Mesh(beamGeo, this.ancientStoneMat);
    beam.position.set(0, 4.6, 0);
    group.add(beam);

    // Glowing Ancient Rune Engraving on arch
    const runeGeo = new THREE.BoxGeometry(3.6, 0.1, 0.92);
    const runeMat = new THREE.MeshBasicMaterial({
      color: 0x00f3ff,
      transparent: true,
      opacity: 0.75
    });
    const runeMesh = new THREE.Mesh(runeGeo, runeMat);
    runeMesh.position.set(0, 4.6, 0);
    group.add(runeMesh);

    this.scene.add(group);
    return group;
  }

  // Create glowing dream tree
  createDreamTree(x, y, z, scale = 1.0) {
    const group = new THREE.Group();
    group.position.set(x, y, z);

    // Trunk
    const trunkGeo = new THREE.CylinderGeometry(0.2 * scale, 0.4 * scale, 2.5 * scale, 8);
    const trunk = new THREE.Mesh(trunkGeo, this.rockMat);
    trunk.position.y = 1.25 * scale;
    group.add(trunk);

    // Foliage (fluffy glowing clouds of leaves)
    const folMat = new THREE.MeshStandardMaterial({
      color: 0x00f3ff,
      emissive: 0x007799,
      emissiveIntensity: 0.5,
      roughness: 0.6
    });

    const f1 = new THREE.Mesh(new THREE.SphereGeometry(1.2 * scale, 10, 10), folMat);
    f1.position.y = 2.8 * scale;
    group.add(f1);

    const f2 = new THREE.Mesh(new THREE.SphereGeometry(0.8 * scale, 8, 8), folMat);
    f2.position.set(0.6 * scale, 3.4 * scale, 0.3 * scale);
    group.add(f2);

    this.scene.add(group);
    return group;
  }

  // Floating idle stones in the air
  createFloatingStones(center, count = 12, spread = 25) {
    for (let i = 0; i < count; i++) {
      const s = 0.4 + Math.random() * 0.8;
      const rockGeo = new THREE.DodecahedronGeometry(s, 0);
      const rock = new THREE.Mesh(rockGeo, this.rockMat);

      const px = center.x + (Math.random() - 0.5) * spread;
      const py = center.y + (Math.random() - 0.5) * 12 + 3;
      const pz = center.z + (Math.random() - 0.5) * spread;

      rock.position.set(px, py, pz);
      this.scene.add(rock);

      this.floatingRocks.push({
        mesh: rock,
        baseY: py,
        speed: 0.8 + Math.random() * 1.5,
        offset: Math.random() * Math.PI * 2,
        rotSpeed: 0.4 + Math.random() * 0.6
      });
    }
  }

  // Distant Sea of Clouds
  createCloudSea(y = -10) {
    const cloudGroup = new THREE.Group();
    cloudGroup.position.y = y;

    for (let i = 0; i < 40; i++) {
      const w = 25 + Math.random() * 40;
      const d = 25 + Math.random() * 40;
      const cGeo = new THREE.BoxGeometry(w, 4, d);
      const cMesh = new THREE.Mesh(cGeo, this.cloudMat);

      cMesh.position.set(
        (Math.random() - 0.5) * 220,
        Math.random() * 3,
        (Math.random() - 0.5) * 220
      );
      cloudGroup.add(cMesh);
    }

    this.scene.add(cloudGroup);
    this.cloudGroup = cloudGroup;
  }

  // Skybox Dome with Celestial Moon, Stars & Nebula
  createCosmicSkybox() {
    const skyGroup = new THREE.Group();

    // Panoramic Celestial Dome
    const domeGeo = new THREE.SphereGeometry(320, 32, 24);
    const textureLoader = new THREE.TextureLoader();
    textureLoader.load('/assets/celestial_sky.png', (tex) => {
      tex.wrapS = THREE.RepeatWrapping;
      tex.wrapT = THREE.ClampToEdgeWrapping;
      tex.colorSpace = THREE.SRGBColorSpace;
      const domeMat = new THREE.MeshBasicMaterial({
        map: tex,
        side: THREE.BackSide,
        depthWrite: false
      });
      const dome = new THREE.Mesh(domeGeo, domeMat);
      skyGroup.add(dome);
    }, undefined, () => {
      // Fallback cosmic gradient dome
      const domeMat = new THREE.MeshBasicMaterial({
        color: 0x070c1e,
        side: THREE.BackSide,
        depthWrite: false
      });
      const dome = new THREE.Mesh(domeGeo, domeMat);
      skyGroup.add(dome);
    });

    // Large Celestial Ringed Moon
    const moonGeo = new THREE.SphereGeometry(18, 24, 24);
    const moonMat = new THREE.MeshBasicMaterial({
      color: 0xccf5ff,
      transparent: true,
      opacity: 0.95
    });
    const moon = new THREE.Mesh(moonGeo, moonMat);
    moon.position.set(80, 70, -140);
    skyGroup.add(moon);

    // Celestial Planet Rings
    const ringGeo = new THREE.RingGeometry(24, 34, 48);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x00f3ff,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.4
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = Math.PI * 0.4;
    ring.rotation.y = Math.PI * 0.15;
    ring.position.copy(moon.position);
    skyGroup.add(ring);

    // Distant Floating Monoliths on horizon
    for (let i = 0; i < 8; i++) {
      const angle = (i / 8) * Math.PI * 2;
      const dist = 160;
      const mGeo = new THREE.BoxGeometry(8, 30, 8);
      const mMesh = new THREE.Mesh(mGeo, this.rockMat);
      mMesh.position.set(Math.cos(angle) * dist, 10 + Math.random() * 20, Math.sin(angle) * dist);
      skyGroup.add(mMesh);
    }

    this.scene.add(skyGroup);
    this.skyGroup = skyGroup;
  }

  // Final Area: Spawn hundreds of tiny translucent Echo silhouettes
  createFinalSanctuaryEchoes(center) {
    const echoMat = new THREE.MeshBasicMaterial({
      color: 0x00f3ff,
      transparent: true,
      opacity: 0.45
    });

    for (let i = 0; i < 150; i++) {
      const group = new THREE.Group();
      const angle = Math.random() * Math.PI * 2;
      const dist = 8 + Math.random() * 45;

      const x = center.x + Math.cos(angle) * dist;
      const y = center.y + (Math.random() - 0.5) * 4;
      const z = center.z + Math.sin(angle) * dist;

      // Stylized silhouette: head + body
      const head = new THREE.Mesh(new THREE.SphereGeometry(0.24, 8, 8), echoMat);
      head.position.y = 0.9;
      group.add(head);

      const body = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.14, 0.55, 8), echoMat);
      body.position.y = 0.5;
      group.add(body);

      group.position.set(x, y, z);
      group.rotation.y = Math.atan2(center.x - x, center.z - z);

      this.scene.add(group);
      this.distantEchoes.push({
        group,
        baseY: y,
        phase: Math.random() * Math.PI * 2
      });
    }
  }

  update(delta) {
    const t = performance.now() * 0.001;

    // Floating rocks idle hover
    for (const rock of this.floatingRocks) {
      rock.mesh.position.y = rock.baseY + Math.sin(t * rock.speed + rock.offset) * 0.4;
      rock.mesh.rotation.y += delta * rock.rotSpeed;
      rock.mesh.rotation.x += delta * (rock.rotSpeed * 0.5);
    }

    // Waterfalls slight shimmer
    for (const wf of this.waterfalls) {
      wf.sheet.position.x += Math.sin(t * 4 + wf.time) * 0.005;
    }

    // Distant Echoes breathing float
    for (const de of this.distantEchoes) {
      de.group.position.y = de.baseY + Math.sin(t * 1.5 + de.phase) * 0.08;
    }

    // Cloud sea slow drift
    if (this.cloudGroup) {
      this.cloudGroup.rotation.y += delta * 0.002;
    }
  }

  // Clear level geometry before loading next level
  clearWorld() {
    this.islandMeshes.forEach(m => this.scene.remove(m));
    this.islandMeshes = [];
    this.waterfalls.forEach(w => this.scene.remove(w.sheet.parent));
    this.waterfalls = [];
    this.crystals.forEach(c => this.scene.remove(c.group));
    this.crystals = [];
    this.floatingRocks.forEach(r => this.scene.remove(r.mesh));
    this.floatingRocks = [];
    this.distantEchoes.forEach(e => this.scene.remove(e.group));
    this.distantEchoes = [];
  }
}
