# GENERIC ACTION & GESTURE SYSTEM SPECIFICATION

## 1. Action Taxonomy

Actions are parameterized kinematic behaviors evaluated across dialogue turns or narrative transitions.

```
                    ┌─────────────────────────┐
                    │      ACTION SYSTEM      │
                    └────────────┬────────────┘
                                 │
     ┌───────────────────────────┼───────────────────────────┐
     ▼                           ▼                           ▼
[LOCOMOTION]                [GESTURAL]                  [INTERACTION]
- walk(target, speed)       - point(target)             - carry(prop_id)
- run()                     - pray()                    - pickup(prop_id)
- turn(facing)              - wave()                    - place(prop_id)
- enter_left / enter_right  - wipe_face()               - cook(prop_id)
- exit_left / exit_right    - warm_hands()              - eat()
```

---

## 2. Action Parameters

All actions support the following generic parameters in the screenplay JSON:

```json
{
  "action": "walk_to_target",
  "action_actor": "char_id",
  "target": "target_actor_or_prop_id",
  "speed": "normal",
  "facing": "3/4_right"
}
```

### Supported Primitives:
1. **Locomotion**:
   - `walk_in_left` / `enter_left`: Walks from left off-screen boundary to designated stage position.
   - `walk_in_right` / `enter_right`: Walks from right off-screen boundary to stage position.
   - `exit_left` / `walk_out_left`: Walks off-screen to the left and unloads presence from stage.
   - `exit_right` / `walk_out_right`: Walks off-screen to the right.
   - `walk_to_target`: Approaches another character or stage anchor point.
   - `walk_toward_camera`: Walks forward with perspective scaling modulation.

2. **Gestures & Acting**:
   - `point`: Arm IK extends index finger toward interlocutor, jabbing forward on syllabic stress peaks.
   - `pray` / `namaste`: Both hands joined at chest level, respectful head tilt.
   - `wipe_face`: Hand extends to tear trajectory on cheek, gentle wiping cycle.
   - `cook`: Two-handed stirring motion over cooking appliance.
   - `warm_hands`: Hands held forward over heat source with gentle rubbing.
   - `shiver`: High-frequency body and arm tremor.
   - `cower`: Physical retreat away from speaker with scale compression and head aversion.
   - `idle`: Natural breathing diaphragm expansion, subtle postural sway, and responsive listening nods.
