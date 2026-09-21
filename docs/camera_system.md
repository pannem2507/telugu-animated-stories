# GENERIC CAMERA SYSTEM SPECIFICATION

## 1. Cinematic Framing Model

The Camera Engine controls the viewport and field of view over the 1920x1080 staging canvas.

```
+-------------------------------------------------------------+
| FULL 1920x1080 STAGE CANVAS                                 |
|   +-----------------------------------------------------+   |
|   | WIDE TWO-SHOT (1.08x - 1.15x)                       |   |
|   |    +-------------------------------------------+    |   |
|   |    | MEDIUM CHARACTER (1.25x)                  |    |   |
|   |    |    +---------------------------------+    |    |   |
|   |    |    | SPEAKER CLOSEUP (1.85x)         |    |    |   |
|   |    |    +---------------------------------+    |    |   |
|   |    +-------------------------------------------+    |   |
|   +-----------------------------------------------------+   |
+-------------------------------------------------------------+
```

---

## 2. Standard Shot Types

1. **`wide` / `establishing_wide`**: Full stage viewport (zoom = 1.0x).
2. **`medium_two_shot`**: Frames two conversational actors (zoom = 1.15x).
3. **`medium_character`**: Frames the active speaker from waist up (zoom = 1.25x).
4. **`speaker_closeup`**: Tight framing on the speaker's face and upper chest (zoom = 1.85x).
5. **`reaction_closeup`**: Tight framing on the listening character's reaction (zoom = 1.85x).
6. **`insert_object`**: Focuses on an interactive prop or carried item (zoom = 1.38x).
7. **`follow_walk`**: Tracks a moving character across the screen (zoom = 1.18x).

---

## 3. Smooth Viewport Interpolation

Transitions between shots use exponential smoothing:
```python
self.current_zoom += (self.target_zoom - self.current_zoom) * smoothing
self.current_cx += (self.target_cx - self.current_cx) * smoothing
self.current_cy += (self.target_cy - self.current_cy) * smoothing
```
A default smoothing factor of `0.12` creates natural camera pans and gentle push-in zooms without jarring instantaneous cuts.
