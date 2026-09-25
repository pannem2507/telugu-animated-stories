"""
Video Compositor Engine for Telugu Animated Stories
Composes articulated puppet characters, backgrounds, dynamic lip-syncing,
true 4-phase walk cycle, 3/4 conversational staging, dynamic camera system,
atmospheric particle effects, interactive props, subtitle overlays, and audio muxing via FFmpeg.
"""

import os
import sys
import math
import subprocess
import wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2

# Fix Windows console UTF-8 printing
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .tts_engine import synthesize_dialogue, get_audio_duration
from .lipsync_engine import extract_lipsync_cues
from .animation_engine import WalkCycleController, IdleController, GestureController, PuppetRenderer
from .camera_engine import CameraEngine
from .scene_director import SceneDirector
from .environment_engine import EnvironmentEngine
from .performance_director import PerformanceDirector, ListenerReactionController, ObjectManager, AudioPerformanceAnalyzer, PerformanceTimeline

from .project_config import load_project_config
_proj_config = load_project_config()

# CHARACTER_ALIASES are now loaded from the project configuration (ProjectConfig)
CHARACTER_ALIASES = _proj_config.character_aliases

# Assets directory resolved from project configuration
ASSETS_DIR = str(_proj_config.resolve_path("assets"))


class AssetCache:
    """Preloads and caches character puppet parts, props, and backgrounds."""
    def __init__(self):
        self.backgrounds = {}
        self.characters = {}
        self.props = {}
        
    def get_background(self, name: str, width: int = 1920, height: int = 1080) -> Image.Image:
        env_map = _proj_config.environments
        base_name = name[:-4] if name.endswith(".png") else name
        resolved = env_map.get(base_name, env_map.get(name, base_name))
        filename = resolved if resolved.endswith(".png") else f"{resolved}.png"
        path = os.path.join(ASSETS_DIR, "backgrounds", filename)
        if not os.path.exists(path):
            path = os.path.join(ASSETS_DIR, "backgrounds", "village_winter_porch.png")
            if not os.path.exists(path):
                path = os.path.join(ASSETS_DIR, "backgrounds", "village_kitchen.png")
            
        if path not in self.backgrounds:
            img = Image.open(path).convert("RGBA")
            if img.size != (width, height):
                img = img.resize((width, height), Image.Resampling.LANCZOS)
            self.backgrounds[path] = img
        return self.backgrounds[path].copy()
        
    def get_prop(self, name: str) -> Image.Image:
        if not name.endswith(".png"):
            name = name + ".png"
        path = os.path.join(ASSETS_DIR, "props", name)
        if path not in self.props and os.path.exists(path):
            self.props[path] = Image.open(path).convert("RGBA")
        return self.props.get(path, None)
        
    def get_character_parts(self, char_name: str) -> dict:
        char_name = char_name.lower()
        actual_char = CHARACTER_ALIASES.get(char_name, char_name)
        
        if actual_char not in self.characters:
            char_dir = os.path.join(ASSETS_DIR, "characters", actual_char)
            if not os.path.exists(char_dir):
                char_dir = os.path.join(ASSETS_DIR, "characters", "atha")
                
            base_img = Image.open(os.path.join(char_dir, "base.png")).convert("RGBA")
            eyes_open_file = os.path.join(char_dir, "eyes_open.png")
            eyes_blink_file = os.path.join(char_dir, "eyes_blink.png")
            cook_file = os.path.join(char_dir, "cook.png")
            cook_right_file = os.path.join(char_dir, "cook_right.png")
            cook_left_file = os.path.join(char_dir, "cook_left.png")
            parts = {
                "base": base_img,
                "eyes_open": Image.open(eyes_open_file).convert("RGBA") if os.path.exists(eyes_open_file) else None,
                "eyes_blink": Image.open(eyes_blink_file).convert("RGBA") if os.path.exists(eyes_blink_file) else None,
                "cook": Image.open(cook_file).convert("RGBA") if os.path.exists(cook_file) else None,
                "cook_right": Image.open(cook_right_file).convert("RGBA") if os.path.exists(cook_right_file) else None,
                "cook_left": Image.open(cook_left_file).convert("RGBA") if os.path.exists(cook_left_file) else None,
                "mouths": {}
            }
            
            for m in ["mouth_closed", "mouth_open_a", "mouth_open_e", "mouth_open_o", "mouth_teeth", "mouth_wide"]:
                m_path = os.path.join(char_dir, f"{m}.png")
                if os.path.exists(m_path):
                    parts["mouths"][m] = Image.open(m_path).convert("RGBA")
                    
            self.characters[actual_char] = parts
        return self.characters[actual_char]

