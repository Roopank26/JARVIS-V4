// ECHOBOUND — Particle Systems (Trails, Portals, Waterfalls, Ambient Sparks)
import * as THREE from 'three';

export class ParticleManager {
  constructor(scene) {
    this.scene = scene;
    this.systems = [];

    this.initAmbientSparks();
    this.initTrailPool();
  }

  // Soft glowing circle sprite texture generated on canvas
  createParticleTexture(colorHex = '#00f3ff') {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');

    const grad = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    grad.addColorStop(0, '#ffffff');
    grad.addColorStop(0.3, colorHex);
    grad.addColorStop(0.7, 'rgba(0, 200, 255, 0.3)');
    grad.addColorStop(1, 'rgba(0, 0, 0, 0)');

    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 64, 64);

    const texture = new THREE.CanvasTexture(canvas);
    return texture;
  }

  initAmbientSparks() {
    const count = 350;
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const speeds = new Float32Array(count);

    const cyan = new THREE.Color(0x00f3ff);
    const gold = new THREE.Color(0xffd166);
    const violet = new THREE.Color(0xbf55ec);

    for (let i = 0; i < count; i++) {
      positions[i * 3 + 0] = (Math.random() - 0.5) * 60;
      positions[i * 3 + 1] = Math.random() * 25 - 2;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 60;

      const r = Math.random();
      const col = r > 0.6 ? cyan : (r > 0.3 ? gold : violet);
      colors[i * 3 + 0] = col.r;
      colors[i * 3 + 1] = col.g;
      colors[i * 3 + 2] = col.b;

      speeds[i] = 0.5 + Math.random() * 1.5;
    }

    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const mat = new THREE.PointsMaterial({
      size: 0.35,
      map: this.createParticleTexture('#ffffff'),
      vertexColors: true,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    this.ambientPoints = new THREE.Points(geo, mat);
    this.scene.add(this.ambientPoints);
    this.ambientSpeeds = speeds;
  }

  initTrailPool() {
    this.trails = [];
  }

  // Spawn trailing motes behind an Echo or Player
  spawnTrail(position, color = 0x00f3ff, size = 0.25) {
    const geo = new THREE.BufferGeometry();
    const pos = new Float32Array([position.x + (Math.random() - 0.5) * 0.1, position.y + (Math.random() - 0.5) * 0.1, position.z + (Math.random() - 0.5) * 0.1]);
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));

    const mat = new THREE.PointsMaterial({
      size: size,
      color: color,
      map: this.createParticleTexture(color === 0xbf55ec ? '#bf55ec' : '#00f3ff'),
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    const point = new THREE.Points(geo, mat);
    this.scene.add(point);

    this.trails.push({
      mesh: point,
      life: 0.8,
      maxLife: 0.8,
      vy: 0.2 + Math.random() * 0.3
    });
  }

  // Echo summon visual burst
  spawnEchoSummonBurst(origin) {
    const count = 60;
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    const velocities = [];

    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = 1.8 + Math.random() * 0.8;
      const height = Math.random() * 1.8;

      positions[i * 3 + 0] = origin.x + Math.cos(angle) * radius;
      positions[i * 3 + 1] = origin.y + height;
      positions[i * 3 + 2] = origin.z + Math.sin(angle) * radius;

      // Inward gathering velocity for reversed effect
      velocities.push({
        vx: -Math.cos(angle) * (3.5 + Math.random() * 2),
        vy: (0.9 - height) * 2,
        vz: -Math.sin(angle) * (3.5 + Math.random() * 2)
      });
    }

    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const mat = new THREE.PointsMaterial({
      size: 0.45,
      color: 0x00ffff,
      map: this.createParticleTexture('#00ffff'),
      transparent: true,
      opacity: 0.9,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    const burst = new THREE.Points(geo, mat);
    this.scene.add(burst);

    this.systems.push({
      mesh: burst,
      velocities: velocities,
      life: 0.55,
      maxLife: 0.55,
      inward: true
    });
  }

  // Footstep dust / spark puff
  spawnFootstepPuff(pos) {
    const count = 8;
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    const velocities = [];

    for (let i = 0; i < count; i++) {
      positions[i * 3 + 0] = pos.x;
      positions[i * 3 + 1] = pos.y + 0.05;
      positions[i * 3 + 2] = pos.z;

      const angle = Math.random() * Math.PI * 2;
      const spd = 0.4 + Math.random() * 0.6;
      velocities.push({
        vx: Math.cos(angle) * spd,
        vy: 0.3 + Math.random() * 0.4,
        vz: Math.sin(angle) * spd
      });
    }

    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const mat = new THREE.PointsMaterial({
      size: 0.2,
      color: 0x88eeff,
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    const puff = new THREE.Points(geo, mat);
    this.scene.add(puff);

    this.systems.push({
      mesh: puff,
      velocities: velocities,
      life: 0.35,
      maxLife: 0.35
    });
  }

  // Puzzle Solved fireworks burst
  spawnVictoryBurst(pos) {
    const count = 120;
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const velocities = [];

    const colorPalette = [new THREE.Color(0x00f3ff), new THREE.Color(0xffd166), new THREE.Color(0xff70a6), new THREE.Color(0x70d6ff)];

    for (let i = 0; i < count; i++) {
      positions[i * 3 + 0] = pos.x;
      positions[i * 3 + 1] = pos.y + 1.2;
      positions[i * 3 + 2] = pos.z;

      const phi = Math.random() * Math.PI * 2;
      const theta = Math.random() * Math.PI;
      const speed = 2.5 + Math.random() * 4.5;

      velocities.push({
        vx: Math.sin(theta) * Math.cos(phi) * speed,
        vy: Math.cos(theta) * speed + 1.5,
        vz: Math.sin(theta) * Math.sin(phi) * speed
      });

      const col = colorPalette[Math.floor(Math.random() * colorPalette.length)];
      colors[i * 3 + 0] = col.r;
      colors[i * 3 + 1] = col.g;
      colors[i * 3 + 2] = col.b;
    }

    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const mat = new THREE.PointsMaterial({
      size: 0.4,
      vertexColors: true,
      map: this.createParticleTexture('#ffffff'),
      transparent: true,
      opacity: 1.0,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    const p = new THREE.Points(geo, mat);
    this.scene.add(p);

    this.systems.push({
      mesh: p,
      velocities: velocities,
      life: 1.5,
      maxLife: 1.5,
      gravity: -6.0
    });
  }

  update(delta) {
    // 1. Update Ambient Sparks
    if (this.ambientPoints) {
      const pos = this.ambientPoints.geometry.attributes.position.array;
      for (let i = 0; i < pos.length / 3; i++) {
        pos[i * 3 + 1] += this.ambientSpeeds[i] * delta;
        pos[i * 3 + 0] += Math.sin(pos[i * 3 + 1] * 0.5) * 0.02;
        if (pos[i * 3 + 1] > 22) {
          pos[i * 3 + 1] = -2;
        }
      }
      this.ambientPoints.geometry.attributes.position.needsUpdate = true;
    }

    // 2. Update Trails
    for (let i = this.trails.length - 1; i >= 0; i--) {
      const t = this.trails[i];
      t.life -= delta;
      if (t.life <= 0) {
        this.scene.remove(t.mesh);
        t.mesh.geometry.dispose();
        t.mesh.material.dispose();
        this.trails.splice(i, 1);
      } else {
        const ratio = t.life / t.maxLife;
        t.mesh.material.opacity = ratio * 0.8;
        t.mesh.material.size *= (1 - delta * 0.5);
        const p = t.mesh.geometry.attributes.position.array;
        p[1] += t.vy * delta;
        t.mesh.geometry.attributes.position.needsUpdate = true;
      }
    }

    // 3. Update Systems (Bursts, Puffs, etc.)
    for (let i = this.systems.length - 1; i >= 0; i--) {
      const sys = this.systems[i];
      sys.life -= delta;
      if (sys.life <= 0) {
        this.scene.remove(sys.mesh);
        sys.mesh.geometry.dispose();
        sys.mesh.material.dispose();
        this.systems.splice(i, 1);
      } else {
        const ratio = sys.life / sys.maxLife;
        sys.mesh.material.opacity = ratio;
        const pos = sys.mesh.geometry.attributes.position.array;
        const vels = sys.velocities;
        const g = sys.gravity || 0;

        for (let j = 0; j < vels.length; j++) {
          pos[j * 3 + 0] += vels[j].vx * delta;
          pos[j * 3 + 1] += vels[j].vy * delta;
          pos[j * 3 + 2] += vels[j].vz * delta;
          vels[j].vy += g * delta;
        }
        sys.mesh.geometry.attributes.position.needsUpdate = true;
      }
    }
  }
}
