# GENERIC INTERACTION SYSTEM SPECIFICATION

## 1. Interaction Domains

The interaction system coordinates spatial and relational dynamics between scene entities:

1. **Actor → Actor**:
   - `talk_to(target_actor_id)`: Orient head and torso toward target actor.
   - `listen_to(speaker_actor_id)`: Adopt listening posture, nodding rhythmically, facing speaker.
   - `approach(target_actor_id)`: Walk toward target actor with safety spacing clamp (maintaining ~300px personal space).
   - `retreat_from(target_actor_id)`: Walk or step backward from aggressive or scolding actor.

2. **Actor → Prop**:
   - `pickup(prop_id)`: Lower body/arms, attach prop to character hand/waist anchor.
   - `carry(prop_id)`: Prop position locked to character position with vertical walking bob compensation.
   - `place(prop_id, stage_pos)`: Detach prop from character and rest on stage surface with contact ground shadow.
   - `use(prop_id)`: Trigger specialized prop interaction (e.g. cooking over stove, drinking from cup).

3. **Actor → Environment**:
   - `knock_door`: Rhythmic door knock animation.
   - `open_door`: Reaching gesture, door reveals interior.
   - `enter_room` / `leave_room`: Seamless stage transitions.
