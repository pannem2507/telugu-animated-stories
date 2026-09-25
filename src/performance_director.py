"""
Upgraded Performance Director for Telugu Animated Stories
Implements:
1. Audio Envelope -> Stress Peaks -> Beat Selection with Min Attack Interval
2. Reaction Latency (150ms-400ms delay before listener physical response)
3. Continuous Intensity-Driven Listener Cowering / Softening (smooth interpolation)
4. Reusable Performance Timelines (multi-beat acting sequences)
5. Secondary Motion Spring-Damper Lag (hair, braid, saree, jewelry, settling)
6. Integrated Object Manager with Hand IK targets
"""

import math
import numpy as np
from .prop_engine import GenericPropManager

class AudioPerformanceAnalyzer:
    """
    Extracts RMS envelope from dialogue audio, finds syllabic stress peaks,
    and filters them with a minimum attack interval for organic acting emphasis.
    """
    @staticmethod
    def extract_envelope_from_wav(wav_path: str, fps: int = 24) -> list:
        import wave
        try:
            with wave.open(wav_path, 'rb') as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                raw_bytes = wf.readframes(n_frames)
                
            if sampwidth == 2:
                audio_data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
            else:
                audio_data = np.frombuffer(raw_bytes, dtype=np.int8).astype(np.float32)
                
            if n_channels > 1:
                audio_data = audio_data.reshape(-1, n_channels).mean(axis=1)
                
            samples_per_video_frame = int(framerate / float(fps))
            total_video_frames = max(1, int(len(audio_data) / samples_per_video_frame))
            
            envelope = []
            for f in range(total_video_frames):
                start = f * samples_per_video_frame
                end = min(len(audio_data), start + samples_per_video_frame)
                chunk = audio_data[start:end]
                if len(chunk) > 0:
                    rms = np.sqrt(np.mean(chunk ** 2))
                    envelope.append(float(rms))
                else:
                    envelope.append(0.0)
                    
            # Normalize to [0.0, 1.0]
            max_val = max(1.0, max(envelope))
            norm_envelope = [min(1.0, val / (max_val * 0.85)) for val in envelope]
            return norm_envelope
        except Exception:
            return [0.0] * 24

    @staticmethod
    def select_performance_beats(envelope: list, fps: int = 24,
                                 min_interval_s: float = 0.45,
                                 stress_threshold: float = 0.48) -> list:
        """
        Enforces a minimum interval between physical gesture attacks.
        Returns a list of booleans indicating frame-by-frame beat strikes.
        """
        min_frames = int(min_interval_s * fps)
        beats = [False] * len(envelope)
        last_beat = -min_frames
        
        for i in range(1, len(envelope) - 1):
            val = envelope[i]
            # Local peak detection
            is_peak = (val >= envelope[i - 1] and val >= envelope[i + 1])
            if is_peak and val >= stress_threshold:
                if (i - last_beat) >= min_frames:
                    beats[i] = True
                    last_beat = i
                    
        return beats

class SecondaryMotionOscillator:
    """
    Damped harmonic spring-damper oscillator for secondary cloth, braid,
    and jewelry motion that lags behind primary body kinematic acceleration.
    """
    def __init__(self, spring_k: float = 14.0, damping_c: float = 3.5):
        self.k = spring_k
        self.c = damping_c
        self.pos = 0.0
        self.vel = 0.0
        
    def update(self, primary_target: float, dt: float = 0.0416) -> float:
        # Spring force towards primary target + velocity damping
        force = -self.k * (self.pos - primary_target) - self.c * self.vel
        self.vel += force * dt
        self.pos += self.vel * dt
        return self.pos

