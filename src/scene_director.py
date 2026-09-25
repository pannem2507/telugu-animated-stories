"""
Scene Director for Telugu Animated Stories
Handles character staging, blocking, natural 3/4 orientations,
presence lifecycle (enter/exit), conversational dynamics, and camera shot selection.
"""

from .conversation_director import ConversationDirector
from .behavior_registry import BehaviorRegistry

class SceneDirector:
    """
    Directs scene blocking and character states deterministically.
    Ensures natural 3/4 staging, manages entrances, exits, walk targets,
    speaker focus, and listener reactions.
    """
    def __init__(self, behavior_defs: dict = None):
        # Default conversational staging positions (natural ~580px spacing)
        self.two_shot_left = {"x": 380, "y": 180, "orientation": "3/4_right"}
        self.two_shot_right = {"x": 960, "y": 180, "orientation": "3/4_left"}
        self.center_stage = {"x": 660, "y": 180, "orientation": "3/4_right"}
        self.stove_stage = {"x": 280, "y": 200, "orientation": "3/4_right"}
        self.tree_platform = {"x": 320, "y": 180, "orientation": "3/4_right"}
        self.bed_stage = {"x": 360, "y": 190, "orientation": "3/4_right"}
        self.desk_stage = {"x": 1050, "y": 190, "orientation": "3/4_left"}
        self.conv_director = ConversationDirector()
        self.behavior_registry = BehaviorRegistry(behavior_defs)

    def register_behavior(self, name: str, data: dict):
        """Dynamic behavior registration facade."""
        return self.behavior_registry.register(name, data)

    def get_behavior(self, name: str):
        """Lookup behavior descriptor from registry."""
        return self.behavior_registry.get(name)
        
    def setup_scene(self, scene: dict) -> dict:
        dialogues = scene.get("dialogues", [])
        
        # Identify non-narrator characters and their very first action in the scene
        characters_in_scene = []
        first_actions = {}
        for d in dialogues:
            char = d["character"].lower()
            if char != "narrator":
                if char not in characters_in_scene:
                    characters_in_scene.append(char)
                    first_actions[char] = d.get("action", "speaking").lower()
                
        bg_name = scene.get("background", "").lower()
        is_kitchen = "kitchen" in bg_name
        is_lake = "lake" in bg_name
        is_bedroom = "bedroom" in bg_name
        
        actors = {}
        if "actors" in scene and isinstance(scene["actors"], dict) and len(scene["actors"]) > 0:
            for char_id, info in scene["actors"].items():
                c_clean = char_id.lower()
                act = first_actions.get(c_clean, "speaking")
                is_init_present = not self.behavior_registry.is_entry_action(act)
                actors[c_clean] = {
                    "x": info.get("x", 400),
                    "y": info.get("y", 280),
                    "orientation": info.get("orientation", "three_quarter_right" if info.get("x", 400) < 700 else "three_quarter_left"),
                    "scale": info.get("scale", 0.95),
                    "is_present": info.get("is_present", is_init_present),
                    "action": act
                }
            return actors

        if len(characters_in_scene) == 1:
            c = characters_in_scene[0]
            action = first_actions[c]
            is_init_present = not self.behavior_registry.is_entry_action(action)
            
            if is_kitchen:
                stage_pos = self.stove_stage
            elif is_lake:
                stage_pos = self.tree_platform
            elif is_bedroom:
                stage_pos = self.desk_stage
            else:
                stage_pos = self.center_stage
                
            actors[c] = {
                "x": stage_pos["x"],
                "y": stage_pos["y"],
                "orientation": stage_pos["orientation"],
                "scale": 1.0,
                "is_present": is_init_present,
                "action": action
            }
        elif len(characters_in_scene) >= 2:
            c1 = characters_in_scene[0]
            c2 = characters_in_scene[1]
            
            # Left vs right role staging
            if is_kitchen:
                left_char = "kodalu" if "kodalu" in [c1, c2] or "anamika" in [c1, c2] else c1
                right_char = c2 if left_char == c1 else c1
                left_pos = self.stove_stage
                right_pos = self.two_shot_right
            elif is_lake:
                # Maharshi is seated under the tree on the left
                left_char = "maharshi" if "maharshi" in [c1, c2] else c1
                right_char = c2 if left_char == c1 else c1
                left_pos = self.tree_platform
                right_pos = self.two_shot_right
            elif is_bedroom:
                left_char = c1
                right_char = c2
                left_pos = self.bed_stage
                right_pos = self.desk_stage
            else:
                act1 = first_actions[c1]
                act2 = first_actions[c2]
                side1 = self.behavior_registry.get_entry_side(act1)
                side2 = self.behavior_registry.get_entry_side(act2)
                
                if side1 == "left":
                    left_char = c1
                    right_char = c2
                elif side2 == "left":
                    left_char = c2
                    right_char = c1
                elif side1 == "right":
                    right_char = c1
                    left_char = c2
                elif side2 == "right":
                    right_char = c2
                    left_char = c1
                else:
                    left_char = c1
                    right_char = c2
                left_pos = self.two_shot_left
                right_pos = self.two_shot_right
            
            is_c1_present = not self.behavior_registry.is_entry_action(first_actions[left_char])
            is_c2_present = not self.behavior_registry.is_entry_action(first_actions[right_char])
            
            actors[left_char] = {
                "x": left_pos["x"],
                "y": left_pos["y"],
                "orientation": left_pos["orientation"],
                "scale": 1.0,
                "is_present": is_c1_present,
                "action": first_actions[left_char]
            }
            actors[right_char] = {
                "x": right_pos["x"],
                "y": right_pos["y"],
                "orientation": right_pos["orientation"],
                "scale": 1.0,
                "is_present": is_c2_present,
                "action": first_actions[right_char]
            }
            if len(characters_in_scene) >= 3:
                for c_extra in characters_in_scene[2:]:
                    is_extra_present = not self.behavior_registry.is_entry_action(first_actions[c_extra])
                    actors[c_extra] = {
                        "x": 660,
                        "y": 180,
                        "orientation": "3/4_right",
                        "scale": 0.95,
                        "is_present": is_extra_present,
                        "action": first_actions[c_extra]
                    }
                
        return actors

    def plan_turn(self, dialogue_turn: dict, actors: dict, fps: int, turn_frames: int) -> dict:
        speaker = dialogue_turn["character"].lower()
        raw_action = dialogue_turn.get("action", "speaking").lower()
        emotion = dialogue_turn.get("emotion", "neutral")
        camera_tag = dialogue_turn.get("camera", "auto").lower()
        target_tag = dialogue_turn.get("target", "")
        
        # Determine physical actor for movement/actions
        phys_actor = dialogue_turn.get("action_actor")
        if not phys_actor or phys_actor not in actors:
            if speaker in actors:
                phys_actor = speaker
            else:
                text_lower = dialogue_turn.get("text", "")
                if "అనామిక" in text_lower or "కోడల" in text_lower:
                    phys_actor = "kodalu" if "kodalu" in actors else None
                elif "శారద" in text_lower or "అత్త" in text_lower:
                    phys_actor = "atha" if "atha" in actors else None
                elif "రమేష్" in text_lower or "బాబు" in text_lower:
                    phys_actor = "gent" if "gent" in actors else None
                elif "మహర్షి" in text_lower:
                    phys_actor = "maharshi" if "maharshi" in actors else None
                elif "సరోజ" in text_lower:
                    phys_actor = "saroja" if "saroja" in actors else None
                elif "పద్మ" in text_lower:
                    phys_actor = "padma" if "padma" in actors else None
                elif target_tag in actors:
                    phys_actor = target_tag
                
                # Generic fallback: check if any actor name appears directly in dialogue text
                if not phys_actor:
                    for act_k in actors:
                        if act_k in text_lower.lower():
                            phys_actor = act_k
                            break

        # Check text for transit cues if raw action is narrate
        t_text = dialogue_turn.get("text", "")
        if raw_action in ["narrate", "narrator"] and phys_actor and phys_actor in actors:
            if any(w in t_text for w in ["బయలుదేరింది", "నడిచింది", "వెళ్ళింది"]):
                # If near right side, exit left; if near left side, exit right
                cur_act_x = actors[phys_actor].get("x", 500)
                raw_action = "exit_left" if cur_act_x > 600 else "exit_right"

        # Consult conversation director for emotional beats & listeners
        conv_plan = self.conv_director.direct_dialogue(
            speaker=speaker,
            text=dialogue_turn.get("text", ""),
            emotion=emotion,
            action_override=raw_action,
            camera_override=camera_tag,
            actors=actors
        )

        # Plan movement via decoupled BehaviorRegistry
        m_plan = self.behavior_registry.plan_movement(
            action_name=raw_action,
            phys_actor=phys_actor,
            actors=actors,
            target_tag=target_tag,
            fps=fps,
            turn_frames=turn_frames
        )
        is_walking = m_plan["is_walking"]
        walk_actor = m_plan["walk_actor"]
        walk_type = m_plan["walk_type"]
        start_x = m_plan["start_x"]
        target_x = m_plan["target_x"]
        walk_frames = m_plan["walk_frames"]
        walk_orientation = m_plan["walk_orientation"]

        # Determine camera shot
        if camera_tag != "auto":
            chosen_shot = camera_tag
        elif is_walking:
            chosen_shot = "follow_walk"
        else:
            chosen_shot = conv_plan["camera_shot"]
            
        return {
            "speaker": speaker,
            "action": conv_plan["speaker_action"],
            "is_walking": is_walking,
            "walk_actor": walk_actor,
            "walk_type": walk_type,
            "start_x": start_x,
            "target_x": target_x,
            "walk_frames": walk_frames,
            "walk_orientation": walk_orientation,
            "camera_shot": chosen_shot,
            "listener_states": conv_plan["listener_states"]
        }
