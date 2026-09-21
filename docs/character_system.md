# GENERIC CHARACTER SYSTEM SPECIFICATION

## 1. Principles of Character Modularity

The generic engine treats characters as modular actors defined by declarative asset packages.

No character identity or behavior is hardcoded in the engine core:
- **No hardcoded names** (`if char_id == "kodalu"` is prohibited).
- **No hardcoded facial anchors** (landmarks are declared in JSON).
- **No hardcoded arm dimensions** (shoulder offsets and limb lengths are defined in configuration).
- **No hardcoded flip logic** (flipping is determined by comparing `base_orientation` with the directed facing angle).

---

## 2. Character Package Structure

A character package resides at `characters/<char_id>/`:

```
characters/<char_id>/
├── character.json          # Main manifest
├── base.png                # Full-body resting puppet (600x900 default canvas)
├── eyes_open.png           # Open eye layer
├── eyes_blink.png          # Eyelid blink layer
├── mouths/                 # Phoneme mouth sprites
│   ├── mouth_closed.png
│   ├── mouth_open_a.png
│   ├── mouth_open_e.png
│   ├── mouth_open_o.png
│   ├── mouth_teeth.png
│   └── mouth_wide.png
└── poses/                  # Optional specialized illustrated poses
    ├── cook_right.png
    └── cook_left.png
```

---

## 3. Dynamic Flip Resolution

When staging characters, the engine computes horizontal mirroring using the character's intrinsic illustration orientation:

```python
def resolve_character_flip(base_orientation: str, target_facing: str) -> bool:
    """
    Computes whether a character sprite must be horizontally flipped.
    base_orientation: '3/4_left' or '3/4_right'
    target_facing: '3/4_left', '3/4_right', 'side_left', 'side_right', 'front', 'back'
    """
    if "left" in target_facing:
        return base_orientation != "3/4_left"
    elif "right" in target_facing:
        return base_orientation != "3/4_right"
    return False
```

This guarantees that characters illustrated facing left (like Kodalu) and characters illustrated facing right (like Atha) are both handled identically and correctly without character-specific `if/else` checks.