class ListenerReactionController:
    """
    Organic listener simulation with configurable reaction latency (150ms - 400ms)
    and continuous intensity-driven physical interpolation.
    """
    def __init__(self, default_latency_ms: int = 250, fps: int = 24):
        self.latency_frames = max(2, int((default_latency_ms / 1000.0) * fps))
        self.fps = fps
        self.phase_seeds = {
            "atha": 0.2, "kodalu": 1.7, "maharshi": 3.1,
            "saroja": 4.5, "padma": 2.8, "gent": 5.2, "kid": 2.1, "father_in_law": 3.8
        }
        
    @staticmethod
    def smooth_hermite(t: float) -> float:
        t = max(0.0, min(1.0, t))
        return 3.0 * (t ** 2) - 2.0 * (t ** 3)
        
    def evaluate_listener(self, listener_id: str, speaker_id: str, emotion: str,
                          frame_idx: int, total_frames: int, listener_pos: tuple,
                          speaker_pos: tuple, speaker_audio_stress: float = 0.0) -> dict:
        seed = self.phase_seeds.get(listener_id, (abs(hash(listener_id)) % 10) * 0.65 + 0.5)
        t = (frame_idx * 0.08) + seed
        
        # 1. Orientation / Head look-at direction toward speaker
        if speaker_pos and listener_pos:
            look_right = (speaker_pos[0] > listener_pos[0])
            head_look_angle = 3.5 if look_right else -3.5
        else:
            head_look_angle = 0.0
            
        # 2. Responsive nod on speech rhythm
        nod_cycle = 44
        nod_phase = (frame_idx + int(seed * 20)) % nod_cycle
        nod_angle = 0.0
        if nod_phase < 12:
            nod_angle = math.sin((nod_phase / 12.0) * math.pi) * 3.5
            
        # 3. Postural breathing micro-sway
        sway_y = math.sin(t * 0.4) * 1.5
        sway_x = math.cos(t * 0.3) * 0.9
        
        # 4. Reaction Latency & Continuous Intensity Evaluation
        # Listener does NOT react immediately; reaction begins after latency_frames
        emotion_l = emotion.lower() if emotion else "neutral"
        
        effective_frame = max(0, frame_idx - self.latency_frames)
        transition_duration = int(0.6 * self.fps) # 0.6s smooth transition
        reaction_prog = min(1.0, effective_frame / float(max(1, transition_duration)))
        smooth_factor = self.smooth_hermite(reaction_prog)
        
        fear_intensity = 0.0
        empathy_intensity = 0.0
        cower_x_offset = 0.0
        cower_scale_mod = 1.0
        reaction_head_rot = 0.0
        
        if emotion_l in ["angry", "scold", "irritation", "peak_anger", "anger"]:
            # Fear rises with latency and speaker audio stress
            fear_intensity = min(1.0, (0.75 + speaker_audio_stress * 0.25) * smooth_factor)
            # Continuous physical interpolation:
            # Retreat away from speaker:
            retreat_dir = 1.0 if (speaker_pos and speaker_pos[0] < listener_pos[0]) else -1.0
            cower_x_offset = retreat_dir * (fear_intensity * 32.0)
            cower_scale_mod = 1.0 - (fear_intensity * 0.09)
            reaction_head_rot = fear_intensity * 7.5
            nod_angle *= (1.0 - fear_intensity * 0.8) # stiffens in fear
            face_emotion = "cower"

        elif emotion_l in ["fear", "cower", "scared", "tremble"]:
            fear_intensity = min(1.0, 0.85 * smooth_factor)
            retreat_dir = 1.0 if (speaker_pos and speaker_pos[0] < listener_pos[0]) else -1.0
            cower_x_offset = retreat_dir * (fear_intensity * 24.0)
            cower_scale_mod = 1.0 - (fear_intensity * 0.06)
            reaction_head_rot = fear_intensity * 6.0
            nod_angle *= 0.3
            face_emotion = "cower"
            
        elif emotion_l in ["cry", "weep", "sad", "sadness", "crying", "intense_crying"]:
            # Empathy softens posture, steps slightly forward toward speaker
            empathy_intensity = min(1.0, 0.85 * smooth_factor)
            advance_dir = -1.0 if (speaker_pos and speaker_pos[0] < listener_pos[0]) else 1.0
            cower_x_offset = advance_dir * (empathy_intensity * 16.0)
            reaction_head_rot = - (empathy_intensity * 4.0) # tilts head sympathetically
            face_emotion = "sad"
            
        elif emotion_l in ["surprised", "surprise", "shock"]:
            face_emotion = "surprised"
            reaction_head_rot = -4.0 * smooth_factor

        elif emotion_l in ["reverence", "pray", "namaste", "devotion", "bow"]:
            face_emotion = "reverence"
            reaction_head_rot = 3.5 * smooth_factor
            empathy_intensity = min(1.0, 0.7 * smooth_factor)

        elif emotion_l in ["relief", "sigh"]:
            face_emotion = "relief"
            reaction_head_rot = 2.0 * smooth_factor
            empathy_intensity = min(1.0, 0.6 * smooth_factor)

        elif emotion_l in ["happy", "joy", "excited", "cheerful"]:
            face_emotion = "happy"
            reaction_head_rot = -2.5 * smooth_factor
            nod_angle *= 1.3
            empathy_intensity = min(1.0, 0.8 * smooth_factor)
        else:
            if listener_id == "kodalu":
                face_emotion = "sad"
                empathy_intensity = min(1.0, 0.75 * smooth_factor)
            else:
                face_emotion = "neutral"
            
        # 5. Organic Eyeblink & Reactive Limb Posture
        blink = ((frame_idx + int(seed * 35)) % 82) in [0, 1, 2]
        
        list_arm_l = 0.0
        list_arm_r = 0.0
        list_torso = 0.0
        if face_emotion == "cower":
            list_arm_l = 14.0 * fear_intensity
            list_arm_r = -14.0 * fear_intensity
            list_torso = 2.5 * fear_intensity
        elif face_emotion == "reverence":
            list_arm_l = 16.0 * smooth_factor
            list_arm_r = -16.0 * smooth_factor
            list_torso = 1.0 * smooth_factor
        elif face_emotion == "relief":
            list_arm_l = 4.0 * smooth_factor
            list_arm_r = -4.0 * smooth_factor
            list_torso = -1.0 * smooth_factor
        elif face_emotion == "happy":
            list_arm_l = 8.0 * smooth_factor
            list_arm_r = -8.0 * smooth_factor

        return {
            "face_emotion": face_emotion,
            "fear_intensity": fear_intensity,
            "empathy_intensity": empathy_intensity,
            "x_offset": cower_x_offset,
            "scale_mod": cower_scale_mod,
            "head_rot": head_look_angle + nod_angle + reaction_head_rot,
            "sway_x": sway_x,
            "sway_y": sway_y,
            "left_arm_rot": list_arm_l,
            "right_arm_rot": list_arm_r,
            "torso_roll": list_torso,
            "is_blinking": blink
        }

