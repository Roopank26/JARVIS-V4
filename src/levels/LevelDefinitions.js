// ECHOBOUND — Level & World Configurations

export const WORLDS_DATA = [
  {
    worldIndex: 1,
    name: "WORLD 1 — FLOATING ISLANDS",
    subtitle: "The Awakening of Time",
    theme: 1,
    maxEchoes: 1,
    description: "Lush floating islands drifting in a sea of clouds. Here, NEO awakens to the strange resonance of time."
  },
  {
    worldIndex: 2,
    name: "WORLD 2 — CRYSTAL FOREST",
    subtitle: "The Harmonic Resonance",
    theme: 2,
    maxEchoes: 2,
    description: "A dark mystical forest crowned with giant bioluminescent violet and cyan crystals."
  },
  {
    worldIndex: 3,
    name: "WORLD 3 — ANCIENT RUINS",
    subtitle: "The Temples of the Forgotten",
    theme: 3,
    maxEchoes: 2,
    description: "Weathered floating sanctuaries where ancient dials and timed mechanisms guard lost truths."
  },
  {
    worldIndex: 4,
    name: "WORLD 4 — BROKEN REALITY",
    subtitle: "The Fractured Continuum",
    theme: 4,
    maxEchoes: 2,
    description: "A shattered dimension where gravity reverses and geometry bends to forgotten echoes."
  },
  {
    worldIndex: 5,
    name: "WORLD 5 — THE MEMORY VOID",
    subtitle: "The Cosmic Nexus",
    theme: 5,
    maxEchoes: 3,
    description: "Deep starlit void holding adrift remnants of all past worlds and untold timelines."
  },
  {
    worldIndex: 6,
    name: "FINAL AREA — THE FIRST ECHO",
    subtitle: "The One Who Guided You",
    theme: 5,
    maxEchoes: 0,
    description: "The celestial convergence where past and present unite."
  }
];

