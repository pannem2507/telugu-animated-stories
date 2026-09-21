# 2D ANIMATION ENGINE ARCHITECTURE SPECIFICATION

## 1. System Overview

The engine is a data-driven, modular 2D animation system designed to render high-definition (1080p, 24 FPS) animated films from declarative screenplay scripts and asset manifests.

The system decouples the core rendering pipeline from narrative and artistic content:
- **Core Engine (`src/`)**: Pure procedural kinematics, 2D inverse kinematics, localized facial deformation, phoneme energy analysis, camera framing, atmospheric particle simulation, and multi-plane composition.
- **Project Layer (`projects/` or `examples/`)**: Screenplays, character manifests, prop schemas, voice configurations, and environments.

---

## 2. Layered Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                            │
│           Screenplay Script (JSON / Timeline DSL Specification)        │
└───────────────────────────────────▲────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴────────────────────────────────────┐
│                       PROJECT CONFIGURATION LAYER                      │
│ - Project Metadata (Language, Resolution, FPS, BGM)                   │
│ - Character Schemas (Landmarks, Arm IK anchors, base facing)           │
│ - Prop Schemas (Assets, scales, attachment offsets, glow FX)           │
│ - Environment Schemas (Backgrounds, stage anchors, particle presets)   │
│ - Voice Profiles (TTS provider, voice model, pitch, rate)              │
└───────────────────────────────────▲────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴────────────────────────────────────┐
│                        CORE ENGINE SUBSYSTEMS                          │
│                                                                        │
│  ┌───────────────────────┐             ┌─────────────────────────┐     │
│  │   Scene Director      │────────────▶│     Camera Engine       │     │
│  │ (Blocking & Staging)  │             │ (Smooth Pan/Zoom DSL)   │     │
│  └───────────────────────┘             └─────────────────────────┘     │
│             │                                       │                  │
│             ▼                                       ▼                  │
│  ┌───────────────────────┐             ┌─────────────────────────┐     │
│  │ Character Kinematics  │             │  Environment FX Engine  │     │
│  │ (Walk/Idle/Secondary) │             │ (Snow, Rain, Steam, FX) │     │
│  └───────────────────────┘             └─────────────────────────┘     │
│             │                                       │                  │
│             ▼                                       ▼                  │
│  ┌───────────────────────┐             ┌─────────────────────────┐     │
│  │ Face & Expression IK  │             │    Prop Manager         │     │
│  │ (Masked Deformation)  │             │ (Attach / Carry / Glow) │     │
│  └───────────────────────┘             └─────────────────────────┘     │
│             │                                       │                  │
│             ▼                                       ▼                  │
│  ┌───────────────────────┐             ┌─────────────────────────┐     │
│  │ Voice & Lip Sync      │             │  Multi-Plane Compositor │     │
│  │ (Phoneme Visemes)     │────────────▶│  & Video Writer         │     │
│  └───────────────────────┘             └─────────────────────────┘     │
└───────────────────────────────────▲────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴────────────────────────────────────┐
│                        OUTPUT & QA VERIFICATION                        │
│               H.264 / AAC MP4 + Automated QA Report                    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Subsystem Contracts

### 3.1 Character System
- Each character is defined by a directory with:
  - `character.json`: Canonical metadata, base orientation (`"3/4_left"` or `"3/4_right"`), scale, anchor points, arm IK shoulder offsets, skin/sleeve colors, and facial landmarks.
  - `base.png`: Base illustrated puppet.
  - `eyes_open.png` / `eyes_blink.png`: Eyelid state sprites.
  - Viseme mouth sprites (`mouth_closed.png`, `mouth_open_a.png`, `mouth_open_e.png`, `mouth_open_o.png`, `mouth_teeth.png`, `mouth_wide.png`).
- The engine uses the character's intrinsic `base_orientation` to compute left/right flipping dynamically.

### 3.2 Emotion & Face Engine
- Expressions operate via localized radial deformation bounded by feathered safety masks that lock hair, ears, bindi, and glasses frames.
- Reusable emotion primitives:
  - `neutral`: Relaxed posture, subtle idle breathing.
  - `angry`: Furrowed inner brows, raised outer brows, aggressive forward lean, pointing gesture.
  - `sad` / `cry`: Inner brow grief lift, heavy eyelids, downturned mouth seam, organic curved tear trajectories.
  - `fear` / `cower`: Retreated posture, arched brows, shiver tremor.
  - `happy` / `joy`: Upright posture, energetic bounce, softened smile.
  - `surprise`: Widened eyes, elevated brow arches.
  - `relief` / `reverence`: Softened facial lines, calm posture.

### 3.3 Prop System
- Reusable props are declared in `props.json` or `project.json`.
- Attributes:
  - `id`: Unique identifier (e.g. `"magic_stove"`, `"scroll"`, `"lantern"`).
  - `asset`: File path relative to project assets.
  - `scale`: Render scale relative to stage coordinates.
  - `attachment_points`: Offsets for `"waist_carry"`, `"hand_hold"`, `"head_wear"`.
  - `glow`: Optional halo parameters (`color`, `radius`, `pulsing`).
  - `shadow`: Ground shadow ellipse dimensions.

### 3.4 Camera System
- Dynamic camera engine supports smooth cubic interpolation across standard cinematographic framing:
  - `wide` / `establishing_wide`: Full stage (1.0x).
  - `medium_two_shot`: Framed on two conversation participants (1.15x).
  - `medium_character`: Framed on active speaker/actor (1.25x).
  - `closeup` / `speaker_closeup`: Tight framing on character face and chest (1.85x).
  - `reaction_closeup`: Tight reaction shot on conversational listener (1.85x).
  - `insert_object`: Focus on prop or held item (1.38x).
  - `follow_walk`: Smooth horizontal tracking shot following a walking character.

### 3.5 Audio & Multilingual Lip-Sync
- Speech synthesis is decoupled through pluggable providers (default: `edge-tts`).
- Viseme cues are extracted directly from audio waveforms (RMS energy, zero-crossing rate, spectral friction) into 6 universal viseme states:
  `mouth_closed`, `mouth_open_a`, `mouth_open_e`, `mouth_open_o`, `mouth_teeth`, `mouth_wide`.
- Subtitles are rendered with configurable font, size, and character accent colors.
