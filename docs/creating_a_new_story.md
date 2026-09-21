# CREATING A NEW ANIMATED PRODUCTION WITH THE GENERIC ENGINE

This step-by-step guide explains how to create, stage, and render a completely new 2D animated production using the generic engine **without modifying a single line of core Python code in `src/`**.

---

## 1. Directory Setup

Create a new directory under `projects/` (e.g. `projects/my_adventure/`):

```bash
projects/my_adventure/
├── project.json
├── screenplay.json
├── characters/
│   ├── hero/
│   └── mentor/
├── props/
│   └── artifact/
├── environments/
│   └── ancient_temple.png
└── audio/
    └── temple_bgm.wav
```

---

## 2. Define `project.json`

Specify project metadata, resolution, frame rate, language, and global BGM:

```json
{
  "title": "The Quest for the Ancient Stone",
  "language": "en-US",
  "resolution": { "width": 1920, "height": 1080 },
  "fps": 24,
  "bgm": {
    "track": "audio/temple_bgm.wav",
    "volume_db": -22.0
  },
  "subtitle_settings": {
    "font_family": "Arial.ttf",
    "speaker_size": 28,
    "text_size": 34
  }
}
```

---

## 3. Register Characters & Assets

For each character (e.g. `hero`):
1. Place art sprites inside `projects/my_adventure/characters/hero/`:
   - `base.png` (600x900 full-body illustrated puppet)
   - `eyes_open.png` / `eyes_blink.png`
   - `mouths/mouth_closed.png`, `mouth_open_a.png`, `mouth_open_e.png`, `mouth_open_o.png`, `mouth_teeth.png`, `mouth_wide.png`
2. Create `character.json`:
```json
{
  "id": "hero",
  "name": "Kiran",
  "base_orientation": "3/4_right",
  "scale": 1.0,
  "voice": {
    "model": "en-US-GuyNeural",
    "pitch": "+0Hz",
    "rate": "+0%"
  },
  "subtitle_color": [100, 200, 255],
  "arm_ik": {
    "shoulder_r": [380, 290],
    "shoulder_l": [420, 290],
    "skin_color": [215, 160, 120],
    "sleeve_color": [60, 100, 180],
    "arm_thickness": 22
  },
  "landmarks": {
    "eye_l": [260, 140],
    "eye_r": [320, 140],
    "brow_l_inner": [275, 120],
    "brow_r_inner": [305, 120],
    "mouth_c": [290, 180]
  }
}
```

---

## 4. Register Props

Place prop artwork in `props/<prop_id>/` and configure `prop.json`:

```json
{
  "id": "crystal_orb",
  "asset": "props/crystal_orb/orb.png",
  "scale": 0.8,
  "glow": {
    "color": [80, 200, 255],
    "radius": 140,
    "pulse": true
  },
  "attachment_points": {
    "waist_carry": { "offset_x": 160, "offset_y": 220 },
    "hand_hold": { "offset_x": 140, "offset_y": 120 }
  }
}
```

---

## 5. Write the Screenplay (`screenplay.json`)

Construct scenes and dialogue turns using the generic action and camera DSL:

```json
{
  "title": "The Quest for the Ancient Stone",
  "scenes": [
    {
      "scene_id": 1,
      "background": "ancient_temple",
      "effect": "dust",
      "actors": {
        "mentor": { "x": 400, "y": 200, "orientation": "3/4_right" },
        "hero": { "x": 1000, "y": 200, "orientation": "3/4_left" }
      },
      "dialogues": [
        {
          "character": "mentor",
          "text": "The prophecy spoke of your arrival, young seeker.",
          "emotion": "reverence",
          "action": "speaking",
          "camera": "medium_two_shot"
        },
        {
          "character": "hero",
          "text": "I came to find the crystal orb before nightfall!",
          "emotion": "happy",
          "action": "point",
          "camera": "speaker_closeup"
        },
        {
          "character": "hero",
          "text": "",
          "action": "walk_to_target",
          "target": "mentor",
          "camera": "follow_walk"
        }
      ]
    }
  ]
}
```

---

## 6. Render the Production

Execute the generic production command:

```bash
python -m src.cli render --project projects/my_adventure/ --output output/my_adventure.mp4
```

The engine reads `project.json`, auto-discovers all characters, binds voices, compiles procedural movements, resolves camera angles, generates audio/visemes, and produces a complete 1080p MP4.