export const LEVELS = [
  // ==========================================
  // WORLD 1: FLOATING ISLANDS
  // ==========================================
  {
    id: "w1_l1",
    worldIndex: 1,
    levelNumber: 1,
    title: "Awakening",
    subtitle: "Learn movement and view the realm",
    loreHint: "Where am I? The wind whispers a name... Neo.",
    maxEchoes: 0, // Not needed yet
    spawnPoint: { x: 0, y: 0, z: 0, rotY: 0 },
    islands: [
      { x: 0, y: 0, z: 0, width: 14, depth: 14, height: 6 },
      { x: 0, y: 0, z: 12, width: 8, depth: 8, height: 4 },
      { x: 0, y: 0.5, z: 24, width: 12, depth: 12, height: 5 }
    ],
    waterfalls: [
      { x: 5, y: 0, z: 2, width: 2.2, height: 16 }
    ],
    crystals: [
      { x: -4, y: 0, z: 3, scale: 1.2, isViolet: false },
      { x: 4, y: 0.5, z: 25, scale: 1.5, isViolet: true }
    ],
    trees: [
      { x: -3.5, y: 0, z: -3.5, scale: 1.2 },
      { x: 3.5, y: 0.5, z: 22, scale: 1.0 }
    ],
    arches: [
      { x: 0, y: 0.5, z: 20, rotY: 0 }
    ],
    puzzleObjects: [
      {
        type: 'portal',
        id: 'portal_1_1',
        position: { x: 0, y: 0.5, z: 26 },
        destinationWorld: 1,
        destinationLevel: 2
      }
    ]
  },
  {
    id: "w1_l2",
    worldIndex: 1,
    levelNumber: 2,
    title: "The Ancient Gate",
    subtitle: "Step onto the pressure plate to lower the gate",
    loreHint: "The ancient stone hums with dormant energy.",
    maxEchoes: 0,
    spawnPoint: { x: 0, y: 0, z: -8, rotY: 0 },
    islands: [
      { x: 0, y: 0, z: -6, width: 12, depth: 12, height: 5 },
      { x: 0, y: 0, z: 10, width: 14, depth: 14, height: 5 }
    ],
    waterfalls: [
      { x: -4.5, y: 0, z: -4, width: 2.0, height: 14 }
    ],
    crystals: [
      { x: 4, y: 0, z: -5, scale: 1.3, isViolet: false }
    ],
    puzzleObjects: [
      {
        type: 'pressure_plate',
        id: 'plate_1_2',
        position: { x: 0, y: 0, z: -3 },
        targets: ['door_1_2']
      },
      {
        type: 'door',
        id: 'door_1_2',
        position: { x: 0, y: 0, z: 2 },
        requiredTriggers: ['plate_1_2']
      },
      {
        type: 'portal',
        id: 'portal_1_2',
        position: { x: 0, y: 0, z: 12 },
        destinationWorld: 1,
        destinationLevel: 3
      }
    ]
  },
  {
    id: "w1_l3",
    worldIndex: 1,
    levelNumber: 3,
    title: "The First Echo",
    subtitle: "Record yourself holding the switch, then press [R] to summon your Echo!",
    loreHint: "The plate is too far from the gate... If only I could be in two places at once.",
    maxEchoes: 1,
    spawnPoint: { x: 0, y: 0, z: -8, rotY: 0 },
    islands: [
      { x: 0, y: 0, z: -6, width: 14, depth: 14, height: 5 },
      { x: -9, y: 0, z: -4, width: 8, depth: 8, height: 4 }, // Echo Plate island
      { x: 0, y: 0, z: 12, width: 14, depth: 14, height: 5 }
    ],
    waterfalls: [
      { x: -7, y: 0, z: -6, width: 2.0, height: 15 }
    ],
    crystals: [
      { x: -9, y: 0, z: -2, scale: 1.4, isViolet: false }
    ],
    puzzleObjects: [
      {
        type: 'pressure_plate',
        id: 'plate_1_3',
        position: { x: -9, y: 0, z: -4 },
        targets: ['door_1_3']
      },
      {
        type: 'door',
        id: 'door_1_3',
        position: { x: 0, y: 0, z: 3 },
        requiredTriggers: ['plate_1_3']
      },
      {
        type: 'portal',
        id: 'portal_1_3',
        position: { x: 0, y: 0, z: 14 },
        destinationWorld: 1,
        destinationLevel: 4
      }
    ]
  },
  {
    id: "w1_l4",
    worldIndex: 1,
    levelNumber: 4,
    title: "The Stepping Bridges",
    subtitle: "Your Echo must maintain the bridge while you navigate the chasm",
    loreHint: "Light solidifies beneath the Echo's weight.",
    maxEchoes: 1,
    spawnPoint: { x: 0, y: 0, z: -10, rotY: 0 },
    islands: [
      { x: 0, y: 0, z: -8, width: 12, depth: 12, height: 5 },
      { x: 8, y: 0, z: -8, width: 8, depth: 8, height: 4 }, // Plate platform
      { x: 0, y: 0, z: 12, width: 12, depth: 12, height: 5 }
    ],
    crystals: [
      { x: 8, y: 0, z: -6, scale: 1.5, isViolet: true }
    ],
    puzzleObjects: [
      {
        type: 'pressure_plate',
        id: 'plate_1_4',
        position: { x: 8, y: 0, z: -8 },
        targets: ['bridge_1_4']
      },
      {
        type: 'bridge',
        id: 'bridge_1_4',
        position: { x: 0, y: 0, z: 2 },
        length: 8.0,
        width: 2.8,
        triggerId: 'plate_1_4'
      },
      {
        type: 'portal',
        id: 'portal_1_4',
        position: { x: 0, y: 0, z: 14 },
        destinationWorld: 1,
        destinationLevel: 5
      }
    ]
  },
  {
    id: "w1_l5",
    worldIndex: 1,
    levelNumber: 5,
    title: "The Dual Pillars",
    subtitle: "Simultaneously hold both shrines to activate the Grand World Portal!",
    loreHint: "Two hearts beating across the same timeline.",
    maxEchoes: 1,
    spawnPoint: { x: 0, y: 0, z: -8, rotY: 0 },
    islands: [
      { x: 0, y: 0, z: -6, width: 14, depth: 14, height: 5 },
      { x: -8, y: 0, z: 2, width: 8, depth: 8, height: 4 },
      { x: 8, y: 0, z: 2, width: 8, depth: 8, height: 4 },
      { x: 0, y: 0.5, z: 14, width: 14, depth: 14, height: 5 }
    ],
    waterfalls: [
      { x: 0, y: 0.5, z: 18, width: 3.5, height: 18 }
    ],
    crystals: [
      { x: -8, y: 0, z: 4, scale: 1.6, isViolet: false },
      { x: 8, y: 0, z: 4, scale: 1.6, isViolet: true }
    ],
    puzzleObjects: [
      {
        type: 'pressure_plate',
        id: 'plate_1_5_A',
        position: { x: -8, y: 0, z: 2 }
      },
      {
        type: 'pressure_plate',
        id: 'plate_1_5_B',
        position: { x: 8, y: 0, z: 2 }
      },
      {
        type: 'door',
        id: 'door_1_5',
        position: { x: 0, y: 0.5, z: 8 },
        requiredTriggers: ['plate_1_5_A', 'plate_1_5_B']
      },
      {
        type: 'portal',
        id: 'portal_world_2',
        position: { x: 0, y: 0.5, z: 16 },
        isWorldExit: true,
        destinationWorld: 2,
        destinationLevel: 1
      }
    ]
  },

  // ==========================================
  // WORLD 2: CRYSTAL FOREST
  // ==========================================
  {
    id: "w2_l1",
    worldIndex: 2,
    levelNumber: 1,
    title: "Crystal Resonance",
    subtitle: "Coordinate moving platforms with your Echo",
    loreHint: "The crystals hum at a frequency that fractures memory.",
    maxEchoes: 1,
    spawnPoint: { x: 0, y: 0, z: -10, rotY: 0 },
    islands: [
      { x: 0, y: 0, z: -8, width: 14, depth: 14, height: 5 },
      { x: 0, y: 0, z: 14, width: 14, depth: 14, height: 5 }
    ],
    crystals: [
      { x: -5, y: 0, z: -7, scale: 2.2, isViolet: true },
      { x: 5, y: 0, z: -7, scale: 2.0, isViolet: false },
      { x: 5, y: 0, z: 15, scale: 2.4, isViolet: true }
    ],
    puzzleObjects: [
      {
        type: 'switch',
        id: 'switch_2_1',
        position: { x: -4, y: 0, z: -8 }
      },
      {
        type: 'moving_platform',
        id: 'plat_2_1',
        startPos: { x: 0, y: 0, z: -2 },
        endPos: { x: 0, y: 0, z: 8 },
        speed: 2.4,
        requiresTrigger: true,
        triggerId: 'switch_2_1'
      },
      {
        type: 'portal',
        id: 'portal_2_1',
        position: { x: 0, y: 0, z: 16 },
        destinationWorld: 2,
        destinationLevel: 2
      }
    ]
  },
  {
    id: "w2_l2",
    worldIndex: 2,
    levelNumber: 2,
    title: "The Shifting Chasm",
    subtitle: "Echo holds the hard-light circuit while Neo crosses",
    loreHint: "A memory is just a bridge built across nothingness.",
    maxEchoes: 1,
    spawnPoint: { x: -10, y: 0, z: 0, rotY: Math.PI / 2 },
    islands: [
      { x: -10, y: 0, z: 0, width: 12, depth: 12, height: 5 },
      { x: 10, y: 0, z: 0, width: 12, depth: 12, height: 5 }
    ],
    crystals: [
      { x: -10, y: 0, z: 4, scale: 1.8, isViolet: true },
      { x: 10, y: 0, z: 4, scale: 2.0, isViolet: false }
    ],
    puzzleObjects: [
      {
        type: 'pressure_plate',
        id: 'plate_2_2',
        position: { x: -10, y: 0, z: -3 }
      },
      {
        type: 'bridge',
        id: 'bridge_2_2',
        position: { x: 0, y: 0, z: 0 },
        length: 10.0,
        width: 2.6,
        rotationY: Math.PI / 2,
        triggerId: 'plate_2_2'
      },
      {
        type: 'portal',
        id: 'portal_2_2',
        position: { x: 12, y: 0, z: 0 },
        destinationWorld: 2,
        destinationLevel: 3
      }
    ]
  },
  {
    id: "w2_l3",
    worldIndex: 2,
    levelNumber: 3,
    title: "Echo Synchronization",
    subtitle: "Ride the ascending platform while Echo powers the lift",
    loreHint: "Timing is an illusion created by consciousness.",
    maxEchoes: 1,
    spawnPoint: { x: 0, y: 0, z: -8, rotY: 0 },
    islands: [
      { x: 0, y: 0, z: -6, width: 12, depth: 12, height: 5 },
      { x: 0, y: 5.0, z: 12, width: 14, depth: 14, height: 5 } // High island
    ],
    crystals: [
      { x: 0, y: 5.0, z: 16, scale: 2.5, isViolet: true }
    ],
    puzzleObjects: [
      {
        type: 'switch',
        id: 'switch_2_3',
        position: { x: -4, y: 0, z: -6 },
        isTimed: true,
        duration: 8.0
      },
      {
        type: 'moving_platform',
        id: 'plat_2_3',
        startPos: { x: 0, y: 0, z: 2 },
        endPos: { x: 0, y: 5.0, z: 7 },
        speed: 2.0,
        requiresTrigger: true,
        triggerId: 'switch_2_3'
      },
      {
        type: 'portal',
        id: 'portal_2_3',
        position: { x: 0, y: 5.0, z: 14 },
        destinationWorld: 2,
        destinationLevel: 4
      }
    ]
  },
  {
    id: "w2_l4",
    worldIndex: 2,
    levelNumber: 4,
    title: "Dual Echo Awakening",
    subtitle: "Unlock 2 simultaneous Echoes! Cooperate with both past selves.",
    loreHint: "The traveler who came before... why do their footsteps match my own?",
    maxEchoes: 2, // 2 Echoes unlocked!
    spawnPoint: { x: 0, y: 0, z: -10, rotY: 0 },
    islands: [
      { x: 0, y: 0, z: -8, width: 14, depth: 14, height: 5 },
      { x: -9, y: 0, z: 2, width: 8, depth: 8, height: 4 },
      { x: 9, y: 0, z: 2, width: 8, depth: 8, height: 4 },
      { x: 0, y: 0, z: 16, width: 16, depth: 16, height: 6 }
    ],
    crystals: [
      { x: -9, y: 0, z: 4, scale: 2.2, isViolet: false },
      { x: 9, y: 0, z: 4, scale: 2.2, isViolet: true }
    ],
    puzzleObjects: [
      {
        type: 'pressure_plate',
        id: 'plate_2_4_A',
        position: { x: -9, y: 0, z: 2 }
      },
      {
        type: 'pressure_plate',
        id: 'plate_2_4_B',
        position: { x: 9, y: 0, z: 2 }
      },
      {
        type: 'door',
        id: 'door_2_4',
        position: { x: 0, y: 0, z: 8 },
        requiredTriggers: ['plate_2_4_A', 'plate_2_4_B']
      },
      {
        type: 'memory_crystal',
        id: 'mem_crystal_1',
        position: { x: -3, y: 0, z: 14 },
        loreText: "MEMORY FRAGMENT I: 'I remember this path. Or did I only imagine waking up here? Every Echo I create feels familiar... like an old friend.'"
      },
      {
        type: 'portal',
        id: 'portal_world_3',
        position: { x: 0, y: 0, z: 18 },
        isWorldExit: true,
        destinationWorld: 3,
        destinationLevel: 1
      }
    ]
  },

  // ==========================================
  // WORLD 3: ANCIENT RUINS
  // ==========================================
  {
    id: "w3_l1",
    worldIndex: 3,
    levelNumber: 1,
    title: "Temple of Dials",
    subtitle: "Navigate the timed sanctuary mechanisms with multiple Echoes",
    loreHint: "These temples were constructed for beings of non-linear time.",
    maxEchoes: 2,
    spawnPoint: { x: 0, y: 0, z: -10, rotY: 0 },
    islands: [
      { x: 0, y: 0, z: -8, width: 14, depth: 14, height: 5 },
      { x: -8, y: 0, z: 0, width: 8, depth: 8, height: 4 },
      { x: 0, y: 0, z: 14, width: 14, depth: 14, height: 5 }
    ],
    arches: [
      { x: 0, y: 0, z: -3, rotY: 0 },
      { x: 0, y: 0, z: 9, rotY: 0 }
    ],
    puzzleObjects: [
      {
        type: 'switch',
        id: 'switch_3_1',
        position: { x: -8, y: 0, z: 0 },
        isTimed: true,
        duration: 9.0
      },
      {
        type: 'moving_platform',
        id: 'plat_3_1',
        startPos: { x: 0, y: 0, z: -1 },
        endPos: { x: 0, y: 0, z: 8 },
        speed: 2.8,
        requiresTrigger: true,
        triggerId: 'switch_3_1'
      },
      {
        type: 'portal',
        id: 'portal_3_1',
        position: { x: 0, y: 0, z: 16 },
        destinationWorld: 3,
        destinationLevel: 2
      }
    ]
  },
  {
    id: "w3_l2",
    worldIndex: 3,
    levelNumber: 2,
    title: "The Echo Relay",
    subtitle: "Echo 1 opens Gate 1. Echo 2 rushes through to open Gate 2. Neo crosses to safety!",
    loreHint: "Relaying actions across the boundaries of seconds.",
    maxEchoes: 2,
    spawnPoint: { x: 0, y: 0, z: -12, rotY: 0 },
    islands: [
      { x: 0, y: 0, z: -10, width: 14, depth: 14, height: 5 },
      { x: 0, y: 0, z: 0, width: 10, depth: 10, height: 4 },
      { x: 0, y: 0, z: 14, width: 14, depth: 14, height: 5 }
    ],
    arches: [
      { x: 0, y: 0, z: -5, rotY: 0 },
      { x: 0, y: 0, z: 7, rotY: 0 }
    ],
    puzzleObjects: [
      {
        type: 'pressure_plate',
        id: 'plate_3_2_A',
        position: { x: -4, y: 0, z: -10 }
      },
      {
        type: 'door',
        id: 'door_3_2_A',
        position: { x: 0, y: 0, z: -5 },
        requiredTriggers: ['plate_3_2_A']
      },
      {
        type: 'pressure_plate',
        id: 'plate_3_2_B',
        position: { x: 3, y: 0, z: 0 }
      },
      {
        type: 'door',
        id: 'door_3_2_B',
        position: { x: 0, y: 0, z: 7 },
        requiredTriggers: ['plate_3_2_B']
      },
      {
        type: 'memory_crystal',
        id: 'mem_crystal_2',
        position: { x: -3, y: 0, z: 12 },
        loreText: "MEMORY FRAGMENT II: 'These ruins were not built for one traveler. They were built for one traveler who exists across multiple moments at once.'"
      },
      {
        type: 'portal',
        id: 'portal_world_4',
        position: { x: 0, y: 0, z: 16 },
        isWorldExit: true,
        destinationWorld: 4,
        destinationLevel: 1
      }
    ]
  },

  // ==========================================
  // WORLD 4: BROKEN REALITY
  // ==========================================
  {
    id: "w4_l1",
    worldIndex: 4,
    levelNumber: 1,
    title: "The Gravity Inversion",
    subtitle: "Use the Gravity Node to traverse inverted platforms",
    loreHint: "When gravity shatters, the Echo remembers true down.",
    maxEchoes: 2,
    spawnPoint: { x: 0, y: 0, z: -8, rotY: 0 },
    islands: [
      { x: 0, y: 0, z: -6, width: 14, depth: 14, height: 5 },
      { x: 0, y: 0, z: 12, width: 14, depth: 14, height: 5 }
    ],
    crystals: [
      { x: -5, y: 0, z: -5, scale: 2.0, isViolet: true },
      { x: 5, y: 0, z: 13, scale: 2.2, isViolet: true }
    ],
    puzzleObjects: [
      {
        type: 'gravity_node',
        id: 'grav_4_1',
        position: { x: -3, y: 0, z: -6 }
      },
      {
        type: 'switch',
        id: 'switch_4_1',
        position: { x: 3, y: 0, z: -6 }
      },
      {
        type: 'bridge',
        id: 'bridge_4_1',
        position: { x: 0, y: 0, z: 3 },
        length: 8.0,
        width: 3.0,
        triggerId: 'switch_4_1'
      },
      {
        type: 'portal',
        id: 'portal_4_1',
        position: { x: 0, y: 0, z: 14 },
        destinationWorld: 4,
        destinationLevel: 2
      }
    ]
  },
  {
    id: "w4_l2",
    worldIndex: 4,
    levelNumber: 2,
    title: "The Glitch Fracture",
    subtitle: "Synchronize across reality tears",
    loreHint: "Reality did not break by accident. It shattered under the weight of countless forgotten timelines.",
    maxEchoes: 2,
    spawnPoint: { x: 0, y: 0, z: -10, rotY: 0 },
    islands: [
      { x: 0, y: 0, z: -8, width: 14, depth: 14, height: 5 },
      { x: -8, y: 0, z: 2, width: 8, depth: 8, height: 4 },
      { x: 8, y: 0, z: 2, width: 8, depth: 8, height: 4 },
      { x: 0, y: 0, z: 16, width: 14, depth: 14, height: 5 }
    ],
    puzzleObjects: [
      {
        type: 'pressure_plate',
        id: 'plate_4_2_A',
        position: { x: -8, y: 0, z: 2 }
      },
      {
        type: 'switch',
        id: 'switch_4_2_B',
        position: { x: 8, y: 0, z: 2 }
      },
      {
        type: 'door',
        id: 'door_4_2',
        position: { x: 0, y: 0, z: 8 },
        requiredTriggers: ['plate_4_2_A', 'switch_4_2_B']
      },
      {
        type: 'memory_crystal',
        id: 'mem_crystal_3',
        position: { x: -3, y: 0, z: 14 },
        loreText: "MEMORY FRAGMENT III: 'Someone was here before you. That Echo isn't following you... it was waiting for you all along.'"
      },
      {
        type: 'portal',
        id: 'portal_world_5',
        position: { x: 0, y: 0, z: 18 },
        isWorldExit: true,
        destinationWorld: 5,
        destinationLevel: 1
      }
    ]
  },

  // ==========================================
  // WORLD 5: THE MEMORY VOID
  // ==========================================
  {
    id: "w5_l1",
    worldIndex: 5,
    levelNumber: 1,
    title: "Fragments of Memory",
    subtitle: "3 Echoes Unlocked! Reclaim the fragments of all previous worlds.",
    loreHint: "Here at the edge of existence, time is infinite.",
    maxEchoes: 3,
    spawnPoint: { x: 0, y: 0, z: -12, rotY: 0 },
    islands: [
      { x: 0, y: 0, z: -10, width: 14, depth: 14, height: 5 },
      { x: -9, y: 0, z: 0, width: 8, depth: 8, height: 4 },
      { x: 9, y: 0, z: 0, width: 8, depth: 8, height: 4 },
      { x: 0, y: 0, z: 16, width: 16, depth: 16, height: 6 }
    ],
    crystals: [
      { x: -9, y: 0, z: 2, scale: 2.2, isViolet: true },
      { x: 9, y: 0, z: 2, scale: 2.2, isViolet: false },
      { x: 0, y: 0, z: 20, scale: 2.8, isViolet: true }
    ],
    puzzleObjects: [
      {
        type: 'pressure_plate',
        id: 'plate_5_1_A',
        position: { x: -9, y: 0, z: 0 }
      },
      {
        type: 'pressure_plate',
        id: 'plate_5_1_B',
        position: { x: 9, y: 0, z: 0 }
      },
      {
        type: 'switch',
        id: 'switch_5_1_C',
        position: { x: 0, y: 0, z: -7 }
      },
      {
        type: 'door',
        id: 'door_5_1',
        position: { x: 0, y: 0, z: 7 },
        requiredTriggers: ['plate_5_1_A', 'plate_5_1_B', 'switch_5_1_C']
      },
      {
        type: 'portal',
        id: 'portal_final_area',
        position: { x: 0, y: 0, z: 18 },
        isWorldExit: true,
        destinationWorld: 6,
        destinationLevel: 1
      }
    ]
  },

  // ==========================================
  // FINAL AREA: THE FIRST ECHO
  // ==========================================
  {
    id: "w6_final",
    worldIndex: 6,
    levelNumber: 1,
    title: "The First Echo",
    subtitle: "The World That Remembers You",
    loreHint: "Hundreds of Echoes watch in reverent silence.",
    maxEchoes: 0,
    isFinalArea: true,
    spawnPoint: { x: 0, y: 0, z: -16, rotY: 0 },
    islands: [
      { x: 0, y: 0, z: -14, width: 14, depth: 14, height: 5 },
      { x: 0, y: 0, z: 0, width: 18, depth: 18, height: 6 },
      { x: 0, y: 0, z: 16, width: 16, depth: 16, height: 6 }
    ],
    crystals: [
      { x: -7, y: 0, z: 0, scale: 3.0, isViolet: false },
      { x: 7, y: 0, z: 0, scale: 3.0, isViolet: true }
    ],
    arches: [
      { x: 0, y: 0, z: 12, rotY: 0 }
    ],
    puzzleObjects: [
      {
        type: 'portal',
        id: 'final_transcendence_portal',
        position: { x: 0, y: 0, z: 18 },
        isWorldExit: true,
        isFinalPortal: true
      }
    ]
  }
];