class PerformanceTimeline:
    """
    Defines multi-beat, multi-second acting progressions for characters.
    Interpolates continuous emotion_intensity, tear states, and arm poses.
    """
    TIMELINES = {
        "scold_timeline": [
            # (timestamp_sec, emotion_intensity, gesture, head_accent, torso_lean, notes)
            (0.0, 0.2, "idle", 0.0, 1.0),
            (0.5, 0.6, "idle", 3.0, 2.5),
            (1.0, 1.0, "point", 6.5, 4.2), # Emphatic point jab starts
            (3.8, 0.9, "point", 4.5, 3.8),
            (5.5, 0.7, "point", 3.0, 2.0),
            (7.0, 0.4, "idle", 1.0, 1.0)
        ],
        "cry_timeline": [
            # (timestamp_sec, emotion_intensity, tear_state, tear_progress, gesture, head_drop, chest_sink)
            (0.0, 0.2, "none", 0.0, "idle", 2.0, 0.0),
            (0.8, 0.5, "accumulate", 0.3, "idle", 5.0, 0.02),
            (1.6, 0.75, "form", 0.7, "idle", 8.5, 0.04),
            (2.5, 1.0, "flow", 0.4, "idle", 11.0, 0.06), # Tears flowing
            (3.8, 1.0, "flow", 0.9, "wipe_face", 9.0, 0.05), # Hand raises to wipe tears
            (5.0, 0.85, "wipe", 0.6, "wipe_face", 7.0, 0.04),
            (6.5, 0.65, "none", 1.0, "idle", 4.0, 0.02),
            (8.0, 0.3, "none", 1.0, "idle", 1.0, 0.0)
        ],
        "pray_timeline": [
            (0.0, 0.3, "idle", 0.0, 0.0),
            (0.6, 0.7, "pray", 3.5, 1.0),
            (1.2, 1.0, "pray", 6.0, 2.0),
            (4.5, 1.0, "pray", 6.0, 2.0),
            (6.0, 0.4, "idle", 1.0, 0.0)
        ],
        "cook_timeline": [
            (0.0, 0.5, "cook", 4.0, 2.0),
            (3.0, 0.7, "cook", 4.0, 2.0),
            (6.0, 0.5, "cook", 4.0, 2.0)
        ],
        "shiver_timeline": [
            # (timestamp_sec, emotion_intensity, gesture, head_accent, torso_lean)
            (0.0, 0.6, "shiver", 3.0, 1.5),
            (1.5, 0.9, "shiver", 5.0, 2.0),
            (4.0, 0.95, "shiver", 4.5, 2.0),
            (8.0, 0.7, "shiver", 2.0, 1.0)
        ]
    }
    
    @classmethod
    def evaluate(cls, timeline_id: str, elapsed_sec: float) -> dict:
        tl = cls.TIMELINES.get(timeline_id)
        if not tl:
            return {"emotion_intensity": 0.5, "gesture": "idle", "tear_state": "none", "tear_progress": 0.0}
            
        # Find bracketing keyframes
        if elapsed_sec <= tl[0][0]:
            kf = tl[0]
            return cls._pack_keyframe(timeline_id, kf)
        if elapsed_sec >= tl[-1][0]:
            kf = tl[-1]
            return cls._pack_keyframe(timeline_id, kf)
            
        for i in range(len(tl) - 1):
            k1 = tl[i]
            k2 = tl[i + 1]
            if k1[0] <= elapsed_sec <= k2[0]:
                u = (elapsed_sec - k1[0]) / float(k2[0] - k1[0])
                # Smooth cubic blend
                smooth_u = 3.0 * (u ** 2) - 2.0 * (u ** 3)
                return cls._interpolate_keyframes(timeline_id, k1, k2, smooth_u)
                
        return cls._pack_keyframe(timeline_id, tl[0])
        
    @staticmethod
    def _pack_keyframe(tl_id: str, kf: tuple) -> dict:
        if "scold" in tl_id:
            return {
                "emotion_intensity": kf[1],
                "gesture": kf[2],
                "head_accent": kf[3],
                "torso_lean": kf[4],
                "tear_state": "none",
                "tear_progress": 0.0,
                "chest_sink": 0.0
            }
        elif "cry" in tl_id:
            return {
                "emotion_intensity": kf[1],
                "tear_state": kf[2],
                "tear_progress": kf[3],
                "gesture": kf[4],
                "head_accent": kf[5],
                "chest_sink": kf[6],
                "torso_lean": 1.0
            }
        else:
            return {
                "emotion_intensity": kf[1],
                "gesture": kf[2],
                "head_accent": kf[3],
                "torso_lean": kf[4] if len(kf) > 4 else 0.0,
                "tear_state": "none",
                "tear_progress": 0.0,
                "chest_sink": 0.0
            }
            
    @staticmethod
    def _interpolate_keyframes(tl_id: str, k1: tuple, k2: tuple, u: float) -> dict:
        intensity = k1[1] + (k2[1] - k1[1]) * u
        if "scold" in tl_id:
            return {
                "emotion_intensity": intensity,
                "gesture": k2[2] if u > 0.3 else k1[2],
                "head_accent": k1[3] + (k2[3] - k1[3]) * u,
                "torso_lean": k1[4] + (k2[4] - k1[4]) * u,
                "tear_state": "none",
                "tear_progress": 0.0,
                "chest_sink": 0.0
            }
        elif "cry" in tl_id:
            return {
                "emotion_intensity": intensity,
                "tear_state": k2[2] if u > 0.4 else k1[2],
                "tear_progress": k1[3] + (k2[3] - k1[3]) * u,
                "gesture": k2[4] if u > 0.4 else k1[4],
                "head_accent": k1[5] + (k2[5] - k1[5]) * u,
                "chest_sink": k1[6] + (k2[6] - k1[6]) * u,
                "torso_lean": 1.0
            }
        else:
            return {
                "emotion_intensity": intensity,
                "gesture": k2[2] if u > 0.3 else k1[2],
                "head_accent": k1[3] + (k2[3] - k1[3]) * u,
                "torso_lean": (k1[4] + (k2[4] - k1[4]) * u) if len(k1) > 4 else 0.0,
                "tear_state": "none",
                "tear_progress": 0.0,
                "chest_sink": 0.0
            }

