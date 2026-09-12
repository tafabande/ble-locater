export interface TourStep {
  id: string
  targetId: string
  tabKey?: string
  questNumber: number
  totalQuests: number
  questTitle: string
  optionName: string
  icon: string
  xpReward: number
  badge: {
    type: 'must_have' | 'recommended' | 'optional' | 'advanced'
    label: string
  }
  whatItDoes: string
  shouldYouUseIt: {
    verdict: string
    useIf: string
    skipIf: string
  }
  proTip: string
}

export const CASUAL_SETUP_TOUR: TourStep[] = [
  {
    id: 'casual_space',
    targetId: 'tour-casual-space',
    tabKey: 'casual',
    questNumber: 1,
    totalQuests: 5,
    questTitle: 'Quest 1: Choose Your Arena',
    optionName: 'Space Sizing & Visual Room Presets',
    icon: '🏠',
    xpReward: 100,
    badge: {
      type: 'must_have',
      label: 'MUST-HAVE',
    },
    whatItDoes:
      'Sets your building dimensions using simple presets (Single Studio, 2-Room Office Suite, 4-Room Smart Complex, Open Warehouse) or custom meters. It establishes the physical coordinate boundary and scale for all positioning.',
    shouldYouUseIt: {
      verdict: '✅ Essential First Step: Required for all tracking.',
      useIf: 'You are setting up any room, office, warehouse, or retail floor.',
      skipIf: 'Never — positioning algorithms must know how wide and long your room is.',
    },
    proTip:
      "Start with 'Single Studio / Office' (5m × 5m) or '2-Room Office Suite' (10m × 10m). You can always tweak custom meters anytime!",
  },
  {
    id: 'casual_anchors',
    targetId: 'tour-casual-anchors',
    tabKey: 'casual',
    questNumber: 2,
    totalQuests: 5,
    questTitle: 'Quest 2: Deploy The Beacons',
    optionName: 'Tracking Boxes Placement (Anchor Layout)',
    icon: '📡',
    xpReward: 100,
    badge: {
      type: 'recommended',
      label: 'RECOMMENDED',
    },
    whatItDoes:
      'Positions your BLE receiver anchor nodes automatically around your space. Offers 4-Corner coverage (best 2D triangulation), 3-Node perimeter (economy), or Single Center Node (proximity detection).',
    shouldYouUseIt: {
      verdict: '⭐ 4-Corner Coverage is strongly recommended for 2D positioning.',
      useIf: 'You have 3 or 4 receiver boxes and want smooth (X, Y) coordinate tracking across the whole floor.',
      skipIf: 'You only possess a single receiver box — in that case, choose Single Center Node for presence detection.',
    },
    proTip:
      'Mount your hardware boxes high up on walls (at least 2m off the floor) with clear line-of-sight to prevent human bodies from attenuating signals.',
  },
  {
    id: 'casual_env',
    targetId: 'tour-casual-env',
    tabKey: 'casual',
    questNumber: 3,
    totalQuests: 5,
    questTitle: 'Quest 3: Set The Terrain',
    optionName: 'Space Environment Profile',
    icon: '🧱',
    xpReward: 100,
    badge: {
      type: 'must_have',
      label: 'MUST-HAVE',
    },
    whatItDoes:
      'Calibrates wireless radio wave propagation automatically without any math or decibels. Tells the system whether your space is Open (few obstacles), Standard Office (drywall & cubicles), or Dense Space (concrete & metal racks).',
    shouldYouUseIt: {
      verdict: '✅ Must match your real physical room environment.',
      useIf: 'Your facility has walls, doors, or furniture that absorb Bluetooth radio signals.',
      skipIf: 'Never — leaving it on Open Space in a dense warehouse will cause severe distance underestimation.',
    },
    proTip:
      "For 90% of indoor spaces, 'Standard Office' produces the sweet-spot balance between range and obstacle compensation.",
  },
  {
    id: 'casual_preview',
    targetId: 'tour-casual-preview',
    tabKey: 'casual',
    questNumber: 4,
    totalQuests: 5,
    questTitle: 'Quest 4: Test Flight Your Badge',
    optionName: 'Interactive Room Preview & Test Badge',
    icon: '🏷️',
    xpReward: 100,
    badge: {
      type: 'recommended',
      label: 'RECOMMENDED',
    },
    whatItDoes:
      'A real-time visual sandbox right in your browser! Drag the purple test badge anywhere on the map to see real-time distance readouts to all anchors and verify coverage rings.',
    shouldYouUseIt: {
      verdict: '⭐ Great visual sanity check before installing physical hardware.',
      useIf: 'You want to check for dead zones, verify room corners, or confirm distance calculations.',
      skipIf: 'You have already finalized your node placements and need to deploy immediately.',
    },
    proTip:
      'Drag the badge into the farthest corners; if distance exceeds 15 meters without an anchor nearby, add an extra node.',
  },
  {
    id: 'casual_activate',
    targetId: 'tour-casual-activate',
    tabKey: 'casual',
    questNumber: 5,
    totalQuests: 5,
    questTitle: 'Quest 5: The Grand Activation',
    optionName: 'Confirm & Activate Space',
    icon: '🚀',
    xpReward: 100,
    badge: {
      type: 'must_have',
      label: 'FINAL ACTIVATION',
    },
    whatItDoes:
      'Locks in your configuration, stores the room blueprint into local storage, and syncs the anchor coordinates directly with the live RTLS engine.',
    shouldYouUseIt: {
      verdict: '🏆 Final Boss: Required to save and begin live tracking!',
      useIf: 'You are pleased with your room dimensions and anchor layout.',
      skipIf: 'You were only experimenting and want to keep your previous setup.',
    },
    proTip:
      "After clicking 'Confirm & Activate Space', click the 'Open Live Monitor' button to watch real-time badges move on your map!",
  },
]