# Backward compatibility wrapper
def build_character_sprite(parts: dict, mouth_cue: str, is_blinking: bool, flip_horizontal: bool = False, scale: float = 1.0, tilt_angle: float = 0.0) -> Image.Image:
    orientation = "3/4_left" if flip_horizontal else "3/4_right"
    return PuppetRenderer.render_puppet(
        parts=parts,
        mouth_cue=mouth_cue,
        is_blinking=is_blinking,
        orientation=orientation,
        scale=scale
    )

def overlay_subtitles(img: Image.Image, speaker: str, text: str):
    """Draw a clean subtitle banner at the bottom with native Telugu typography.
    Colours are loaded from ProjectConfig.subtitles.
    """
    w, h = img.size
    draw = ImageDraw.Draw(img)

    banner_h = 130
    banner_y = h - banner_h - 40
    box = [(120, banner_y), (w - 120, banner_y + banner_h)]

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    o_draw = ImageDraw.Draw(overlay)
    o_draw.rounded_rectangle(box, radius=20, fill=(15, 15, 20, 205), outline=(220, 180, 50, 230), width=3)
    img.alpha_composite(overlay)

    try:
        font_speaker = ImageFont.truetype("C:/Windows/Fonts/Nirmala.ttc", 30)
        font_text = ImageFont.truetype("C:/Windows/Fonts/Nirmala.ttc", 36)
    except Exception:
        try:
            font_speaker = ImageFont.truetype("C:/Windows/Fonts/ARIALUNI.TTF", 30)
            font_text = ImageFont.truetype("C:/Windows/Fonts/ARIALUNI.TTF", 36)
        except Exception:
            font_speaker = ImageFont.load_default()
            font_text = ImageFont.load_default()

    speaker_tag = speaker.upper()
    color_map = _proj_config.subtitles
    color_map = {k: tuple(v) for k, v in color_map.items()}
    tag_color = color_map.get(speaker_tag, (240, 240, 240))
    draw.text((160, banner_y + 15), speaker_tag, font=font_speaker, fill=tag_color)
    draw.text((160, banner_y + 60), text, font=font_text, fill=(255, 255, 255))

