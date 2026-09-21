"""
Scene Director for Telugu Animated Stories
Handles character staging, blocking, natural 3/4 orientations,
presence lifecycle (enter/exit), conversational dynamics, and camera shot selection.
"""

from .conversation_director import ConversationDirector

class SceneDirector:
    """
    Directs scene blocking and character states deterministically.
    Ensures natural 3/4 staging, manages entrances, exits, walk targets,
    speaker focus, and listener reactions.
    """
    def __init__(self):
        # Default conversational staging positions (natural ~580px spacing)
        self.two_shot_left = {"x": 380, "y": 180, "orientation": "3/4_right"}
        self.two_shot_right = {"x": 960, "y": 180, "orientation": "3/4_left"}
        self.center_stage = {"x": 660, "y": 180, "orientation": "3/4_right"}
        self.stove_stage = {"x": 280, "y": 200, "orientation": "3/4_right"}
        self.tree_platform = {"x": 320, "y": 180, "orientation": "3/4_right"}
        self.bed_stage = {"x": 360, "y": 190, "orientation": "3/4_right"}
        self.desk_stage = {"x": 1050, "y": 190, "orientation": "3/4_left"}
        self.conv_director = ConversationDirector()
        
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
                is_init_present = act not in ["walk_in", "walk_in_left", "walk_in_right", "enter", "enter_left", "enter_right"]
                actors[c_clean] = {
                    "x": info.get("x", 400),
                    "y": info.get("y", 280),
                    "orientation": info.get("orientation", "three_quarter_right" if info.get("x", 400) < 700 else "three_quarter_left"),
                    "scale": info.get("scale", 0.95),
                    "is_present": is_init_present,
                    "action": act
                }
            return actors

        if len(characters_in_scene) == 1:
            c = characters_in_scene[0]
            action = first_actions[c]
            is_init_present = action not in ["walk_in", "walk_in_left", "walk_in_right", "enter", "enter_left", "enter_right"]
            
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
                if act1 in ["walk_in_left", "enter_left"]:
                    left_char = c1
                    right_char = c2
                elif act2 in ["walk_in_left", "enter_left"]:
                    left_char = c2
                    right_char = c1
                elif act1 in ["walk_in_right", "enter_right", "walk_in", "enter"]:
                    right_char = c1
                    left_char = c2
                elif act2 in ["walk_in_right", "enter_right", "walk_in", "enter"]:
                    right_char = c2
                    left_char = c1
                else:
                    left_char = c1
                    right_char = c2
                left_pos = self.two_shot_left
                right_pos = self.two_shot_right
            
            is_c1_present = first_actions[left_char] not in ["walk_in", "walk_in_left", "walk_in_right", "enter", "enter_left", "enter_right"]
            is_c2_present = first_actions[right_char] not in ["walk_in", "walk_in_left", "walk_in_right", "enter", "enter_left", "enter_right"]
            
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
                    is_extra_present = first_actions[c_extra] not in ["walk_in", "walk_in_left", "walk_in_right", "enter", "enter_left", "enter_right"]
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
        
        # Consult conversation director for emotional beats & listeners
        conv_plan = self.conv_director.direct_dialogue(
            speaker=speaker,
            text=dialogue_turn.get("text", ""),
            emotion=emotion,
            action_override=raw_action,
            camera_override=camera_tag,
            actors=actors
        )
        
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

        # Detect movement type
        is_walking = False
        start_x, target_x = 0, 0
        walk_actor = None
        walk_frames = 0
        walk_orientation = "3/4_right"
        walk_type = "walk_right"
        
        # Check text for transit cues if raw action is narrate
        t_text = dialogue_turn.get("text", "")
        if raw_action in ["narrate", "narrator"] and phys_actor and phys_actor in actors:
            if any(w in t_text for w in ["బయలుదేరింది", "నడిచింది", "వెళ్ళింది"]):
                # If near right side, exit left; if near left side, exit right
                cur_act_x = actors[phys_actor].get("x", 500)
                if cur_act_x > 600:
                    raw_action = "exit_left"
                else:
                    raw_action = "exit_right"
        
        if raw_action in ["walk_in_left", "enter_left", "walk_in"] and phys_actor and phys_actor in actors:
            is_walking = True
            walk_actor = phys_actor
            actors[phys_actor]["is_present"] = True
            start_x = -650
            target_x = actors[phys_actor]["x"]
            walk_frames = min(turn_frames, int(2.2 * fps))
            walk_orientation = "3/4_right"
            actors[phys_actor]["orientation"] = "3/4_right"
            walk_type = "walk_right"
            
        elif raw_action in ["walk_in_right", "enter_right"] and phys_actor and phys_actor in actors:
            is_walking = True
            walk_actor = phys_actor
            actors[phys_actor]["is_present"] = True
            start_x = 2100
            target_x = actors[phys_actor]["x"]
            walk_frames = min(turn_frames, int(2.2 * fps))
            walk_orientation = "3/4_left"
            actors[phys_actor]["orientation"] = "3/4_left"
            walk_type = "walk_left"
            
        elif raw_action in ["exit_left", "walk_out_left"] and phys_actor and phys_actor in actors:
            is_walking = True
            walk_actor = phys_actor
            start_x = actors[phys_actor]["x"]
            target_x = -650
            walk_frames = min(turn_frames, int(2.2 * fps))
            walk_orientation = "3/4_left"
            walk_type = "walk_left"
            
        elif raw_action in ["exit_right", "walk_out_right", "exit", "walk_out"] and phys_actor and phys_actor in actors:
            is_walking = True
            walk_actor = phys_actor
            start_x = actors[phys_actor]["x"]
            target_x = 2100
            walk_frames = min(turn_frames, int(2.2 * fps))
            walk_orientation = "3/4_right"
            walk_type = "walk_right"
            
        elif raw_action in ["walk_to_target", "walk_towards"] and phys_actor and phys_actor in actors:
            is_walking = True
            walk_actor = phys_actor
            start_x = actors[phys_actor]["x"]
            # Target position
            if target_tag and target_tag in actors:
                target_x = actors[target_tag]["x"] - 200 if actors[target_tag]["x"] > start_x else actors[target_tag]["x"] + 200
            elif target_tag == "door":
                target_x = 1500
            elif target_tag == "stove":
                target_x = 280
            else:
                target_x = 660
            walk_frames = min(turn_frames, int(2.0 * fps))
            walk_orientation = "3/4_right" if target_x >= start_x else "3/4_left"
            walk_type = "walk_right" if target_x >= start_x else "walk_left"
            
        elif raw_action == "walk_toward_camera" and phys_actor and phys_actor in actors:
            is_walking = True
            walk_actor = phys_actor
            start_x = actors[phys_actor]["x"]
            target_x = actors[phys_actor]["x"]
            walk_frames = min(turn_frames, int(1.8 * fps))
            walk_orientation = "front"
            walk_type = "walk_toward_camera"
            
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
