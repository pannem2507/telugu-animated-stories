# GENERIC PROP SYSTEM SPECIFICATION

## 1. Modular Prop Concepts

A prop is an independent physical or mystical item that can exist on stage, rest on a surface, be picked up, carried, handed over, or placed down.

The engine does not have built-in knowledge of specific props (such as a magic stove or lantern). All prop behavior is data-driven.

---

## 2. Prop Manifest Schema (`prop.json`)

```json
{
  "id": "magic_stove",
  "name": "Clay Magic Chulha",
  "asset": "magic_stove.png",
  "scale": 0.95,
  "depth_layer": "foreground",
  "attachment_points": {
    "waist_carry": {
      "offset_x_right": 185,
      "offset_x_left": 100,
      "offset_y": 245
    },
    "table_rest": {
      "offset_x": 0,
      "offset_y": 0
    }
  },
  "effects": {
    "glow": {
      "enabled": true,
      "color": [255, 215, 60],
      "max_radius": 180,
      "rings": [
        { "radius_multiplier": 1.0, "alpha": 40 },
        { "radius_multiplier": 0.7, "alpha": 80 },
        { "radius_multiplier": 0.4, "alpha": 140 }
      ]
    },
    "shadow": {
      "enabled": true,
      "width": 140,
      "height": 24,
      "offset_y": 140
    }
  }
}
```

---

## 3. Runtime Lifecycle States

```
                ┌─────────────────────────┐
                │      UNMANIFESTED       │ (alpha = 0.0, visible = false)
                └────────────┬────────────┘
                             │ reveal_prop(progress)
                             ▼
                ┌─────────────────────────┐
                │         ON STAGE        │ (resting on floor/table with shadow)
                └────────────┬────────────┘
                             │ attach_to_character(char_id, "waist_carry")
                             ▼
                ┌─────────────────────────┐
                │       HELD / CARRIED    │ (tracks character x, y, walk bobbing)
                └────────────┬────────────┘
                             │ detach_prop(stage_pos)
                             ▼
                ┌─────────────────────────┐
                │         ON STAGE        │
                └─────────────────────────┘
```
