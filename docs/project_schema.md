# PROJECT & SCREENPLAY SCHEMA SPECIFICATION

## 1. Project Directory Layout

Every animation project conforms to the following directory structure:

```
project_root/
├── project.json              # Project-level manifest & settings
├── screenplay.json           # Story scenes, dialogue, camera, & actions
├── characters/               # Character assets & configuration
│   └── <char_id>/
│       ├── character.json    # Character landmarks, orientation, arm config
│       ├── base.png          # Illustrated character body
│       ├── eyes_open.png     # Open eyes sprite
│       ├── eyes_blink.png    # Blink overlay sprite
│       └── mouths/           # Viseme mouth sprites (6 phonemes)
├── props/                    # Interactive and scenic props
│   └── <prop_id>/
│       ├── prop.json         # Prop dimensions, attachment offsets, glow FX
│       └── <prop_name>.png
├── environments/             # Scenic backgrounds & stage configs
│   ├── <env_id>.png
│   └── environments.json     # Stage anchor coordinates & FX presets
├── audio/                    # BGM, ambient tracks, SFX
│   └── village_bgm.wav
└── output/                   # Final rendered MP4 & QA reports
```

---

## 2. `project.json` Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AnimationProjectConfig",
  "type": "object",
  "required": ["title", "resolution", "fps", "language"],
  "properties": {
    "title": { "type": "string" },
    "language": { "type": "string", "default": "te-IN" },
    "resolution": {
      "type": "object",
      "properties": {
        "width": { "type": "integer", "default": 1920 },
        "height": { "type": "integer", "default": 1080 }
      }
    },
    "fps": { "type": "integer", "default": 24 },
    "bgm": {
      "type": "object",
      "properties": {
        "track": { "type": "string" },
        "volume_db": { "type": "number", "default": -20.0 }
      }
    },
    "subtitle_settings": {
      "type": "object",
      "properties": {
        "font_family": { "type": "string", "default": "Nirmala.ttc" },
        "speaker_size": { "type": "integer", "default": 30 },
        "text_size": { "type": "integer", "default": 36 }
      }
    }
  }
}
```

---

## 3. Character Schema (`character.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CharacterDefinition",
  "type": "object",
  "required": ["id", "name", "base_orientation"],
  "properties": {
    "id": { "type": "string" },
    "name": { "type": "string" },
    "base_orientation": {
      "type": "string",
      "enum": ["3/4_left", "3/4_right", "front"],
      "description": "Natural facing orientation in base illustration artwork."
    },
    "scale": { "type": "number", "default": 1.0 },
    "voice": {
      "type": "object",
      "properties": {
        "model": { "type": "string", "default": "te-IN-ShrutiNeural" },
        "pitch": { "type": "string", "default": "+0Hz" },
        "rate": { "type": "string", "default": "+0%" }
      }
    },
    "subtitle_color": {
      "type": "array",
      "items": { "type": "integer" },
      "minItems": 3,
      "maxItems": 3
    },
    "arm_ik": {
      "type": "object",
      "properties": {
        "shoulder_r": { "type": "array", "items": { "type": "integer" }, "minItems": 2, "maxItems": 2 },
        "shoulder_l": { "type": "array", "items": { "type": "integer" }, "minItems": 2, "maxItems": 2 },
        "skin_color": { "type": "array", "items": { "type": "integer" }, "minItems": 3, "maxItems": 3 },
        "sleeve_color": { "type": "array", "items": { "type": "integer" }, "minItems": 3, "maxItems": 3 },
        "bangle_color": { "type": "array", "items": { "type": "integer" } },
        "arm_thickness": { "type": "integer", "default": 20 }
      }
    },
    "landmarks": {
      "type": "object",
      "description": "Facial landmark anchor coordinates in base sprite (600x900) pixel space",
      "properties": {
        "brow_l_inner": { "type": "array", "items": { "type": "integer" }, "minItems": 2, "maxItems": 2 },
        "brow_l_outer": { "type": "array", "items": { "type": "integer" }, "minItems": 2, "maxItems": 2 },
        "brow_r_inner": { "type": "array", "items": { "type": "integer" }, "minItems": 2, "maxItems": 2 },
        "brow_r_outer": { "type": "array", "items": { "type": "integer" }, "minItems": 2, "maxItems": 2 },
        "eye_l": { "type": "array", "items": { "type": "integer" }, "minItems": 2, "maxItems": 2 },
        "eye_r": { "type": "array", "items": { "type": "integer" }, "minItems": 2, "maxItems": 2 },
        "mouth_c": { "type": "array", "items": { "type": "integer" }, "minItems": 2, "maxItems": 2 },
        "bindi": { "type": "array", "items": { "type": "integer" } },
        "glasses_box": { "type": "array", "items": { "type": "integer" } }
      }
    }
  }
}
```

---

## 4. Screenplay Schema (`screenplay.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ScreenplayScript",
  "type": "object",
  "required": ["title", "scenes"],
  "properties": {
    "title": { "type": "string" },
    "scenes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["scene_id", "background", "dialogues"],
        "properties": {
          "scene_id": { "type": "integer" },
          "background": { "type": "string" },
          "effect": { "type": "string" },
          "actors": {
            "type": "object",
            "additionalProperties": {
              "type": "object",
              "properties": {
                "x": { "type": "integer" },
                "y": { "type": "integer" },
                "orientation": { "type": "string" },
                "scale": { "type": "number" }
              }
            }
          },
          "dialogues": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["character", "text"],
              "properties": {
                "character": { "type": "string" },
                "text": { "type": "string" },
                "emotion": { "type": "string", "default": "neutral" },
                "action": { "type": "string", "default": "speaking" },
                "action_actor": { "type": "string" },
                "target": { "type": "string" },
                "camera": { "type": "string", "default": "auto" }
              }
            }
          }
        }
      }
    }
  }
}
```