class ObjectManager(GenericPropManager):
    """
    Manages interactive props on stage dynamically via GenericPropManager:
    - Coordinates, alpha, glow, held status, character attachment via hand IK
    - Fully backwards-compatible with legacy .objects dict and methods.
    """
    def __init__(self, props_dir: str = None, prop_configs: list = None):
        super().__init__(props_dir=props_dir)
        # Load magic_stove manifest if available, fallback to baseline registration
        if "magic_stove" not in self.props:
            loaded = self.load_prop_by_name("magic_stove")
            if not loaded:
                self.register_prop(
                    prop_id="magic_stove",
                    asset_name="magic_stove.png",
                    x=840,
                    y=730,
                    scale=0.95,
                    glow_color=(255, 215, 60),
                    attachment_offsets={"waist_carry": {"right": (185, 245), "left": (100, 245)}}
                )
        if prop_configs:
            for cfg in prop_configs:
                self.load_prop_config(cfg)
        
    def reveal_object(self, obj_id: str, progress: float):
        self.reveal_prop(obj_id, progress)

class PerformanceDirector:
    """
    Master Performance Director unifying timelines, listener reactions,
    audio-stress beats, and hand IK gestures.
    """
    def __init__(self):
        self.listener_controller = ListenerReactionController()
        self.object_manager = ObjectManager()
        self.audio_analyzer = AudioPerformanceAnalyzer()
        self.secondary_oscillators = {}
        
    def plan_performance(self, turn: dict, actors: dict, fps: int, turn_frames: int,
                          scene_context: dict = None) -> dict:
        speaker = turn.get("character", "narrator").lower()
        text = turn.get("text", "")
        raw_action = turn.get("action", "speaking").lower()
        emotion = turn.get("emotion", "neutral").lower()
        camera_tag = turn.get("camera", "auto").lower()
        
        is_movement = any(raw_action.startswith(p) for p in ["walk", "enter", "exit", "move", "run", "leave"])

        # Infer emotion from action and Telugu text cues if not explicitly specified
        if emotion == "neutral":
            if raw_action in ["angry", "scold", "peak_anger", "irritation"] or "కోపం" in text or "కోపంగా" in text:
                emotion = "angry"
            elif raw_action in ["cry", "weep", "crying", "intense_crying"] or "కన్నీళ్లు" in text or "ఏడుస్తూ" in text or "బాధ" in text:
                emotion = "cry"
            elif raw_action in ["sad", "sadness", "worry", "distress"]:
                emotion = "sad"
            elif raw_action in ["shiver", "cold"] or (( "చలి" in text or "గడ్డకట్టే" in text ) and not is_movement):
                emotion = "shiver"
            elif raw_action in ["fear", "cower", "scared", "tremble"] or "భయం" in text:
                emotion = "fear"
            elif raw_action in ["surprise", "shock", "surprised"] or "ఆశ్చర్యం" in text or "బాబోయ్" in text:
                emotion = "surprise"
            elif raw_action in ["relief", "sigh"]:
                emotion = "relief"
            elif raw_action in ["joy", "happy", "excited", "cheerful"] or "సంతోషం" in text:
                emotion = "joy"
            elif raw_action in ["pray", "namaste", "reverence", "devotion", "bow"] or "నమస్కారం" in text:
                emotion = "reverence"

        # Select timeline ID (movement actions always preserve movement performance type)
        if is_movement:
            timeline_id = "standard_timeline"
            perf_type = raw_action
        elif emotion in ["cry", "weep", "crying", "intense_crying"] or "కన్నీళ్లు" in text or "ఏడుస్తూ" in text or raw_action in ["cry", "weep"]:
            timeline_id = "cry_timeline"
            perf_type = "cry_sequence"
        elif emotion in ["angry", "scold", "irritation", "peak_anger"] or "కోపంగా" in text or raw_action in ["angry", "scold"]:
            timeline_id = "scold_timeline"
            perf_type = "scold_sequence"
        elif raw_action in ["pray", "namaste"]:
            timeline_id = "pray_timeline"
            perf_type = "pray_sequence"
        elif raw_action in ["cook", "use_stove"]:
            timeline_id = "cook_timeline"
            perf_type = "cook_sequence"
        elif emotion == "shiver" or raw_action in ["shiver", "cold"]:
            timeline_id = "shiver_timeline"
            perf_type = "shiver"
        else:
            timeline_id = "standard_timeline"
            perf_type = raw_action
            
        # Camera shot selection
        if camera_tag != "auto":
            camera_shot = camera_tag
        elif perf_type == "cry_sequence":
            camera_shot = "speaker_closeup"
        elif perf_type == "scold_sequence":
            camera_shot = "speaker_closeup"
        elif len(actors) >= 2:
            camera_shot = "medium_two_shot"
        else:
            camera_shot = "medium_character"
            
        return {
            "speaker": speaker,
            "timeline_id": timeline_id,
            "performance_type": perf_type,
            "emotion": emotion,
            "camera_shot": camera_shot,
            "turn_frames": turn_frames
        }
        
    def evaluate_performance_frame(self, timeline_id: str, frame_idx: int,
                                   fps: int, audio_stress: float = 0.0,
                                   is_strike_beat: bool = False) -> dict:
        elapsed_sec = frame_idx / float(max(1, fps))
        eval_data = PerformanceTimeline.evaluate(timeline_id, elapsed_sec)
        
        # Audio stress beat accentuates head nod and lean
        stress_head = (audio_stress * 4.0) if is_strike_beat else (audio_stress * 1.5)
        head_accent = eval_data.get("head_accent", 0.0) + stress_head
        
        return {
            "emotion_intensity": eval_data.get("emotion_intensity", 0.5),
            "gesture": eval_data.get("gesture", "idle"),
            "tear_state": eval_data.get("tear_state", "none"),
            "tear_progress": eval_data.get("tear_progress", 0.0),
            "head_accent": head_accent,
            "torso_lean": eval_data.get("torso_lean", 0.0),
            "chest_sink": eval_data.get("chest_sink", 0.0)
        }

    def evaluate_acting_frame(self, performance_type: str, frame_idx: int, total_frames: int,
                              is_speaker: bool, walk_state: dict = None,
                              audio_stress: float = 0.0, is_strike_beat: bool = False,
                              char_id: str = None) -> dict:
        from .animation_engine import GestureController
        g_state = GestureController.evaluate(performance_type, frame_idx, total_frames, is_speaker, char_id=char_id)

        if "cry" in performance_type or "weep" in performance_type:
            tl_id = "cry_timeline"
        elif "scold" in performance_type or "angry" in performance_type or "point" in performance_type or "irritation" in performance_type:
            tl_id = "scold_timeline"
        elif "pray" in performance_type or "namaste" in performance_type:
            tl_id = "pray_timeline"
        elif "cook" in performance_type or "stir" in performance_type:
            tl_id = "cook_timeline"
        else:
            tl_id = "standard_timeline"
            
        data = PerformanceTimeline.evaluate(tl_id, frame_idx / 24.0)
        char_seed = (abs(hash(char_id)) % 13) * 0.45 if char_id else 0.0
        bob = math.sin((frame_idx * 0.45) + char_seed) * 3.0 if is_speaker else math.sin((frame_idx * 0.2) + char_seed) * 1.5
        
        # Audio-driven gesture pulse on stressed syllables and speech emphasis beats
        arm_pulse = (audio_stress * 7.0 + (5.0 if is_strike_beat else 0.0)) if is_speaker else 0.0
        base_r = g_state.get("right_arm_rot", 0.0)
        base_l = g_state.get("left_arm_rot", 0.0)
        if base_r < -2.0:
            final_r = base_r - arm_pulse
            final_l = base_l + arm_pulse * 0.4
        elif base_l > 2.0:
            final_l = base_l + arm_pulse
            final_r = base_r - arm_pulse * 0.4
        elif is_speaker:
            final_r = base_r - arm_pulse
            final_l = base_l + arm_pulse * 0.5
        else:
            final_r = base_r
            final_l = base_l

        return {
            "head_rot": g_state.get("head_rot", 0.0) + data.get("head_accent", 0.0),
            "left_arm_rot": final_l,
            "right_arm_rot": final_r,
            "jitter_x": g_state.get("jitter_x", 0.0),
            "jitter_y": g_state.get("jitter_y", 0.0),
            "bob_y": g_state.get("bob_y", 0.0) + bob,
            "torso_roll": g_state.get("torso_roll", 0.0) + data.get("torso_lean", 0.0),
            "scale_x": g_state.get("scale_x", 1.0),
            "scale_y": g_state.get("scale_y", 1.0)
        }
