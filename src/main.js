// ECHOBOUND — Main Game Engine & Loop
import * as THREE from 'three';
import { soundManager } from './audio/SoundManager.js';
import { ParticleManager } from './particles/ParticleSystem.js';
import { CameraController } from './camera/CameraController.js';
import { PlayerController } from './character/PlayerController.js';
import { EchoSystem } from './systems/EchoSystem.js';
import { WorldBuilder } from './world/WorldBuilder.js';
import { UIManager } from './ui/UIManager.js';
import {
  PressurePlate,
  MagicSwitch,
  MagicDoor,
  MovingPlatform,
  DisappearingBridge,
  MemoryCrystal,
  TeleportPortal,
  GravityNode
} from './world/PuzzleObjects.js';
import { LEVELS, WORLDS_DATA } from './levels/LevelDefinitions.js';

class EchoboundGame {
  constructor() {
    this.container = document.getElementById('canvas-container');

    // 1. Three.js Scene, Camera, Renderer
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x060c1c);

    this.camera = new THREE.PerspectiveCamera(
      55,
      window.innerWidth / window.innerHeight,
      0.1,
      600
    );

    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: 'high-performance'
    });
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.15;
    this.container.appendChild(this.renderer.domElement);

    // 2. Systems
    this.particleManager = new ParticleManager(this.scene);
    this.cameraController = new CameraController(this.camera, this.renderer.domElement);
    this.player = new PlayerController(this.scene, this.particleManager, this.cameraController);
    this.echoSystem = new EchoSystem(this.scene, this.particleManager);
    this.worldBuilder = new WorldBuilder(this.scene);

    // 3. Game State
    this.currentLevelIndex = 0;
    this.currentLevel = null;
    this.puzzleObjects = [];
    this.islandMeshes = [];
    this.triggerStates = {};
    this.isGameActive = false;
    this.firstEchoNPC = null;
    this.hasEncounteredFirstEcho = false;

    // Statistics tracking
    this.stats = {
      puzzlesSolved: 0,
      echoesCreated: 0,
      memoriesDiscovered: 0
    };

    // 4. UI Manager
    this.ui = new UIManager({
      onStartGame: () => this.startGame(),
      onRestartLevel: () => this.restartLevel(),
      onReturnToMenu: () => this.returnToMenu(),
      onSelectLevel: (lvlId) => this.loadLevelById(lvlId),
      onCameraSensitivityChange: (s) => this.cameraController.setSensitivity(s)
    });

    this.initLights();
    this.initSkyAndAtmosphere();
    this.bindGlobalKeys();
    this.setupResize();

    // Load initial world into menu background
    this.loadLevel(0);
    this.ui.populateLevelSelect(WORLDS_DATA, LEVELS, LEVELS[0].id);

    // Start render loop
    this.clock = new THREE.Clock();
    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);
  }

  initLights() {
    // Ambient Light (deep twilight indigo)
    this.ambientLight = new THREE.AmbientLight(0x2d3b59, 1.2);
    this.scene.add(this.ambientLight);

    // Directional Sunlight (warm pale gold-cyan)
    this.sunLight = new THREE.DirectionalLight(0xa6d8ff, 2.2);
    this.sunLight.position.set(24, 45, 18);
    this.sunLight.castShadow = true;
    this.sunLight.shadow.mapSize.width = 2048;
    this.sunLight.shadow.mapSize.height = 2048;
    this.sunLight.shadow.camera.near = 1;
    this.sunLight.shadow.camera.far = 120;
    this.sunLight.shadow.camera.left = -30;
    this.sunLight.shadow.camera.right = 30;
    this.sunLight.shadow.camera.top = 30;
    this.sunLight.shadow.camera.bottom = -30;
    this.sunLight.shadow.bias = -0.0005;
    this.scene.add(this.sunLight);

    // Hemispheric Light (Cyan sky, deep purple ground)
    this.hemiLight = new THREE.HemisphereLight(0x00f3ff, 0x1b0a2a, 0.75);
    this.scene.add(this.hemiLight);
  }

  initSkyAndAtmosphere() {
    this.worldBuilder.createCosmicSkybox();
    this.worldBuilder.createCloudSea(-14);
  }

  setupResize() {
    window.addEventListener('resize', () => {
      this.camera.aspect = window.innerWidth / window.innerHeight;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(window.innerWidth, window.innerHeight);
    });
  }

  bindGlobalKeys() {
    window.addEventListener('keydown', (e) => {
      if (!this.isGameActive) return;

      // [R] Key: Commit Echo & Rewind
      if (e.code === 'KeyR') {
        if (this.currentLevel && this.currentLevel.maxEchoes > 0) {
          const success = this.echoSystem.commitEchoAndRewind(this.player);
          if (success) {
            this.stats.echoesCreated++;
            this.cameraController.addTrauma(0.25);
          }
        }
      }

      // [C] Key: Clear all active Echoes
      if (e.code === 'KeyC') {
        this.echoSystem.clearEchoes();
      }

      // [E] Key: Interact with nearby Switch, Memory Crystal, or Gravity Node
      if (e.code === 'KeyE') {
        this.handlePlayerInteraction();
      }

      // [Backspace] Key: Quick restart level
      if (e.code === 'Backspace') {
        this.restartLevel();
      }
    });
  }

  handlePlayerInteraction() {
    const pPos = this.player.position;

    // 1. Check Magic Switches
    for (const obj of this.puzzleObjects) {
      if (obj.type === 'switch' && obj.canInteract(pPos)) {
        const state = obj.toggle();
        this.triggerStates[obj.id] = state;

        // Record switch toggle in Echo track
        this.echoSystem.recordFrame(0, this.player, {
          type: 'switch_toggle',
          targetId: obj.id,
          state: state
        });
        return;
      }
    }

    // 2. Check Memory Crystals
    for (const obj of this.puzzleObjects) {
      if (obj.type === 'memory_crystal' && obj.canInteract(pPos)) {
        const lore = obj.collect();
        this.stats.memoriesDiscovered++;
        this.ui.updateMemoryProgress(20 + this.stats.memoriesDiscovered * 20);
        this.ui.showDialogue(lore, "ANCIENT TIMELINE RESONANCE");
        return;
      }
    }

    // 3. Check Gravity Nodes
    for (const obj of this.puzzleObjects) {
      if (obj.type === 'gravity_node' && obj.canInteract(pPos)) {
        const inverted = obj.toggle();
        this.player.setGravityInverted(inverted);
        this.cameraController.addTrauma(0.35);
        return;
      }
    }
  }

  loadLevel(index) {
    if (index < 0 || index >= LEVELS.length) return;

    this.currentLevelIndex = index;
    const lvl = LEVELS[index];
    this.currentLevel = lvl;

    // Clear previous objects
    this.puzzleObjects = [];
    this.triggerStates = {};
    this.worldBuilder.clearWorld();

    if (this.firstEchoNPC) {
      this.scene.remove(this.firstEchoNPC);
      this.firstEchoNPC = null;
    }

    // 1. Apply World theme colors and audio
    this.worldBuilder.applyWorldTheme(lvl.worldIndex);
    soundManager.setWorldTheme(lvl.worldIndex);

    // 2. Build Floating Islands
    this.islandMeshes = [];
    lvl.islands.forEach(isl => {
      const created = this.worldBuilder.createFloatingIsland(
        isl.x,
        isl.y,
        isl.z,
        isl.width,
        isl.depth,
        isl.height
      );
      this.islandMeshes.push(created);
    });

    // 3. Build Waterfalls
    if (lvl.waterfalls) {
      lvl.waterfalls.forEach(wf => {
        this.worldBuilder.createWaterfall(wf.x, wf.y, wf.z, wf.width, wf.height);
      });
    }

    // 4. Build Giant Crystals
    if (lvl.crystals) {
      lvl.crystals.forEach(c => {
        this.worldBuilder.createGiantCrystal(c.x, c.y, c.z, c.scale, c.isViolet);
      });
    }

    // 5. Build Trees
    if (lvl.trees) {
      lvl.trees.forEach(t => {
        this.worldBuilder.createDreamTree(t.x, t.y, t.z, t.scale);
      });
    }

    // 6. Build Ancient Arches
    if (lvl.arches) {
      lvl.arches.forEach(a => {
        this.worldBuilder.createAncientArch(a.x, a.y, a.z, a.rotY);
      });
    }

    // 7. Floating idle rocks around islands
    this.worldBuilder.createFloatingStones(
      new THREE.Vector3(lvl.spawnPoint.x, lvl.spawnPoint.y, lvl.spawnPoint.z),
      14,
      35
    );

    // 8. Instantiate Puzzle Objects
    lvl.puzzleObjects.forEach(def => {
      let obj = null;
      if (def.type === 'pressure_plate') {
        obj = new PressurePlate(def.id, new THREE.Vector3(def.position.x, def.position.y, def.position.z), def, this.scene);
      } else if (def.type === 'switch') {
        obj = new MagicSwitch(def.id, new THREE.Vector3(def.position.x, def.position.y, def.position.z), def, this.scene);
      } else if (def.type === 'door') {
        obj = new MagicDoor(def.id, new THREE.Vector3(def.position.x, def.position.y, def.position.z), def, this.scene);
      } else if (def.type === 'moving_platform') {
        obj = new MovingPlatform(
          def.id,
          new THREE.Vector3(def.startPos.x, def.startPos.y, def.startPos.z),
          new THREE.Vector3(def.endPos.x, def.endPos.y, def.endPos.z),
          def,
          this.scene
        );
      } else if (def.type === 'bridge') {
        obj = new DisappearingBridge(def.id, new THREE.Vector3(def.position.x, def.position.y, def.position.z), def, this.scene);
      } else if (def.type === 'memory_crystal') {
        obj = new MemoryCrystal(def.id, new THREE.Vector3(def.position.x, def.position.y, def.position.z), def.loreText, this.scene);
      } else if (def.type === 'gravity_node') {
        obj = new GravityNode(def.id, new THREE.Vector3(def.position.x, def.position.y, def.position.z), def, this.scene);
      } else if (def.type === 'portal') {
        obj = new TeleportPortal(def.id, new THREE.Vector3(def.position.x, def.position.y, def.position.z), def, this.scene);
      }

      if (obj) {
        this.puzzleObjects.push(obj);
      }
    });

    // 9. Special Final Area Setup
    if (lvl.isFinalArea) {
      this.worldBuilder.createFinalSanctuaryEchoes(new THREE.Vector3(0, 0, 0));
      this.spawnFirstEchoFigure();
    }

    // 10. Position Player & Echo Anchor
    const spawnV = new THREE.Vector3(lvl.spawnPoint.x, lvl.spawnPoint.y + 0.1, lvl.spawnPoint.z);
    this.player.setCheckpoint(spawnV, lvl.spawnPoint.rotY);
    this.player.teleport(spawnV, lvl.spawnPoint.rotY);
    this.player.setGravityInverted(false);

    this.echoSystem.setMaxEchoes(lvl.maxEchoes);
    this.echoSystem.setAnchor(spawnV, lvl.spawnPoint.rotY);
    this.echoSystem.clearEchoes();

    // 11. Update UI
    this.ui.updateHUD(lvl, { activeEchoCount: 0 });
    this.ui.populateLevelSelect(WORLDS_DATA, LEVELS, lvl.id);

    // Initial cinematic sweep when awakening
    if (lvl.id === 'w1_l1') {
      const camStart = new THREE.Vector3(0, 12, -18);
      const lookAt = new THREE.Vector3(0, 1, 10);
      this.cameraController.playCinematic(camStart, lookAt, 3.2);
    }
  }

  // Spawns the legendary First Echo NPC in the Final Sanctuary
  spawnFirstEchoFigure() {
    const firstEchoGroup = new THREE.Group();
    firstEchoGroup.position.set(0, 0, 10);
    firstEchoGroup.rotation.y = Math.PI;

    // Translucent glowing anime figure
    const echoMat = new THREE.MeshStandardMaterial({
      color: 0x00f3ff,
      emissive: 0x00f3ff,
      emissiveIntensity: 1.2,
      roughness: 0.1,
      metalness: 0.3,
      transparent: true,
      opacity: 0.85
    });

    const head = new THREE.Mesh(new THREE.SphereGeometry(0.32, 16, 16), echoMat);
    head.position.y = 0.95;
    firstEchoGroup.add(head);

    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.2, 0.44, 16), echoMat);
    body.position.y = 0.62;
    firstEchoGroup.add(body);

    const scarf = new THREE.Mesh(new THREE.TorusGeometry(0.24, 0.08, 10, 16), echoMat);
    scarf.rotation.x = Math.PI / 2;
    scarf.position.y = 0.84;
    firstEchoGroup.add(scarf);

    // Raised glowing hand
    const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.05, 0.35, 8), echoMat);
    arm.position.set(0.32, 0.82, 0.12);
    arm.rotation.x = -Math.PI * 0.35;
    firstEchoGroup.add(arm);

    this.scene.add(firstEchoGroup);
    this.firstEchoNPC = firstEchoGroup;
  }

  startGame() {
    this.isGameActive = true;
    soundManager.ensureContext();
    this.loadLevel(0);
  }

  restartLevel() {
    this.loadLevel(this.currentLevelIndex);
  }

  returnToMenu() {
    this.isGameActive = false;
    this.loadLevel(0);
  }

  loadLevelById(id) {
    const idx = LEVELS.findIndex(l => l.id === id);
    if (idx !== -1) {
      this.isGameActive = true;
      this.loadLevel(idx);
    }
  }

  // Next level transition
  advanceToNextLevel() {
    this.stats.puzzlesSolved++;
    soundManager.playLevelComplete();
    this.particleManager.spawnVictoryBurst(this.player.position);
    this.ui.showLevelCompleteBanner();

    setTimeout(() => {
      if (this.currentLevelIndex + 1 < LEVELS.length) {
        this.loadLevel(this.currentLevelIndex + 1);
      } else {
        // Finale Triggered
        this.triggerGameEnding();
      }
    }, 1800);
  }

  triggerGameEnding() {
    this.isGameActive = false;
    this.cameraController.addTrauma(0.5);
    this.ui.showEndingScreen(this.stats);
  }

  animate() {
    requestAnimationFrame(this.animate);

    const delta = Math.min(this.clock.getDelta(), 0.06);

    // 1. Update Particle Manager
    this.particleManager.update(delta);

    // 2. Update World Builder idle animations
    this.worldBuilder.update(delta);

    // 3. Update Player & Echo System
    if (this.isGameActive && this.currentLevel) {
      // Gather active entities (Player + Echoes) for pressure plate triggers
      const echoPositions = this.echoSystem.activeEchoes.map(e => ({
        position: e.getCurrentPosition()
      }));
      const allEntities = [{ position: this.player.position }, ...echoPositions];

      // Update Puzzle Objects and gather trigger states
      this.puzzleObjects.forEach(obj => {
        if (obj.type === 'pressure_plate') {
          const isPressed = obj.update(delta, allEntities);
          this.triggerStates[obj.id] = isPressed;
        } else if (obj.type === 'switch') {
          const isActive = obj.update(delta);
          this.triggerStates[obj.id] = isActive;
        } else if (obj.type === 'moving_platform') {
          obj.update(delta, this.triggerStates);
        } else if (obj.type === 'bridge') {
          obj.update(delta, this.triggerStates);
        } else if (obj.type === 'door') {
          obj.update(delta, this.triggerStates);
        } else if (obj.type === 'memory_crystal') {
          obj.update(delta);
        } else if (obj.type === 'gravity_node') {
          obj.update(delta);
        } else if (obj.type === 'portal') {
          obj.update(delta);

          // Check if player enters portal
          if (obj.isPlayerEntering(this.player.position)) {
            if (obj.isFinalPortal) {
              this.triggerGameEnding();
            } else {
              this.advanceToNextLevel();
            }
          }
        }
      });

      // Update Player Controller
      const playerState = this.player.update(
        delta,
        this.islandMeshes,
        this.puzzleObjects
      );

      // Record player state into current Echo timeline
      this.echoSystem.recordFrame(delta, playerState);

      // Update Echoes playback & synchronization
      const echoUpdateResult = this.echoSystem.update(delta, this.puzzleObjects);

      // Update Timeline HUD
      this.ui.updateTimelineStatus(
        echoUpdateResult.recordDuration,
        this.echoSystem.maxRecordDuration,
        this.echoSystem.isRecording,
        echoUpdateResult.replayTime,
        echoUpdateResult.activeEchoCount > 0
      );

      this.ui.updateHUD(this.currentLevel, {
        activeEchoCount: echoUpdateResult.activeEchoCount
      });

      // Check interaction prompts near player
      this.checkProximityPrompts();

      // Check Final Encounter with First Echo
      if (this.currentLevel.isFinalArea && this.firstEchoNPC) {
        const dist = this.player.position.distanceTo(this.firstEchoNPC.position);
        if (dist < 4.5 && !this.hasEncounteredFirstEcho) {
          this.hasEncounteredFirstEcho = true;
          this.ui.showDialogue(
            "THE FIRST ECHO: 'You were never alone. Every step you took through this shattered reality was guided by the first version of yourself that dreamed of reaching this place. Walk with me into eternity.'",
            "THE FIRST ECHO"
          );
        }
      }

      // Update Camera follow
      this.cameraController.update(
        delta,
        this.player.position,
        this.player.rotationY,
        playerState.isMoving,
        playerState.isRunning
      );
    } else {
      // Menu Camera slow scenic orbit
      const t = performance.now() * 0.00035;
      const camX = Math.cos(t) * 16;
      const camZ = Math.sin(t) * 16;
      this.camera.position.set(camX, 8, camZ);
      this.camera.lookAt(0, 1.5, 0);
    }

    // Render Scene
    this.renderer.render(this.scene, this.camera);
  }

  checkProximityPrompts() {
    const pPos = this.player.position;
    let foundPrompt = false;

    // Check switches
    for (const obj of this.puzzleObjects) {
      if (obj.type === 'switch' && obj.canInteract(pPos)) {
        this.ui.showInteractionPrompt("TOGGLE SWITCH", "E");
        foundPrompt = true;
        break;
      }
    }

    // Check memory crystals
    if (!foundPrompt) {
      for (const obj of this.puzzleObjects) {
        if (obj.type === 'memory_crystal' && obj.canInteract(pPos)) {
          this.ui.showInteractionPrompt("READ MEMORY CRYSTAL", "E");
          foundPrompt = true;
          break;
        }
      }
    }

    // Check gravity nodes
    if (!foundPrompt) {
      for (const obj of this.puzzleObjects) {
        if (obj.type === 'gravity_node' && obj.canInteract(pPos)) {
          this.ui.showInteractionPrompt("INVERT GRAVITY", "E");
          foundPrompt = true;
          break;
        }
      }
    }

    if (!foundPrompt) {
      this.ui.hideInteractionPrompt();
    }
  }
}

// Start Game Instance on DOM load
window.addEventListener('DOMContentLoaded', () => {
  window.game = new EchoboundGame();
});