export const ENGINEER_STUDIO_TOUR: TourStep[] = [
  {
    id: 'eng_floor',
    targetId: 'tour-eng-tab-floor',
    tabKey: 'floor',
    questNumber: 1,
    totalQuests: 5,
    questTitle: 'Quest 1: Blueprint Architecture',
    optionName: 'CAD Floor Plan Designer',
    icon: '📐',
    xpReward: 100,
    badge: {
      type: 'advanced',
      label: 'CAD STUDIO',
    },
    whatItDoes:
      'Full precision 2D CAD blueprint editor. Allows drawing custom polygon walls, assigning per-wall RF attenuation (dB), placing doors, and positioning anchor nodes to millimeter coordinates.',
    shouldYouUseIt: {
      verdict: '🛠️ Essential for complex architectural floor plans.',
      useIf: 'You have official building CAD drawings or complex non-rectangular partition layouts.',
      skipIf: 'Casual Setup presets already match your rectangular office or room.',
    },
    proTip:
      'Turn on Grid Snapping (G) and zoom into corners to ensure wall endpoints align cleanly without signal leakage gaps.',
  },
  {
    id: 'eng_calibration',
    targetId: 'tour-eng-tab-calibration',
    tabKey: 'calibration',
    questNumber: 2,
    totalQuests: 5,
    questTitle: 'Quest 2: Tame The Radio Physics',
    optionName: 'Log-Distance ML Calibration',
    icon: '📊',
    xpReward: 100,
    badge: {
      type: 'recommended',
      label: 'ACADEMIC / R&D',
    },
    whatItDoes:
      'Performs least-squares linear regression on empirical RSSI measurements across measured distances to calculate the true Path Loss Exponent (n) and 1m Reference Power (A₀).',
    shouldYouUseIt: {
      verdict: '⭐ Best for scientific validation and sub-meter tuning.',
      useIf: 'Conducting empirical research, calibrating custom antenna designs, or writing thesis evaluations.',
      skipIf: 'You are using standard office environments where preset exponents (n=2.0 to 3.0) suffice.',
    },
    proTip:
      'Take at least 15 empirical measurements per anchor at 1m, 2m, 4m, and 8m distances to achieve an RMSE fit under 1.5 dB.',
  },
  {
    id: 'eng_analytics',
    targetId: 'tour-eng-tab-analytics',
    tabKey: 'analytics',
    questNumber: 3,
    totalQuests: 5,
    questTitle: 'Quest 3: Telemetry & Diagnostics',
    optionName: 'Spatial Analytics & Heatmaps',
    icon: '📈',
    xpReward: 100,
    badge: {
      type: 'optional',
      label: 'SYSTEM HEALTH',
    },
    whatItDoes:
      'Visualizes packet reception rates, anchor UART latency histograms, tag dwell time density heatmaps, and trilateration error distributions.',
    shouldYouUseIt: {
      verdict: '⚠️ Diagnostic and performance optimization suite.',
      useIf: 'Troubleshooting packet drops, finding wireless dead zones, or auditing traffic congestion.',
      skipIf: 'System is running smoothly and you only need standard position tracking.',
    },
    proTip:
      'If anchor packet latency spikes above 200ms, inspect your USB serial hub or check for 2.4 GHz Wi-Fi interference on channel 37/38/39.',
  },
  {
    id: 'eng_history',
    targetId: 'tour-eng-tab-history',
    tabKey: 'history',
    questNumber: 4,
    totalQuests: 5,
    questTitle: 'Quest 4: Time Travel Forensics',
    optionName: 'Security History & Geofence Replay',
    icon: '🛡️',
    xpReward: 100,
    badge: {
      type: 'optional',
      label: 'SECURITY AUDIT',
    },
    whatItDoes:
      'Maintains an indexed timeline of historical tag movements, route breadcrumbs, and geofence perimeter breach alarms with an interactive replay scrubber.',
    shouldYouUseIt: {
      verdict: '⚠️ Essential for post-incident security forensics.',
      useIf: 'Auditing unauthorized asset movement, tracing worker workflow paths, or reviewing alert logs.',
      skipIf: 'You only care about live current positions right this second.',
    },
    proTip:
      'Use the replay scrubber slider to rewind to the exact second an asset crossed an alert boundary.',
  },
  {
    id: 'eng_config',
    targetId: 'tour-eng-tab-config',
    tabKey: 'config',
    questNumber: 5,
    totalQuests: 5,
    questTitle: 'Quest 5: Daemon Core Control',
    optionName: 'Hardware Mesh & Daemon Configuration',
    icon: '⚙️',
    xpReward: 100,
    badge: {
      type: 'advanced',
      label: 'HARDWARE & DAEMON',
    },
    whatItDoes:
      'Manages backend REST/WebSocket endpoints, polling interval milliseconds, anchor USB COM serial port bindings, simulation engine toggles, and Kalman filter smoothing weights.',
    shouldYouUseIt: {
      verdict: '🛠️ Hardware administrator setup.',
      useIf: 'Connecting physical ESP32 dongles, changing network IP hostnames, or toggling simulation daemons.',
      skipIf: 'You are using default local port 3000 and auto-detected serial ports.',
    },
    proTip:
      'For stable USB UART performance without buffer overflows, set the polling interval to 2000ms–2500ms.',
  },
]