def render_story_video(script_data: dict, output_mp4: str, fps: int = 24) -> str:
    """
    Renders an entire script into a complete 1080p MP4 with lip-synced audio,
    BGM ducking, procedural walk cycles, 3/4 conversational staging, dynamic camera system,
    atmospheric particle effects, interactive props, and subtitles.
    """
    os.makedirs("output/temp", exist_ok=True)
    temp_video_path = os.path.abspath("output/temp/raw_video.mp4")
    temp_audio_path = os.path.abspath("output/temp/final_audio.wav")
    
    cache = AssetCache()
    width, height = 1920, 1080
    
    # Initialize animation, camera, environment, performance, and directing engines
    camera = CameraEngine(width, height)
    director = SceneDirector()
    env_engine = EnvironmentEngine(width, height)
    perf_director = PerformanceDirector()
    obj_manager = perf_director.object_manager
    walk_engine = WalkCycleController(step_duration_s=0.38, fps=fps)
    idle_controllers = {}
    
    # Set up OpenCV video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_video_path, fourcc, fps, (width, height))
    
    from pydub import AudioSegment
    combined_audio = AudioSegment.empty()
    
    total_scenes = len(script_data["scenes"])
    print(f"[Render] Starting video production for '{script_data.get('title', 'Telugu Story')}' ({total_scenes} scenes)", flush=True)
    
    global_frame = 0
    
    for s_idx, scene in enumerate(script_data["scenes"]):
        camera.reset()
        bg_name = scene.get("background", "village_winter_porch")
        dialogues = scene.get("dialogues", [])
        
        # Determine environmental effects
        scene_effects = []
        raw_effect = scene.get("effect", "")
        if raw_effect:
            for eff in raw_effect.split(","):
                eff = eff.strip()
                if eff and eff not in scene_effects:
                    scene_effects.append(eff)
        if ("winter" in bg_name.lower() or "street" in bg_name.lower() or "lake" in bg_name.lower()) and "snow" not in scene_effects:
            scene_effects.append("snow")
            
        if "kitchen" in bg_name:
            if "magic_stove" in obj_manager.objects:
                st = obj_manager.objects["magic_stove"]
                ms_cfg = _proj_config.magic_stove
                st["is_held"] = False
                st["held_by"] = None
                st["x"] = ms_cfg["anchor"][0]
                st["y"] = ms_cfg["anchor"][1]
                st["visible"] = True
                st["alpha"] = ms_cfg.get("glow_intensity", 1.0)
        elif "porch" in bg_name and s_idx > 0:
            if "magic_stove" in obj_manager.objects:
                st = obj_manager.objects["magic_stove"]
                ms_cfg = _proj_config.magic_stove
                st["is_held"] = True
                st["held_by"] = "kodalu"
                st["visible"] = False
                st["alpha"] = ms_cfg.get("glow_intensity", 1.0)

        actors = director.setup_scene(scene)
        
        for d_idx, d in enumerate(dialogues):
            speaker = d["character"].lower()
            text = d["text"]
            
            # 1. Synthesize Voice
            voice_out = f"output/temp/dialogue_s{s_idx}_d{d_idx}.mp3"
            synth_res = synthesize_dialogue(text, character=speaker, output_path=voice_out)
            wav_path = synth_res["wav_path"]
            duration_s = synth_res["duration"]
            
            turn_audio = AudioSegment.from_wav(wav_path)
            combined_audio += turn_audio
            pause_audio = AudioSegment.silent(duration=350)
            combined_audio += pause_audio
            
            # 2. Extract Lip-Sync Cues & Audio Stress Envelope
            cues = extract_lipsync_cues(wav_path, fps=fps, text=text)
            pause_frames = int(0.35 * fps)
            cues.extend(["mouth_closed"] * pause_frames)
            total_turn_frames = len(cues)
            
            audio_env = AudioPerformanceAnalyzer.extract_envelope_from_wav(wav_path, fps=fps)
            while len(audio_env) < total_turn_frames:
                audio_env.append(0.0)
            strike_beats = AudioPerformanceAnalyzer.select_performance_beats(audio_env, fps=fps, min_interval_s=0.45, stress_threshold=0.48)
            while len(strike_beats) < total_turn_frames:
                strike_beats.append(False)
            
            # 3. Plan Turn Performance & Camera
            turn_plan = director.plan_turn(d, actors, fps=fps, turn_frames=total_turn_frames)
            perf_plan = perf_director.plan_performance(d, actors, fps=fps, turn_frames=total_turn_frames)
            
            action = turn_plan["action"]
            perf_type = perf_plan["performance_type"]
            is_walking = turn_plan["is_walking"]
            walk_actor = turn_plan["walk_actor"]
            walk_type = turn_plan.get("walk_type", "walk_right")
            start_x = turn_plan["start_x"]
            target_x = turn_plan["target_x"]
            walk_frames = turn_plan["walk_frames"]
            walk_orient = turn_plan["walk_orientation"]
            camera_shot = perf_plan["camera_shot"]
            
            print(f"   -> Turn {d_idx + 1}: {speaker.upper()} [{perf_type}] (shot: {camera_shot}, {duration_s:.2f}s, {total_turn_frames} frames)", flush=True)
            
            # Configure Camera target for this turn
            stove_obj = obj_manager.objects.get("magic_stove")
            if len(actors) >= 2:
                if speaker in actors:
                    other_actors = [a for c, a in actors.items() if c != speaker]
                    two_pos = [(actors[speaker]["x"], actors[speaker]["y"]), (other_actors[0]["x"], other_actors[0]["y"])]
                else:
                    two_pos = [(a["x"], a["y"]) for a in actors.values()][:2]
            else:
                two_pos = None
            
            if camera_shot in ["medium_character", "speaker_medium", "speaker", "kodalu_medium", "maharshi_medium"]:
                target_char = None
                for c_name in actors:
                    if c_name in camera_shot:
                        target_char = c_name
                        break
                if not target_char:
                    target_char = speaker
                if target_char in actors:
                    camera.set_shot("medium_character", target_pos=(actors[target_char]["x"], actors[target_char]["y"]))
                else:
                    camera.set_shot("wide")
            elif camera_shot in ["medium_two_shot", "two_shot", "wide_two_shot"]:
                camera.set_shot(camera_shot, two_shot_targets=two_pos)
            elif camera_shot in ["speaker_closeup", "closeup", "kodalu_closeup", "maharshi_closeup"]:
                target_char = None
                for c_name in actors:
                    if c_name in camera_shot:
                        target_char = c_name
                        break
                if not target_char:
                    target_char = speaker
                if target_char in actors:
                    camera.set_shot("speaker_closeup", target_pos=(actors[target_char]["x"], actors[target_char]["y"]))
                else:
                    camera.set_shot("wide")
            elif camera_shot in ["reaction_closeup", "maharshi_reaction", "kodalu_reaction"]:
                target_char = None
                for c_name in actors:
                    if c_name in camera_shot:
                        target_char = c_name
                        break
                if not target_char:
                    listeners = [c for c in actors if c != speaker]
                    target_char = listeners[0] if listeners else speaker
                if target_char in actors:
                    camera.set_shot("reaction_closeup", target_pos=(actors[target_char]["x"], actors[target_char]["y"]))
                else:
                    camera.set_shot("wide")
            elif camera_shot in ["insert_object", "object_insert"]:
                target_p = stove_obj or (next(iter(obj_manager.objects.values())) if obj_manager.objects else None)
                obj_pos = (target_p["x"] + 150, target_p["y"] + 100) if target_p else None
                camera.set_shot("insert_object", object_pos=obj_pos)
            elif camera_shot in ["magic_wide"]:
                camera.set_shot("magic_wide")
            elif camera_shot in ["follow_walk", "follow_exit"] and is_walking and walk_actor in actors:
                camera.set_shot("follow_walk", target_pos=(start_x, actors[walk_actor]["y"]))
            else:
                camera.set_shot("wide")

            if d_idx == 0:
                camera.snap_to_target()
                
            # Check for turn-level magic sparkle / steam effect
            turn_effects = list(scene_effects)
            if ("magic" in action or "à°®à°¾à°¯à°¾" in text or "magic" in perf_type or camera_shot == "magic_wide") and "magic" not in turn_effects:
                turn_effects.append("magic")
            if ("cook" in action or "stir" in action) and "steam" not in turn_effects:
                turn_effects.append("steam")
                
            # 4. Render Video Frames
            for f_idx in range(total_turn_frames):
                bg_frame = cache.get_background(bg_name, width, height)
                active_mouth = cues[f_idx]
                turn_progress = f_idx / float(total_turn_frames)
                a_stress = audio_env[f_idx] if f_idx < len(audio_env) else 0.0
                is_strike = strike_beats[f_idx] if f_idx < len(strike_beats) else False
                
                # Evaluate Performance Timeline
                timeline_id = perf_plan.get("timeline_id", "standard_timeline")
                perf_eval = perf_director.evaluate_performance_frame(
                    timeline_id, f_idx, fps=fps, audio_stress=a_stress, is_strike_beat=is_strike
                )
                
                # Update interactive props
                if "magic" in turn_effects or "reveal_object" in action:
                    obj_manager.reveal_object("magic_stove", min(1.0, turn_progress * 1.5))
                if perf_type == "pickup_sequence" and turn_progress > 0.65:
                    obj_manager.attach_to_character("magic_stove", speaker)
                elif action in ["carry", "hold_object"]:
                    obj_manager.attach_to_character("magic_stove", speaker)
                    
                speaker_blink = ((global_frame + 20) % 75) in [0, 1, 2]
                
                # Render actors
                for ch_name, actor in actors.items():
                    if not actor.get("is_present", True):
                        continue
                    if ch_name not in idle_controllers:
                        idle_controllers[ch_name] = IdleController(seed=len(idle_controllers), char_id=ch_name)
                        
                    parts = cache.get_character_parts(ch_name)
                    is_speaker = (ch_name == speaker)
                    m_cue = active_mouth if is_speaker else "mouth_closed"
                    
                    walk_state = None
                    gesture_state = None
                    list_info = {}
                    idle_state = idle_controllers[ch_name].evaluate(global_frame)
                    
                    cur_x = actor["x"]
                    cur_y = actor["y"]
                    cur_orient = actor["orientation"]
                    actor_scale = actor.get("scale", 1.0)
                    cur_emotion = "neutral"
                    cur_intensity = 0.5
                    cur_tear_state = "none"
                    cur_tear_progress = 0.0
                    cur_gesture = "idle"
                    cur_chest_sink = 0.0
                    
                    if is_walking and ch_name == walk_actor:
                        if f_idx < walk_frames:
                            prog = f_idx / float(walk_frames)
                            is_exit_walk = (target_x >= 1900 or target_x <= -500)
                            if is_exit_walk:
                                # Exit acceleration: full walking momentum into off-screen exit
                                exit_prog = prog ** 1.2
                                cur_x = int(start_x + (target_x - start_x) * exit_prog)
                            else:
                                smooth_prog = 3.0 * (prog ** 2) - 2.0 * (prog ** 3)
                                cur_x = int(start_x + (target_x - start_x) * smooth_prog)
                            actor["x"] = cur_x

                            # Check if character has walked completely off-screen during exit
                            if (target_x >= 1920 and cur_x >= 1920) or (target_x <= -500 and cur_x <= -500):
                                actor["is_present"] = False
                                continue

                            travel_dist = abs(target_x - start_x)
                            walk_state = walk_engine.evaluate(f_idx, walk_type=walk_type, total_walk_frames=walk_frames, char_id=walk_actor, travel_distance=travel_dist)
                            cur_orient = walk_orient
                            cur_emotion = perf_plan.get("emotion", "neutral") if is_speaker else "neutral"
                            cur_intensity = 0.6 if is_speaker else 0.5
                            cur_tear_state = "none"
                            cur_tear_progress = 0.0
                            is_carrying = any(p.get("is_held") and p.get("held_by") == ch_name for p in obj_manager.objects.values()) or "carry" in action
                            cur_gesture = "carry" if is_carrying else "walk"
                            cur_chest_sink = 0.0

                            # If character is speaking while in transit, articulate speech nods and head movement
                            if is_speaker:
                                raw_transit_g = perf_director.evaluate_acting_frame(
                                    "speaking", f_idx, total_turn_frames, is_speaker=True,
                                    audio_stress=a_stress, is_strike_beat=is_strike,
                                    char_id=walk_actor
                                )
                                # During locomotion transit, arms maintain carry posture if holding prop, or resting swing
                                gesture_state = dict(raw_transit_g)
                                if is_carrying:
                                    gesture_state["left_arm_rot"] = 24.0
                                    gesture_state["right_arm_rot"] = -24.0
                                else:
                                    gesture_state["left_arm_rot"] = 0.0
                                    gesture_state["right_arm_rot"] = 0.0
                            elif is_carrying:
                                gesture_state = {
                                    "left_arm_rot": 24.0,
                                    "right_arm_rot": -24.0,
                                    "head_rot": 0.0,
                                    "bob_y": 0.0,
                                    "torso_roll": 0.0,
                                    "scale_x": 1.0,
                                    "scale_y": 1.0
                                }

                            if camera_shot in ["follow_walk", "follow_exit"]:
                                crop_w = int(width / camera.target_zoom)
                                min_cam_x = crop_w / 2.0
                                max_cam_x = width - (crop_w / 2.0)
                                
                                # Dynamic tracking of walking actor across valid camera bounds
                                actor_cx = cur_x + 300.0
                                other_actors_x = [a["x"] + 300.0 for c, a in actors.items() if c != walk_actor and a.get("is_present", True)]
                                if other_actors_x and camera_shot == "follow_walk":
                                    group_cx = (actor_cx + other_actors_x[0]) / 2.0
                                    t_w = f_idx / float(max(1, walk_frames))
                                    smooth_t = 3.0 * (t_w ** 2) - 2.0 * (t_w ** 3)
                                    desired_cx = actor_cx * (1.0 - smooth_t * 0.5) + group_cx * (smooth_t * 0.5)
                                else:
                                    desired_cx = actor_cx
                                camera.target_cx = max(min_cam_x, min(max_cam_x, desired_cx))
                                camera.target_cy = cur_y + (walk_state["y_bob"] if walk_state else 0.0) * 0.4 + 270.0
                        else:
                            cur_x = target_x
                            actor["x"] = target_x
                            if target_x <= -500 or target_x >= 1920:
                                actor["is_present"] = False
                                continue
                            actor["orientation"] = walk_orient
                            cur_orient = walk_orient
                            # Smooth post-walk settling transition (decay leftover stride bobbing over 10 frames)
                            settle_idx = f_idx - walk_frames
                            if settle_idx < 10:
                                settle_decay = 1.0 - (settle_idx / 10.0)
                                ws = walk_engine.evaluate(walk_frames, walk_type=walk_type, total_walk_frames=walk_frames, char_id=walk_actor, travel_distance=abs(target_x - start_x))
                                if ws:
                                    walk_state = {k: (v if k in ["scale_mod", "phase", "dampen"] else v * settle_decay) if isinstance(v, (int, float)) else v for k, v in ws.items()}
                            
                            # Resume active speaker emotional expression & gestures post-walk
                            if is_speaker:
                                cur_emotion = perf_plan["emotion"]
                                cur_intensity = perf_eval["emotion_intensity"]
                                cur_tear_state = perf_eval["tear_state"]
                                cur_tear_progress = perf_eval["tear_progress"]
                                cur_gesture = perf_eval["gesture"] if perf_eval.get("gesture", "idle") not in ["idle", "walk", "walk_in_right", "walk_in_left", "walk_out_right", "walk_out_left"] else "speaking"
                                cur_chest_sink = perf_eval["chest_sink"]
                                raw_g = perf_director.evaluate_acting_frame(
                                    cur_gesture, f_idx, total_turn_frames, is_speaker=True,
                                    audio_stress=a_stress, is_strike_beat=is_strike,
                                    char_id=ch_name
                                )
                                if settle_idx < 10:
                                    # Smooth cross-fade from walk settling to conversational speaking gesture
                                    t_blend = settle_idx / 10.0
                                    smooth_blend = 3.0 * (t_blend ** 2) - 2.0 * (t_blend ** 3)
                                    gesture_state = {
                                        k: (v * smooth_blend) if isinstance(v, (int, float)) else v
                                        for k, v in raw_g.items()
                                    }
                                else:
                                    gesture_state = raw_g
                            else:
                                speaker_actor = actors.get(speaker)
                                speaker_coords = (speaker_actor["x"], speaker_actor["y"]) if speaker_actor else None
                                listener_coords = (cur_x, cur_y)
                                speaker_emotion = perf_plan.get("emotion", d.get("emotion", "neutral"))
                                list_info = perf_director.listener_controller.evaluate_listener(
                                    listener_id=ch_name,
                                    speaker_id=speaker,
                                    emotion=speaker_emotion,
                                    frame_idx=f_idx,
                                    total_frames=total_turn_frames,
                                    listener_pos=listener_coords,
                                    speaker_pos=speaker_coords,
                                    speaker_audio_stress=a_stress
                                )
                                cur_x += int(list_info["x_offset"])
                                actor_scale = actor.get("scale", 1.0) * list_info["scale_mod"]
                                cur_emotion = list_info["face_emotion"]
                                cur_intensity = list_info["fear_intensity"] if cur_emotion == "cower" else list_info["empathy_intensity"]
                                cur_tear_state = "none"
                                cur_tear_progress = 0.0
                                cur_gesture = "idle"
                                cur_chest_sink = 0.0
                                
                                gesture_state = {
                                    "head_rot": list_info["head_rot"],
                                    "left_arm_rot": list_info.get("left_arm_rot", 0.0),
                                    "right_arm_rot": list_info.get("right_arm_rot", 0.0),
                                    "jitter_x": list_info.get("jitter_x", 0.0),
                                    "jitter_y": list_info.get("jitter_y", 0.0),
                                    "bob_y": list_info["sway_y"],
                                    "torso_roll": list_info.get("torso_roll", 0.0),
                                    "scale_x": 1.0,
                                    "scale_y": 1.0
                                }
                        
                    elif is_speaker:
                        gesture_state = perf_director.evaluate_acting_frame(
                            perf_type, f_idx, total_turn_frames, is_speaker=True,
                            audio_stress=a_stress, is_strike_beat=is_strike,
                            char_id=ch_name
                        )
                        cur_emotion = perf_plan["emotion"]
                        cur_intensity = perf_eval["emotion_intensity"]
                        cur_tear_state = perf_eval["tear_state"]
                        cur_tear_progress = perf_eval["tear_progress"]
                        cur_gesture = perf_eval["gesture"] if perf_eval.get("gesture", "idle") != "idle" else (perf_type or action)
                        cur_chest_sink = perf_eval["chest_sink"]
                        if perf_type in ["turn", "turn_around", "turn_left", "turn_right"] or action in ["turn", "turn_around", "turn_left", "turn_right"]:
                            if f_idx >= int(total_turn_frames * 0.45):
                                if "left" in (perf_type or action):
                                    cur_orient = "3/4_left"
                                elif "right" in (perf_type or action):
                                    cur_orient = "3/4_right"
                                else:
                                    cur_orient = "3/4_left" if "right" in actor.get("orientation", "3/4_right") else "3/4_right"
                                actor["orientation"] = cur_orient
                    else:
                        # Listener dynamic performance with reaction latency responding to active speaker emotion
                        speaker_actor = actors.get(speaker)
                        speaker_coords = (speaker_actor["x"], speaker_actor["y"]) if speaker_actor else None
                        listener_coords = (actor["x"], actor["y"])
                        speaker_emotion = perf_plan.get("emotion", d.get("emotion", "neutral"))
                        list_info = perf_director.listener_controller.evaluate_listener(
                            listener_id=ch_name,
                            speaker_id=speaker,
                            emotion=speaker_emotion,
                            frame_idx=f_idx,
                            total_frames=total_turn_frames,
                            listener_pos=listener_coords,
                            speaker_pos=speaker_coords,
                            speaker_audio_stress=a_stress
                        )
                        cur_x += int(list_info["x_offset"])
                        actor_scale = actor.get("scale", 1.0) * list_info["scale_mod"]
                        cur_emotion = list_info["face_emotion"]
                        cur_intensity = list_info["fear_intensity"] if cur_emotion == "cower" else list_info["empathy_intensity"]
                        cur_tear_state = "none"
                        cur_tear_progress = 0.0
                        cur_gesture = "idle"
                        cur_chest_sink = 0.0
                        
                        gesture_state = {
                            "head_rot": list_info["head_rot"],
                            "left_arm_rot": list_info.get("left_arm_rot", 0.0),
                            "right_arm_rot": list_info.get("right_arm_rot", 0.0),
                            "jitter_x": list_info.get("jitter_x", 0.0),
                            "jitter_y": list_info.get("jitter_y", 0.0),
                            "bob_y": list_info["sway_y"],
                            "torso_roll": list_info.get("torso_roll", 0.0),
                            "scale_x": 1.0,
                            "scale_y": 1.0
                        }
                        
                    is_blinking = speaker_blink if is_speaker else list_info.get("is_blinking", False)
                    
                    sprite = PuppetRenderer.render_puppet(
                        parts=parts,
                        mouth_cue=m_cue,
                        is_blinking=is_blinking,
                        char_id=ch_name,
                        emotion=cur_emotion,
                        emotion_intensity=cur_intensity,
                        audio_stress=a_stress if is_speaker else 0.0,
                        tear_state=cur_tear_state,
                        tear_progress=cur_tear_progress,
                        gesture_pose=cur_gesture,
                        frame_idx=global_frame,
                        chest_sink=cur_chest_sink,
                        walk_state=walk_state,
                        idle_state=idle_state,
                        gesture_state=gesture_state,
                        orientation=cur_orient,
                        scale=actor_scale
                    )
                    
                    # Calculate physical offsets for sprite screen placement from walking, tremor, and idle
                    char_offset_x = 0
                    char_offset_y = 0

                    if walk_state:
                        char_offset_y += int(walk_state.get("y_bob", 0.0))
                        char_offset_x += int(walk_state.get("settle_shift_x", 0.0))
                    if gesture_state:
                        char_offset_y += int(gesture_state.get("bob_y", 0.0))
                    elif idle_state and not walk_state:
                        char_offset_y += int(idle_state.get("sway_y", 0.0))

                    if gesture_state:
                        char_offset_x += int(gesture_state.get("jitter_x", 0.0))
                        char_offset_y += int(gesture_state.get("jitter_y", 0.0))
                    elif idle_state and not walk_state:
                        char_offset_x += int(idle_state.get("sway_x", 0.0))

                    render_x = cur_x + char_offset_x
                    render_y = cur_y + char_offset_y

                    # Draw soft ambient ground contact shadow
                    shadow_y = cur_y + 860
                    shadow_x = cur_x + 300 + char_offset_x
                    shadow_w = 140
                    shadow_h = 24
                    total_bob = (walk_state.get("y_bob", 0.0) if walk_state else 0.0) + (gesture_state.get("bob_y", 0.0) if gesture_state else 0.0)
                    if abs(total_bob) > 0.1:
                        shadow_w = int(140 + total_bob * 1.5)
                    s_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                    s_draw = ImageDraw.Draw(s_overlay)
                    s_draw.ellipse([(shadow_x - shadow_w//2, shadow_y - shadow_h//2),
                                     (shadow_x + shadow_w//2, shadow_y + shadow_h//2)],
                                   fill=(20, 20, 25, 60))
                    bg_frame.alpha_composite(s_overlay)
                    
                    # Composite character sprite at physical render coordinates
                    bg_frame.alpha_composite(sprite, dest=(render_x, render_y))
                    
                    # Update held object position
                    for p_id, p_obj in obj_manager.objects.items():
                        if p_obj.get("is_held") and p_obj.get("held_by") == ch_name:
                            obj_manager.update_held_position(p_id, render_x, render_y, walk_state["y_bob"] if walk_state else 0, orientation=cur_orient, scale=actor_scale)
                            p_obj["visible"] = True
                        
                # 5. Render Interactive Props (Generic Prop Engine)
                for p_id, p_obj in obj_manager.objects.items():
                    holder = p_obj.get("held_by")
                    is_held_absent = p_obj.get("is_held") and holder and (holder not in actors or not actors[holder].get("is_present", True))
                    if not is_held_absent and p_obj.get("visible", False) and p_obj.get("alpha", 0.0) > 0.05:
                        prop_asset = p_obj.get("asset_name", f"{p_id}.png")
                        p_img = cache.get_prop(prop_asset)
                        if p_img:
                            obj_manager.render_prop(p_id, bg_frame, p_img, global_frame)
                        
                # 6. Render Environmental Effects (Snow, Steam, Magic Sparkles)
                env_engine.render(bg_frame, global_frame, turn_effects)
                
                # 7. Update and Apply Camera Engine
                # Subtle camera micro recoil on shouting peaks (max 1.5px, within 0-2px limit)
                if perf_plan["emotion"] in ["angry", "scold"] and is_strike and a_stress > 0.60:
                    recoil_x = math.sin(f_idx * 1.5) * 1.4
                    recoil_y = math.cos(f_idx * 1.8) * 0.9
                    camera.current_cx += recoil_x
                    camera.current_cy += recoil_y
                    
                camera.update(smoothing=0.12)
                bg_frame = camera.apply(bg_frame)
                
                # 8. Overlay Subtitle Banner
                overlay_subtitles(bg_frame, speaker=speaker, text=text)
                
                # Convert to OpenCV BGR and write
                cv_frame = cv2.cvtColor(np.array(bg_frame), cv2.COLOR_RGBA2BGR)
                out.write(cv_frame)
                
                global_frame += 1
                
            # If this turn was an exit, mark actor as not present for subsequent turns
            if action in ["exit_left", "walk_out_left", "exit_right", "walk_out_right", "exit", "walk_out"] or director.behavior_registry.is_exit_action(action):
                if walk_actor and walk_actor in actors:
                    actors[walk_actor]["is_present"] = False
                
    out.release()
    print(f"[Render] Video frames completed ({global_frame} frames). Mixing audio...")
    
    # Export Combined Dialogue Audio
    dialogue_wav = "output/temp/dialogues_combined.wav"
    combined_audio.export(dialogue_wav, format="wav")
    
    # Mix Background Music (ducked to -20dB)
    bgm_path = os.path.join(ASSETS_DIR, "audio", "village_bgm.wav")
    final_audio = AudioSegment.from_wav(dialogue_wav)
    
    if os.path.exists(bgm_path):
        bgm = AudioSegment.from_wav(bgm_path)
        loops_needed = int(len(final_audio) / len(bgm)) + 2
        bgm_looped = bgm * loops_needed
        bgm_looped = bgm_looped[:len(final_audio)]
        bgm_ducked = bgm_looped - 20
        mixed_audio = bgm_ducked.overlay(final_audio)
        mixed_audio.export(temp_audio_path, format="wav")
    else:
        final_audio.export(temp_audio_path, format="wav")
        
    output_mp4 = os.path.abspath(output_mp4)
    os.makedirs(os.path.dirname(output_mp4), exist_ok=True)
    
    print(f"[Render] Muxing video and audio with FFmpeg into: {output_mp4}", flush=True)
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", temp_video_path,
        "-i", temp_audio_path,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_mp4
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"[Render] SUCCESS! Video generated at: {output_mp4}", flush=True)
    return output_mp4


def inspect_frame_state(frame_idx: int, actors: dict, current_shot: str,
                        camera_target: tuple, cues: dict = None) -> dict:
    """
    Lightweight diagnostic snapshot for inspecting animation, actor positioning,
    mouth states, and camera tracking without noisy stdout output.
    """
    snapshot = {
        "frame_idx": frame_idx,
        "shot": current_shot,
        "camera_target": camera_target,
        "actors": {}
    }
    for name, a in actors.items():
        snapshot["actors"][name] = {
            "x": a.get("x", 0),
            "y": a.get("y", 0),
            "is_present": a.get("is_present", True),
            "orientation": a.get("orientation", "3/4_right"),
            "action": a.get("action", "idle")
        }
    return snapshot

