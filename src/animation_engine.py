"""
2D Animation Engine for Telugu Animated Stories
Provides procedural 2D puppet kinematics, true 4-phase walk cycle,
anatomical articulation (Head, Torso, Arms, Legs/Saree), orientation control (3/4, front, side, back),
character gestures, idle breathing, expressions, and secondary cloth/hair motion.
"""

import os
import sys
import math
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter

from .face_engine import FacePerformanceEngine
from .arm_ik import ArmGestureRenderer
from .character_registry import CharacterRegistry

# Character anatomical anchor definitions (standard 600x900 canvas)
NECK_PIVOT = (300, 260)
HIP_PIVOT = (300, 520)
LEFT_SHOULDER = (200, 290)
RIGHT_SHOULDER = (400, 290)
GROUND_PIVOT = (300, 870)

class WalkCycleController:
    """
    Procedural 4-phase cartoon walk cycle:
    1. Contact 1 (phi = 0.0): Left foot heel strike forward, Right foot back, zero vertical drop
    2. Recoil / Down 1 (phi = 0.125): Impact absorbed, knee flexes, hip drops (-12px)
    3. Passing 1 (phi = 0.25): Right leg swings past planted left leg, torso rising
    4. High Point / Up 1 (phi = 0.375): Push off ball of foot, torso peaks (+6px)
    5. Contact 2 (phi = 0.5): Right foot heel strike forward, Left foot back
    6. Recoil / Down 2 (phi = 0.625)
    7. Passing 2 (phi = 0.75)
    8. High Point / Up 2 (phi = 0.875)
    """
    CADENCE_PROFILES = {
        "atha": {"speed": 0.94, "bob": 1.12, "sway": 1.10, "stride": 0.95},
        "kodalu": {"speed": 1.05, "bob": 0.95, "sway": 0.95, "stride": 1.05},
        "gent": {"speed": 1.00, "bob": 1.00, "sway": 1.00, "stride": 1.05},
        "kid": {"speed": 1.25, "bob": 1.25, "sway": 1.20, "stride": 0.85},
        "maharshi": {"speed": 0.88, "bob": 0.85, "sway": 0.85, "stride": 0.92},
        "kanthamma": {"speed": 0.96, "bob": 1.08, "sway": 1.05, "stride": 0.98},
        "padma": {"speed": 1.02, "bob": 0.98, "sway": 0.98, "stride": 1.02},
        "saroja": {"speed": 0.97, "bob": 1.04, "sway": 1.02, "stride": 1.00},
        "father_in_law": {"speed": 0.90, "bob": 1.10, "sway": 1.12, "stride": 0.92}
    }

    def __init__(self, step_duration_s: float = 0.38, fps: int = 24):
        self.step_frames = max(4, int(step_duration_s * fps))
        self.cycle_frames = self.step_frames * 2
        self.fps = fps
        
    @staticmethod
    def ease_in_out(t: float) -> float:
        """Smooth cubic hermite ease-in/ease-out: 3t^2 - 2t^3."""
        t = max(0.0, min(1.0, t))
        return 3.0 * (t ** 2) - 2.0 * (t ** 3)
        
    def evaluate(self, frame_idx: int, walk_type: str = "walk_right",
                 total_walk_frames: int = None, is_stopping: bool = False,
                 char_id: str = None, travel_distance: float = None) -> dict:
        cid = char_id.lower() if char_id else ""
        prof = self.CADENCE_PROFILES.get(cid, {"speed": 1.0, "bob": 1.0, "sway": 1.0, "stride": 1.0})

        # Adobe Animate Speed Principle: Synchronize gait frequency to travel distance
        if travel_distance is not None and abs(travel_distance) > 50 and total_walk_frames and total_walk_frames > 0:
            n_cycles = max(1.0, round(abs(travel_distance) / 160.0))
            eff_cycle_frames = float(total_walk_frames) / n_cycles
        else:
            eff_cycle_frames = self.cycle_frames / prof["speed"]

        phase = (frame_idx / float(eff_cycle_frames)) * (2.0 * math.pi)
        
        # Determine dampening if coming to a stop (foot planting) or starting from rest
        dampen = 1.0
        is_exit = any(k in walk_type for k in ["exit", "walk_out", "leave"])
        is_entrance = any(k in walk_type for k in ["walk_in", "enter", "appear"])

        remaining = 999
        if total_walk_frames and total_walk_frames > 0:
            # Start ease-in damping only for stationary starts (NOT for characters walking in from off-screen)
            if frame_idx < 8 and not is_entrance:
                t_start = max(0.0, min(1.0, frame_idx / 8.0))
                dampen *= (3.0 * (t_start ** 2) - 2.0 * (t_start ** 3))
            # Stop ease-out damping only for stopping in-scene (NOT for exit walks off-screen)
            remaining = total_walk_frames - frame_idx
            if remaining < 10 and not is_exit:
                dampen *= max(0.0, remaining / 10.0)
                
        # 1. Vertical Pelvic Bob: Richard Williams / Adobe Animate 4-phase walk cycle
        # Contact (0, pi): neutral (0)
        # Down (pi/4, 5pi/4): lowest point, weight cushion (+bob)
        # Passing (pi/2, 3pi/2): neutral (0)
        # High point / Up (3pi/4, 7pi/4): highest push-off (-bob)
        y_bob = (-math.sin(2.0 * phase) * (14.0 * prof["bob"])) * dampen
        
        # 2. Torso Pitch / Sway Roll with forward walk momentum lean
        torso_roll = (math.sin(phase) * (3.8 * prof["sway"])) * dampen
        
        # 3. Head Counter-Stabilization (maintains stable eye line)
        head_tilt = (-torso_roll * 0.70 + math.sin(2.0 * phase) * 1.2) * dampen
        
        # 4. Alternating Arm Swing (opposite to leg stride, clear swing arc)
        left_arm_angle = (-math.sin(phase) * (26.0 * prof["stride"])) * dampen
        right_arm_angle = (math.sin(phase) * (26.0 * prof["stride"])) * dampen
        
        # 5. Lower Saree / Leg Stride Shear & Ripple
        stride_shear = (math.sin(phase) * (30.0 * prof["stride"])) * dampen
        saree_wave = (math.sin(phase - 0.4) * 8.0) * dampen
        
        # 6. Foot contact heights (clean parabolic lift during swing phase, 0 during stance)
        # Left foot stance in [0, pi], swing in [pi, 2pi]
        # Right foot swing in [0, pi], stance in [pi, 2pi]
        left_foot_lift = max(0.0, -math.sin(phase)) * 20.0 * dampen
        right_foot_lift = max(0.0, math.sin(phase)) * 20.0 * dampen
        
        # 7. Natural settling weight shift when decelerating to a stop
        settle_shift_x = 0.0
        if total_walk_frames and remaining < 10 and not is_exit:
            settle_shift_x = math.sin(((10 - remaining) / 10.0) * math.pi) * 2.5
        
        # 8. Perspective scale modulation (for toward/away walks)
        scale_mod = 1.0
        if walk_type == "walk_toward_camera" and total_walk_frames:
            prog = min(1.0, frame_idx / float(total_walk_frames))
            scale_mod = 1.0 + prog * 0.20
        elif walk_type == "walk_away" and total_walk_frames:
            prog = min(1.0, frame_idx / float(total_walk_frames))
            scale_mod = 1.0 - prog * 0.20
            
        return {
            "y_bob": y_bob,
            "torso_roll": torso_roll,
            "head_tilt": head_tilt,
            "left_arm_angle": left_arm_angle,
            "right_arm_angle": right_arm_angle,
            "stride_shear": stride_shear,
            "saree_wave": saree_wave,
            "left_foot_lift": left_foot_lift,
            "right_foot_lift": right_foot_lift,
            "scale_mod": scale_mod,
            "phase": phase,
            "dampen": dampen,
            "settle_shift_x": settle_shift_x
        }

class IdleController:
    """Subtle realistic idle secondary motion: breathing, weight shifting, head drift."""
    def __init__(self, seed: int = 0, char_id: str = None):
        char_seed = (abs(hash(char_id)) % 11) * 0.65 if char_id else (seed * 1.3)
        self.phase_offset = char_seed
        self.breath_rate = 0.38 + ((abs(hash(char_id or str(seed))) % 5) * 0.025)
        self.sway_rate = 0.22 + ((abs(hash(char_id or str(seed))) % 7) * 0.02)
        
    def evaluate(self, frame_idx: int) -> dict:
        t = frame_idx * 0.08 + self.phase_offset
        # Gentle diaphragm breathing (individualized rate)
        breath_scale_y = 1.0 + math.sin(t * self.breath_rate) * 0.014
        breath_scale_x = 1.0 - math.sin(t * self.breath_rate) * 0.005
        # Subtle posture sway & natural weight shift
        sway_x = math.sin(t * self.sway_rate) * 1.6
        head_idle_nod = math.sin(t * (self.breath_rate * 1.25)) * 1.2
        
        return {
            "scale_x": breath_scale_x,
            "scale_y": breath_scale_y,
            "sway_x": sway_x,
            "head_nod": head_idle_nod
        }

class GestureController:
    """
    Generates kinematic transformations for the complete action library:
    idle, walk, talk, listen, turn, look_left, look_right, look_at, gesture, point,
    angry, sad, happy, surprised, cry, think, sit, stand, bend, pick_up, put_down,
    cook, eat, sleep, wake, knock_door, open_door, close_door, carry, pray,
    meditate, warm_hands, light_fire, use_stove, hold_object, give_object, receive_object,
    leave, enter.
    """
    @staticmethod
    def evaluate(action: str, frame_idx: int, total_frames: int, is_speaker: bool, char_id: str = None) -> dict:
        action = action.lower() if action else "idle"
        act = action.replace("_sequence", "").replace("_timeline", "").strip()
        prog = min(1.0, frame_idx / max(1, total_frames))
        char_seed = (abs(hash(char_id)) % 13) * 0.45 if char_id else 0.0
        
        head_rot = 0.0
        left_arm_rot = 0.0
        right_arm_rot = 0.0
        body_jitter_x = 0.0
        body_jitter_y = 0.0
        bob_y = 0.0
        torso_roll = 0.0
        scale_x = 1.0
        scale_y = 1.0
        sit_progress = 0.0
        
        # 1. Emotional & Reactive States
        if act == "shiver":
            # Multi-frequency high-amplitude winter cold shivering tremor
            body_jitter_x = math.sin(frame_idx * 2.1) * 3.5 + math.sin(frame_idx * 4.7) * 2.5
            body_jitter_y = math.cos(frame_idx * 2.3) * 2.5 + math.sin(frame_idx * 5.1) * 1.5
            head_rot = math.sin(frame_idx * 3.8) * 3.5 + math.cos(frame_idx * 1.5) * 2.0
            torso_roll = math.sin(frame_idx * 3.2) * 2.8
            left_arm_rot = 10.0 + math.sin(frame_idx * 4.1) * 6.0
            right_arm_rot = -10.0 - math.cos(frame_idx * 4.3) * 6.0
            bob_y = math.sin(frame_idx * 2.7) * 2.0
            
        elif act in ["angry", "scold", "anger"]:
            # Aggressive forward lean, scolding hand gesture
            head_rot = 5.0 + math.sin(frame_idx * 0.6) * 4.0
            bob_y = math.sin(frame_idx * 0.5) * 4.0
            right_arm_rot = -26.0 + math.sin(frame_idx * 0.45) * 14.0
            left_arm_rot = 14.0 + math.sin(frame_idx * 0.35) * 8.0
            torso_roll = 3.5
            
        elif act in ["cry", "weep", "crying", "intense_crying"]:
            # Head bowed deeply, weeping rhythmic shoulder heaving
            head_rot = 10.0
            bob_y = math.sin(frame_idx * 0.8) * 3.5
            left_arm_rot = 18.0
            right_arm_rot = -25.0
            body_jitter_y = math.sin(frame_idx * 1.5) * 1.5
            
        elif act in ["sad", "sadness", "worry", "distress"]:
            # Downcast head and slumped posture
            head_rot = 7.0
            bob_y = 4.0
            torso_roll = 1.5
            left_arm_rot = 8.0
            right_arm_rot = -8.0

        elif act in ["fear", "cower", "scared", "tremble"]:
            # Defensive trembling, crouching, arms guarded
            body_jitter_x = math.sin(frame_idx * 1.5) * 2.5
            body_jitter_y = math.cos(frame_idx * 1.8) * 1.5
            head_rot = -4.0 + math.sin(frame_idx * 0.8) * 2.0
            bob_y = 6.0
            left_arm_rot = 16.0
            right_arm_rot = -16.0
            scale_y = 0.97

        elif act in ["relief", "sigh"]:
            # Exhaling release, shoulders dropping, gentle settling
            ease = min(1.0, frame_idx / 15.0)
            bob_y = 3.0 * ease
            head_rot = 2.0 * math.sin(prog * math.pi)
            torso_roll = -1.0 * ease
            left_arm_rot = 4.0
            right_arm_rot = -4.0
            
        elif act in ["happy", "joy", "excited", "cheerful"]:
            # Upright energetic bounce and head tilt
            head_rot = -3.0 + math.sin(frame_idx * 0.4) * 3.0
            bob_y = -math.sin(frame_idx * 0.6) * 5.0
            right_arm_rot = -20.0 + math.sin(frame_idx * 0.5) * 10.0
            left_arm_rot = 15.0
            
        elif act in ["surprised", "surprise", "shock"]:
            # Sudden vertical pop and head tilt
            ease_in = min(1.0, frame_idx / 8.0)
            bob_y = -9.0 * ease_in
            head_rot = -5.0 * ease_in
            left_arm_rot = 18.0 * ease_in
            right_arm_rot = -18.0 * ease_in
            
        elif action in ["think", "contemplate"]:
            # Hand touching chin, tilted head
            head_rot = -6.0
            right_arm_rot = -42.0
            bob_y = 1.0
            
        # 2. Environmental & Household Actions
        elif act in ["cook", "stir", "use_stove"]:
            # Tending the chulha stove, rhythmic stirring
            bob_y = math.sin(frame_idx * 0.35) * 5.0
            right_arm_rot = math.sin(frame_idx * 0.4) * 18.0
            head_rot = 4.0
            
        elif act in ["warm_hands"]:
            # Rubbing hands together over campfire/heater
            bob_y = math.sin(frame_idx * 0.3) * 3.0
            right_arm_rot = -26.0 + math.sin(frame_idx * 1.2) * 5.0
            left_arm_rot = 26.0 - math.sin(frame_idx * 1.2) * 5.0
            head_rot = 4.0
            
        elif act in ["light_fire"]:
            # Leaning down towards stove/hearth
            bob_y = 12.0
            torso_roll = 5.0
            head_rot = 8.0
            right_arm_rot = -35.0
            
        elif act in ["eat"]:
            # Hand to mouth rhythmic motion
            right_arm_rot = -35.0 + math.sin(frame_idx * 0.4) * 15.0
            head_rot = 3.0 + math.sin(frame_idx * 0.4) * 2.5
            bob_y = 2.0
            
        elif act in ["sleep"]:
            # Resting down, head tilted
            head_rot = 14.0
            bob_y = 16.0
            torso_roll = 8.0
            scale_y = 0.95
            
        elif act in ["wake"]:
            # Rising upright
            ease = min(1.0, frame_idx / 16.0)
            head_rot = 14.0 * (1.0 - ease)
            bob_y = 16.0 * (1.0 - ease)
            
        elif act in ["knock_door"]:
            # Rhythmic knocking on wooden door
            right_arm_rot = -55.0 + math.sin(frame_idx * 1.6) * 10.0
            head_rot = 2.0
            
        elif act in ["reach", "extend_hand", "open_door", "close_door"]:
            # Reaching arm forward/upward with torso lean
            ease = math.sin(prog * math.pi)
            right_arm_rot = -38.0 * ease
            left_arm_rot = 12.0 * ease
            torso_roll = 2.5 * ease
            bob_y = 2.0 * ease
            head_rot = 2.0 * ease
            
        elif act in ["carry", "hold_object"]:
            # Carrying stove / vessel firmly clamped at waist
            right_arm_rot = -32.0
            left_arm_rot = 32.0
            bob_y = 2.0
            
        elif act in ["give_object"]:
            # Offering object forward
            ease = math.sin(prog * math.pi)
            right_arm_rot = -35.0 * ease
            left_arm_rot = 25.0 * ease
            
        elif act in ["receive_object", "pick_up"]:
            # Cupped hands accepting
            ease = math.sin(prog * math.pi)
            right_arm_rot = -28.0 * ease
            left_arm_rot = 28.0 * ease
            bob_y = 6.0 * ease
            
        elif act in ["pray", "namaste", "reverence", "devotion", "bow"]:
            # Folded hands at chest, respectful head bow
            head_rot = 5.0
            right_arm_rot = -20.0
            left_arm_rot = 20.0
            bob_y = 2.0
            
        elif act in ["meditate"]:
            # Serene steady seated meditation
            head_rot = 0.0
            bob_y = math.sin(frame_idx * 0.15) * 1.5
            torso_roll = 0.0
            
        elif act in ["bend"]:
            bob_y = 18.0
            torso_roll = 10.0
            head_rot = 8.0
            
        elif act in ["sit"]:
            # Real 2D Cutout Sitting: Deep pelvic descent, torso leans forward for balance, arms fold onto lap
            ease = min(1.0, frame_idx / max(1, min(18, total_frames)))
            smooth_ease = 3.0 * (ease ** 2) - 2.0 * (ease ** 3)
            bob_y = 120.0 * smooth_ease
            torso_roll = 12.0 * smooth_ease
            head_rot = -5.0 * smooth_ease
            left_arm_rot = 26.0 * smooth_ease
            right_arm_rot = -26.0 * smooth_ease
            sit_progress = smooth_ease
            
        elif act in ["stand"]:
            # Real 2D Cutout Standing: Anticipation forward lean, push-off, rising ascent, upright settling
            t = min(1.0, frame_idx / max(1, min(18, total_frames)))
            if t < 0.25:
                ant_t = t / 0.25
                ant_ease = math.sin(ant_t * math.pi)
                bob_y = 120.0 + 6.0 * ant_ease
                torso_roll = 12.0 + 4.0 * ant_ease
                head_rot = -5.0 - 2.0 * ant_ease
                left_arm_rot = 26.0 + 6.0 * ant_ease
                right_arm_rot = -26.0 - 6.0 * ant_ease
                sit_progress = 1.0
            else:
                rise_t = (t - 0.25) / 0.75
                rise_ease = 3.0 * (rise_t ** 2) - 2.0 * (rise_t ** 3)
                bob_y = 120.0 * (1.0 - rise_ease)
                torso_roll = 12.0 * (1.0 - rise_ease)
                head_rot = -5.0 * (1.0 - rise_ease)
                left_arm_rot = 26.0 * (1.0 - rise_ease)
                right_arm_rot = -26.0 * (1.0 - rise_ease)
                sit_progress = 1.0 - rise_ease
            
        elif act in ["idle"]:
            # Resting calm idle posture
            head_rot = math.sin(frame_idx * 0.12 + char_seed) * 1.5
            bob_y = math.sin(frame_idx * 0.15 + char_seed) * 1.0
            left_arm_rot = 0.0
            right_arm_rot = 0.0
            sit_progress = 0.0
            
        elif act in ["point", "accuse"]:
            ease = math.sin(prog * math.pi) if prog < 0.9 else 0.0
            right_arm_rot = -38.0 * ease + math.sin(frame_idx * 0.5) * 8.0
            left_arm_rot = 12.0 * ease
            head_rot = 5.0 * ease
            torso_roll = 4.0 * ease
            sit_progress = 0.0
            
        elif act in ["turn", "turn_around", "turn_left", "turn_right"]:
            # 3-Stage Cutout Breakdown Turn: Anticipation -> Breakdown Profile Silhouette -> Settle Recovery
            turn_t = min(1.0, frame_idx / max(1, min(16, total_frames)))
            turn_compression = math.sin(turn_t * math.pi)
            scale_x = 1.0 - 0.72 * turn_compression  # Compresses down to 0.28 at midpoint
            scale_y = 1.0 + 0.04 * turn_compression  # 2D volume preservation
            head_rot = -12.0 * turn_compression
            torso_roll = -4.0 * turn_compression
            sit_progress = 0.0
            
        elif act in ["look_left"]:
            head_rot = -8.0
            sit_progress = 0.0
            
        elif act in ["look_right"]:
            head_rot = 8.0
            sit_progress = 0.0
            
        elif act in ["gesture", "talk", "speaking"]:
            # Communicative character acting: speech cadence, head accent nod, expressive gesture
            t_spk = frame_idx * 0.45 + char_seed
            head_rot = math.sin(t_spk) * 3.8 + math.cos(t_spk * 0.5) * 1.6
            bob_y = math.sin(t_spk) * 2.8
            gesture_phase = math.sin(frame_idx * 0.28 + char_seed)
            right_arm_rot = -24.0 + gesture_phase * 16.0
            left_arm_rot = 14.0 + math.cos(frame_idx * 0.22 + char_seed) * 8.0
            torso_roll = 1.8 + math.sin(frame_idx * 0.25 + char_seed) * 1.5
            sit_progress = 0.0
            
        elif is_speaker:
            # Natural talking articulation
            t_spk = frame_idx * 0.45 + char_seed
            head_rot = math.sin(t_spk) * 3.6 + math.sin(t_spk * 0.3) * 1.2
            bob_y = math.sin(t_spk) * 2.5
            right_arm_rot = -20.0 + math.sin(frame_idx * 0.3 + char_seed) * 12.0
            left_arm_rot = 12.0 + math.cos(frame_idx * 0.24 + char_seed) * 8.0
            torso_roll = math.sin(frame_idx * 0.25 + char_seed) * 1.8
            sit_progress = 0.0
            
        else:
            # Alive listener: subtle attentive nodding with character phase
            listen_cycle = 48
            listen_frame = (frame_idx + int(char_seed * 20)) % listen_cycle
            sit_progress = 0.0
            if listen_frame < 14:
                head_rot = math.sin((listen_frame / 14.0) * math.pi) * 3.0
                
        return {
            "head_rot": head_rot,
            "left_arm_rot": left_arm_rot,
            "right_arm_rot": right_arm_rot,
            "jitter_x": body_jitter_x,
            "jitter_y": body_jitter_y,
            "bob_y": bob_y,
            "torso_roll": torso_roll,
            "scale_x": scale_x,
            "scale_y": scale_y,
            "sit_progress": sit_progress
        }

class PuppetRenderer:
    """
    Composes full animated character by applying anatomical transforms:
    - FACE Channel: Localized mask deformation (Brows, Eyes, Mouth, Tears)
    - BODY Channel: Torso lean/puff/sink, Head rotation/accent, Lower Saree stride shear
    - HANDS Channel: 2D Arm IK articulation (Pointing jab, Wipe tears, Pray, Cook)
    - Orientation control (front, 3/4_left, 3/4_right, side_left, side_right, back)
    """
    face_engine = FacePerformanceEngine(max_displacement=22.0)
    arm_renderer = ArmGestureRenderer()

    @staticmethod
    def render_puppet(parts: dict, mouth_cue: str, is_blinking: bool,
                      char_id: str = "kodalu",
                      emotion: str = "neutral",
                      emotion_intensity: float = 0.5,
                      audio_stress: float = 0.0,
                      tear_state: str = "none",
                      tear_progress: float = 0.0,
                      gesture_pose: str = "idle",
                      frame_idx: int = 0,
                      chest_sink: float = 0.0,
                      walk_state: dict = None, idle_state: dict = None,
                      gesture_state: dict = None, orientation: str = "three_quarter_left",
                      scale: float = 1.0) -> Image.Image:
                      
        if gesture_pose == "cook" and parts.get("cook") is not None:
            if "left" in orientation and parts.get("cook_left"):
                base = parts["cook_left"].copy()
            elif parts.get("cook_right"):
                base = parts["cook_right"].copy()
            else:
                base = parts["cook"].copy()
        elif char_id == "kodalu":
            rig_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "characters", "kodalu", "rig"))
            clean_file = os.path.join(rig_dir, "torso_head_clean.png")
            if os.path.exists(clean_file):
                base = Image.open(clean_file).convert("RGBA")
            elif parts.get("base_clean") is not None:
                base = parts["base_clean"].copy()
            else:
                base = parts["base"].copy()
        elif parts.get("base_clean") is not None and ((mouth_cue and mouth_cue != "mouth_closed") or emotion in ["sad", "cry", "weep", "angry", "scold"]):
            base = parts["base_clean"].copy()
        else:
            base = parts["base"].copy()
        is_back = (orientation == "back")
        
        # 1. FACE CHANNEL: Blink, Eyes Open, Localized Safe Deformation, Organic Tears
        lm = PuppetRenderer.face_engine.get_landmarks(char_id)
        mc = lm.get("mouth_c", (300, 185))
        xc = int(mc[0]) # character horizontal anatomical center
        eye_y = lm.get("eye_l", (xc - 35, 140))[1]
        ys = int(eye_y + 145) # shoulder horizontal axis (~285px)
        
        left_shoulder = (int(xc - 75), ys)
        right_shoulder = (int(xc + 75), ys)
        neck_pivot = (int(xc), int(ys - 25))
        hip_pivot = (int(xc), int(ys + 235))

        if not is_back:
            eye_l = lm.get("eye_l", (xc - 35, 140))
            eye_r = lm.get("eye_r", (xc + 35, 140))
            target_cy = (eye_l[1] + eye_r[1]) / 2.0
            target_cx = (eye_l[0] + eye_r[0]) / 2.0

            # Composite eyes layer: blink when blinking (base puppet illustration already has open eyes)
            if is_blinking and parts.get("eyes_blink"):
                eye_img = parts["eyes_blink"]
                if eye_img.size == base.size:
                    base.alpha_composite(eye_img)
                else:
                    bw, bh = eye_img.size
                    dest_x = int(target_cx - bw / 2.0)
                    dest_y = int(target_cy - bh / 2.0)
                    base.alpha_composite(eye_img, dest=(dest_x, dest_y))
                    
            # Apply safe localized deformation (Brows, Eyelids, Mouth corners & multi-axis viseme articulation)
            # Active for all expressive states as well as speaking phonemes
            if emotion in ["angry", "scold", "irritation", "peak_anger", "anger", "sad", "sadness", "cry", "weep", "crying", "intense_crying", "cower", "fear", "shiver", "cold", "happy", "joy", "relief", "reverence", "surprise", "surprised", "shock"] or audio_stress > 0.05 or (mouth_cue and mouth_cue != "mouth_closed"):
                base = PuppetRenderer.face_engine.deform_face(
                    base_img=base,
                    char_id=char_id,
                    emotion=emotion,
                    intensity=emotion_intensity,
                    audio_stress=audio_stress,
                    frame_idx=frame_idx,
                    mouth_cue=mouth_cue
                )
                
            # Apply organic curved tear trajectory
            if tear_state != "none":
                base = PuppetRenderer.face_engine.render_organic_tears(
                    canvas=base,
                    char_id=char_id,
                    tear_state=tear_state,
                    progress=tear_progress,
                    intensity=emotion_intensity
                )

        # Clean mouth rendering: For Kodalu, feather skin patch over the mouth region
        # to erase the baked-in open smile, then composite clean closed mouth or non-empty viseme
        if not is_back:
            m_cue_str = str(mouth_cue).lower().strip() if mouth_cue else "mouth_closed"
            if char_id == "kodalu":
                arr_b = np.array(base)
                hb, wb, _ = arr_b.shape
                skin_sample = arr_b[150, 265, :3].astype(np.float32)
                y_c, x_c = np.ogrid[:hb, :wb]
                dist_m = ((x_c - 265.0) / 28.0) ** 2 + ((y_c - 168.0) / 13.0) ** 2
                mask_m = np.clip(1.0 - dist_m, 0.0, 1.0).astype(np.float32)
                mask_m = (3.0 * mask_m**2 - 2.0 * mask_m**3)[:, :, None]
                skin_p = np.zeros_like(arr_b[:, :, :3], dtype=np.float32)
                skin_p[:, :] = skin_sample
                arr_b[:, :, :3] = (arr_b[:, :, :3].astype(np.float32) * (1.0 - mask_m) + skin_p * mask_m).astype(np.uint8)
                base = Image.fromarray(arr_b)
                
            mouth_img = None
            if m_cue_str != "mouth_closed" and parts.get("mouths"):
                mouth_img = parts["mouths"].get(m_cue_str)
                if not mouth_img and parts.get(m_cue_str):
                    mouth_img = parts[m_cue_str]
            elif m_cue_str == "mouth_closed" and parts.get("mouths"):
                if emotion in ["sad", "cry", "weep", "cower", "fear"] and parts["mouths"].get("mouth_sad"):
                    mouth_img = parts["mouths"]["mouth_sad"]
                elif emotion in ["angry", "scold"] and parts["mouths"].get("mouth_angry"):
                    mouth_img = parts["mouths"]["mouth_angry"]
                elif parts["mouths"].get("mouth_closed") and np.array(parts["mouths"]["mouth_closed"])[:, :, 3].max() > 0:
                    mouth_img = parts["mouths"]["mouth_closed"]

            if mouth_img is not None and np.array(mouth_img)[:, :, 3].max() > 0:
                if mouth_img.size == base.size:
                    base.alpha_composite(mouth_img)
                else:
                    arr_m = np.array(mouth_img)
                    alpha_m = arr_m[:, :, 3]
                    pts = np.argwhere(alpha_m > 10)
                    if len(pts) > 0:
                        y0, x0 = pts.min(axis=0)
                        y1, x1 = pts.max(axis=0)
                        cx_m = (x0 + x1) / 2.0
                        cy_m = (y0 + y1) / 2.0
                        dx_m = int(round(mc[0] - cx_m))
                        dy_m = int(round(mc[1] - cy_m))
                        w_b, h_b = base.size
                        shifted_m = Image.new("RGBA", (w_b, h_b), (0, 0, 0, 0))
                        shifted_m.paste(mouth_img, (dx_m, dy_m), mouth_img)
                        base.alpha_composite(shifted_m)
            elif char_id == "kodalu" and m_cue_str == "mouth_closed":
                # High-fidelity natural closed lip seam on clean skin
                draw_m = ImageDraw.Draw(base)
                cx_k, cy_k = 265, 168
                seam_col = (95, 30, 28)
                lip_col = (168, 62, 58)
                if emotion in ["sad", "cry", "weep", "cower"]:
                    draw_m.arc([cx_k - 16, cy_k, cx_k + 16, cy_k + 12], start=200, end=340, fill=seam_col, width=2)
                else:
                    draw_m.line([(cx_k - 15, cy_k), (cx_k + 15, cy_k)], fill=seam_col, width=2)
                    draw_m.line([(cx_k - 8, cy_k - 1), (cx_k + 8, cy_k - 1)], fill=lip_col, width=1)
                    draw_m.line([(cx_k - 9, cy_k + 2), (cx_k + 9, cy_k + 2)], fill=lip_col, width=1)
            
        np_base = np.array(base)
        h, w, c = np_base.shape
        
        # 3. BODY CHANNEL: Torso Lean/Puff/Sink, Head Rotation/Accent, Stride Shear
        head_rot = 0.0
        torso_roll = 0.0
        stride_shear = 0.0
        y_bob = 0.0
        left_arm_rot = 0.0
        right_arm_rot = 0.0
        
        if idle_state:
            head_rot += idle_state.get("head_nod", 0.0)
            
        if gesture_state:
            head_rot += gesture_state.get("head_rot", 0.0)
            y_bob += gesture_state.get("bob_y", 0.0)
            torso_roll += gesture_state.get("torso_roll", 0.0)
            left_arm_rot += gesture_state.get("left_arm_rot", 0.0)
            right_arm_rot += gesture_state.get("right_arm_rot", 0.0)
            
        if walk_state:
            y_bob += walk_state.get("y_bob", 0.0)
            torso_roll += walk_state.get("torso_roll", 0.0)
            head_rot += walk_state.get("head_tilt", 0.0)
            stride_shear += walk_state.get("stride_shear", 0.0)
            # Monolithic character illustrations preserve resting arm posture during walk cycles
            
        if emotion in ["angry", "scold"]:
            torso_roll += 3.5 * emotion_intensity
        elif emotion in ["sad", "cry", "weep"]:
            torso_roll += 1.2 * emotion_intensity
            y_bob += math.sin(frame_idx * 1.5) * 2.2 * emotion_intensity # rhythmic sobbing tremor
        elif emotion in ["shiver", "cold"]:
            torso_roll += math.sin(frame_idx * 2.8) * 3.2 * emotion_intensity
            y_bob += math.sin(frame_idx * 3.5) * 4.0 * emotion_intensity

        if char_id == "kodalu":
            rig_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "characters", "kodalu", "rig"))
            saree_path = os.path.join(rig_dir, "lower_body_saree.png")
            foot_l_path = os.path.join(rig_dir, "foot_l.png")
            foot_r_path = os.path.join(rig_dir, "foot_r.png")
            
            saree_img = Image.open(saree_path).convert("RGBA") if os.path.exists(saree_path) else None
            foot_l_img = Image.open(foot_l_path).convert("RGBA") if os.path.exists(foot_l_path) else None
            foot_r_img = Image.open(foot_r_path).convert("RGBA") if os.path.exists(foot_r_path) else None
            
            # 1. Lower body saree with shear / wave math (applied to saree layer only)
            if saree_img is not None:
                saree_arr = np.array(saree_img)
                # Patch saree waist from base illustration (spanning y=480..560) to eliminate alpha gaps when sheared
                base_orig = parts.get("base")
                if base_orig is not None:
                    base_orig_arr = np.array(base_orig)
                    patch_mask = (base_orig_arr[480:560, :, 3] > 50) & (saree_arr[480:560, :, 3] < 200)
                    saree_arr[480:560, :][patch_mask] = base_orig_arr[480:560, :][patch_mask]

                if walk_state and abs(walk_state.get("dampen", 1.0)) > 0.01:
                    phase = walk_state.get("phase", 0.0)
                    dampen = walk_state.get("dampen", 1.0)
                    s_wave = walk_state.get("saree_wave", 0.0)
                    
                    is_flip = CharacterRegistry.should_flip(char_id, orientation)
                    facing_sign = -1.0 if ("left" in orientation) else 1.0
                    eff_dir = -facing_sign if is_flip else facing_sign
                    
                    grid_y, grid_x = np.mgrid[:h, :w].astype(np.float32)
                    v_prog = np.clip((grid_y - 515.0) / 345.0, 0.0, 1.0)
                    v_prog = (3.0 * v_prog**2 - 2.0 * v_prog**3)
                    
                    dx_stride = -(walk_state.get("stride_shear", 0.0) * 1.5) * eff_dir * v_prog
                    dx_wave = (s_wave * np.sin(v_prog * math.pi) * eff_dir)
                    dy_bob = y_bob * (1.0 - v_prog)
                    
                    map_x = grid_x - dx_stride - dx_wave
                    map_y = grid_y - dy_bob
                    warped_saree = cv2.remap(saree_arr, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                elif abs(stride_shear) > 0.5:
                    shear_factor = stride_shear / 360.0
                    M_lower = np.array([
                        [1.0, shear_factor, -shear_factor * 540.0],
                        [0.0, 1.0, 0.0]
                    ], dtype=np.float32)
                    warped_saree = cv2.warpAffine(saree_arr, M_lower, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                else:
                    warped_saree = saree_arr.copy()
            else:
                warped_saree = np.zeros((h, w, 4), dtype=np.uint8)
                
            # 2. Feet with ground contact, swing lift, and skin-toned ankle/shin filler
            lift_l = walk_state.get("left_foot_lift", 0.0) if walk_state else 0.0
            lift_r = walk_state.get("right_foot_lift", 0.0) if walk_state else 0.0
            
            def make_feathered_filler(poly_pts, color=(195, 128, 88), blur_radius=1.8):
                mask = Image.new("L", (w, h), 0)
                d = ImageDraw.Draw(mask)
                d.polygon(poly_pts, fill=255)
                mask = mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))
                color_img = Image.new("RGBA", (w, h), (*color, 255))
                color_img.putalpha(mask)
                return color_img

            if foot_l_img is not None:
                arr_l = np.array(foot_l_img)
                # Clean yellow hem border, red saree cloth, and white background fringing from cutout
                for y_s in range(850, 877):
                    for x_s in range(190, 275):
                        r_p, g_p, b_p, a_p = arr_l[y_s, x_s]
                        if a_p > 0:
                            is_yellow = (r_p > 175 and g_p > 125 and b_p < 90)
                            is_red = (r_p > 130 and g_p < 95 and b_p < 75)
                            is_white = (r_p > 220 and g_p > 220 and b_p > 220)
                            if is_yellow or is_red or is_white:
                                arr_l[y_s, x_s] = [0, 0, 0, 0]
                
                # Skin-toned ankle/shin filler bridging foot to saree hem (deep overlap Y: 760..878)
                ankle_l_feathered = make_feathered_filler([(225, 760), (262, 760), (267, 878), (215, 878)], color=(195, 128, 88), blur_radius=1.8)
                
                foot_l_full = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                foot_l_full.alpha_composite(ankle_l_feathered)
                foot_l_full.alpha_composite(Image.fromarray(arr_l))
                
                M_fl = np.array([[1.0, 0.0, 0.0],
                                 [0.0, 1.0, -lift_l]], dtype=np.float32)
                warped_foot_l = cv2.warpAffine(np.array(foot_l_full), M_fl, (w, h), flags=cv2.INTER_LINEAR)
            else:
                warped_foot_l = np.zeros((h, w, 4), dtype=np.uint8)
                
            if foot_r_img is not None:
                arr_r = np.array(foot_r_img)
                # Clean yellow hem residue, red saree cloth, and white fringing from cutout
                for y_s in range(850, 875):
                    for x_s in range(290, 368):
                        r_p, g_p, b_p, a_p = arr_r[y_s, x_s]
                        if a_p > 0:
                            is_yellow = (r_p > 175 and g_p > 125 and b_p < 90)
                            is_red = (r_p > 130 and g_p < 95 and b_p < 75)
                            is_white = (r_p > 220 and g_p > 220 and b_p > 220)
                            if is_yellow or is_red or is_white:
                                arr_r[y_s, x_s] = [0, 0, 0, 0]
                        
                ankle_r_feathered = make_feathered_filler([(308, 760), (350, 760), (358, 878), (298, 878)], color=(195, 128, 88), blur_radius=1.8)
                
                foot_r_full = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                foot_r_full.alpha_composite(ankle_r_feathered)
                foot_r_full.alpha_composite(Image.fromarray(arr_r))
                
                M_fr = np.array([[1.0, 0.0, 0.0],
                                 [0.0, 1.0, -lift_r]], dtype=np.float32)
                warped_foot_r = cv2.warpAffine(np.array(foot_r_full), M_fr, (w, h), flags=cv2.INTER_LINEAR)
            else:
                warped_foot_r = np.zeros((h, w, 4), dtype=np.uint8)
                
            # 3. Torso Head: Pelvic bob and torso_roll applied to torso_head only
            torso_clean_arr = np_base.copy()
            M_torso = cv2.getRotationMatrix2D(hip_pivot, torso_roll, 1.0)
            M_torso[1, 2] += y_bob
            warped_torso = cv2.warpAffine(torso_clean_arr, M_torso, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            
            # Head counter-stabilization / tilt
            total_head_rot = head_rot + torso_roll
            if abs(total_head_rot) > 0.1:
                rad_t = math.radians(torso_roll)
                cos_t = math.cos(rad_t)
                sin_t = math.sin(rad_t)
                xn = hip_pivot[0] + (neck_pivot[0] - hip_pivot[0]) * cos_t - (neck_pivot[1] - hip_pivot[1]) * sin_t
                yn = hip_pivot[1] + (neck_pivot[0] - hip_pivot[0]) * sin_t + (neck_pivot[1] - hip_pivot[1]) * cos_t + y_bob
                M_head = cv2.getRotationMatrix2D((xn, yn), head_rot, 1.0)
                y_idx = np.arange(h)[:, None]
                head_mask = np.clip((int(yn + 20) - y_idx) / 25.0, 0.0, 1.0).astype(np.float32)
                warped_head = cv2.warpAffine(warped_torso, M_head, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                warped_torso = (warped_head.astype(np.float32) * head_mask[:, :, None] + warped_torso.astype(np.float32) * (1.0 - head_mask[:, :, None])).astype(np.uint8)
                
            # 4. Composite Lower Body (feet under saree, saree under torso)
            canvas_lower = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            canvas_lower.alpha_composite(Image.fromarray(warped_foot_l))
            canvas_lower.alpha_composite(Image.fromarray(warped_foot_r))
            canvas_lower.alpha_composite(Image.fromarray(warped_saree))
            
            canvas_torso = Image.fromarray(warped_torso)
            
            # 5. Composite Arms via ArmGestureRenderer in z-index order
            g_prog = gesture_state.get("progress", frame_idx / 24.0) if gesture_state else (frame_idx / 24.0)
            final_pil = PuppetRenderer.arm_renderer.render_arm_overlay(
                canvas=canvas_lower,
                char_id=char_id,
                gesture=gesture_pose,
                progress=g_prog,
                audio_stress=audio_stress,
                walk_state=walk_state,
                torso_layer=canvas_torso
            )
        else:
            # Base body remains completely intact - preserving 100% illustration fidelity
            # Characters are cutouts with reusable poses; limbs are articulated without tearing base artwork
            body_base = np_base.copy()

            # Segment 1: Lower Saree & Legs (y from 480 to 900)
            # Seated folding kinematics OR true dual-foot alternating walk kinematics
            sit_prog = gesture_state.get("sit_progress", 0.0) if gesture_state else 0.0
            
            if sit_prog > 0.01:
                # Real 2D Cutout Seated Lower Body: Knees fold, hem spreads laterally at floor, compresses vertically
                grid_y, grid_x = np.mgrid[:h, :w].astype(np.float32)
                v_sit = np.clip((grid_y - 480.0) / 380.0, 0.0, 1.0)
                # Vertical compression: lower half compresses by up to 45% (positive dy in map_y compresses upward)
                dy_sit = v_sit * (180.0 * sit_prog)
                # Lateral expansion: hem spreads outward into stable floor triangle
                dx_sit = (grid_x - float(xc)) * (0.32 * sit_prog * v_sit)
                map_x_sit = grid_x - dx_sit
                map_y_sit = grid_y + dy_sit
                lower_part = cv2.remap(body_base, map_x_sit, map_y_sit, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            elif walk_state and abs(walk_state.get("dampen", 1.0)) > 0.01:
                phase = walk_state.get("phase", 0.0)
                dampen = walk_state.get("dampen", 1.0)
                lift_l = walk_state.get("left_foot_lift", 0.0)
                lift_r = walk_state.get("right_foot_lift", 0.0)
                s_wave = walk_state.get("saree_wave", 0.0)
                
                # Stride direction in screen space
                is_flip = CharacterRegistry.should_flip(char_id, orientation)
                facing_sign = -1.0 if ("left" in orientation) else 1.0
                # If flipped horizontally at the end, negate displacement in base coordinates
                eff_dir = -facing_sign if is_flip else facing_sign
                
                grid_y, grid_x = np.mgrid[:h, :w].astype(np.float32)
                v_prog = np.clip((grid_y - 500.0) / 360.0, 0.0, 1.0)
                v_prog = (3.0 * v_prog**2 - 2.0 * v_prog**3)
                
                # True 2D Grounded Dual-Leg Stride Mechanics
                L_stride = 52.0 * dampen
                dx_stride = -L_stride * math.cos(phase) * eff_dir * v_prog
                # Leading knee forward flex
                v_knee = np.clip(np.sin(v_prog * math.pi), 0.0, 1.0)
                dx_knee = (26.0 * max(0.0, -math.cos(phase)) * eff_dir * dampen * v_knee)
                # Vertical foot lift during swing phase
                lift_vert = (lift_l if math.sin(phase) < 0 else lift_r) * v_prog
                
                # Saree fabric wave
                dx_wave = (math.sin(phase - 0.4) * 10.0 * np.sin(v_prog * math.pi) * eff_dir * dampen)
                
                map_x = grid_x - dx_stride - dx_knee - dx_wave
                map_y = grid_y + lift_vert
                
                lower_part = cv2.remap(body_base, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            elif abs(stride_shear) > 0.5:
                shear_factor = stride_shear / 360.0
                M_lower = np.array([
                    [1.0, shear_factor, -shear_factor * 540.0],
                    [0.0, 1.0, 0.0]
                ], dtype=np.float32)
                lower_part = cv2.warpAffine(body_base, M_lower, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            else:
                lower_part = body_base.copy()
                
            # Segment 2: Torso & Spine (pivoted from character hip pivot)
            rad_torso = math.radians(torso_roll)
            if abs(torso_roll) > 0.1:
                M_torso = cv2.getRotationMatrix2D(hip_pivot, torso_roll, 1.0)
                torso_part = cv2.warpAffine(body_base, M_torso, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            else:
                torso_part = body_base.copy()

            # Real Illustrated Arm Articulation (Walking swing + Speaking gestures)
            # Articulates actual illustrated pixels pivoted at shoulders without stick arms or fake patches
            arm_l_angle = left_arm_rot
            arm_r_angle = right_arm_rot
            is_carry = (gesture_pose in ["carry", "hold_object"])
            if walk_state and abs(walk_state.get("dampen", 1.0)) > 0.01 and not is_carry:
                arm_l_angle += walk_state.get("left_arm_angle", 0.0)
                arm_r_angle += walk_state.get("right_arm_angle", 0.0)
                
            if abs(arm_l_angle) > 0.5 or abs(arm_r_angle) > 0.5:
                if abs(arm_r_angle) > 0.5:
                    M_r = cv2.getRotationMatrix2D(right_shoulder, arm_r_angle, 1.0)
                    warped_r = cv2.warpAffine(torso_part, M_r, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                else:
                    warped_r = torso_part
                    
                if abs(arm_l_angle) > 0.5:
                    M_l = cv2.getRotationMatrix2D(left_shoulder, arm_l_angle, 1.0)
                    warped_l = cv2.warpAffine(torso_part, M_l, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                else:
                    warped_l = torso_part

                y_grid, x_grid = np.ogrid[:h, :w]
                v_arm = np.clip((y_grid - (ys - 15.0)) / 30.0, 0.0, 1.0).astype(np.float32)
                
                r_arm_mask = np.clip((x_grid - float(xc + 30)) / 45.0, 0.0, 1.0).astype(np.float32) * v_arm
                l_arm_mask = np.clip((float(xc - 30) - x_grid) / 45.0, 0.0, 1.0).astype(np.float32) * v_arm
                
                torso_part = (torso_part.astype(np.float32) * (1.0 - r_arm_mask[:, :, None]) + warped_r.astype(np.float32) * r_arm_mask[:, :, None])
                torso_part = (torso_part * (1.0 - l_arm_mask[:, :, None]) + warped_l.astype(np.float32) * l_arm_mask[:, :, None])
                torso_part = np.clip(torso_part, 0, 255).astype(np.uint8)
                
            # Segment 3: Head & Neck (follows hierarchical neck pivot)
            cos_t = math.cos(rad_torso)
            sin_t = math.sin(rad_torso)
            xn_trans = hip_pivot[0] + (neck_pivot[0] - hip_pivot[0]) * cos_t - (neck_pivot[1] - hip_pivot[1]) * sin_t
            yn_trans = hip_pivot[1] + (neck_pivot[0] - hip_pivot[0]) * sin_t + (neck_pivot[1] - hip_pivot[1]) * cos_t
            curr_neck_pivot = (float(xn_trans), float(yn_trans))
            
            total_head_rot = head_rot + torso_roll
            if abs(total_head_rot) > 0.1:
                M_head = cv2.getRotationMatrix2D(curr_neck_pivot, total_head_rot, 1.0)
                head_part = cv2.warpAffine(body_base, M_head, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            else:
                head_part = body_base.copy()
                
            # Seamless vertical gradient blending across segments
            grad_lower = np.clip((np.arange(h)[:, None] - 500) / 40.0, 0.0, 1.0).astype(np.float32)
            neck_seam_y = int(yn_trans - 15)
            grad_head = np.clip((neck_seam_y - np.arange(h)[:, None]) / 25.0, 0.0, 1.0).astype(np.float32)
            grad_torso = 1.0 - np.maximum(grad_lower, grad_head)
            
            blended = (head_part * grad_head[:, :, None] +
                       torso_part * grad_torso[:, :, None] +
                       lower_part * grad_lower[:, :, None]).astype(np.uint8)

            # Composite separate layered limbs if separate arm sprites exist in character pack
            if parts.get("arm_l") is not None and abs(left_arm_rot) > 0.4:
                arm_img_l = parts["arm_l"]
                M_arm_l = cv2.getRotationMatrix2D(left_shoulder, left_arm_rot, 1.0)
                warped_arm_l = cv2.warpAffine(np.array(arm_img_l), M_arm_l, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                arm_a_l = (warped_arm_l[:, :, 3:] / 255.0).astype(np.float32)
                blended = (warped_arm_l * arm_a_l + blended * (1.0 - arm_a_l)).astype(np.uint8)

            if parts.get("arm_r") is not None and abs(right_arm_rot) > 0.4:
                arm_img_r = parts["arm_r"]
                M_arm_r = cv2.getRotationMatrix2D(right_shoulder, right_arm_rot, 1.0)
                warped_arm_r = cv2.warpAffine(np.array(arm_img_r), M_arm_r, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                arm_a_r = (warped_arm_r[:, :, 3:] / 255.0).astype(np.float32)
                blended = (warped_arm_r * arm_a_r + blended * (1.0 - arm_a_r)).astype(np.uint8)
                       
            final_pil = Image.fromarray(blended)

        # Active gestures articulate the real character artwork directly via localized arm pivots above.
        # No artificial vector stick arms, no third arms, no fake solid clothing patches.
        
        # Orientation & perspective handling
        # Support: front, 3/4_left, 3/4_right, side_left, side_right, back
        flip = False
        compress_x = 1.0
        
        if orientation in ["three_quarter_left", "3/4_left", "side_left"]:
            flip = CharacterRegistry.should_flip(char_id, orientation)
            if "side" in orientation:
                compress_x = 0.85
        elif orientation in ["three_quarter_right", "3/4_right", "side_right"]:
            flip = CharacterRegistry.should_flip(char_id, orientation)
            if "side" in orientation:
                compress_x = 0.85
        elif orientation == "front":
            flip = False
            compress_x = 1.02
        elif orientation == "back":
            flip = False
            # Back view: slightly darker tone
            np_arr = np.array(final_pil)
            np_arr[:, :, :3] = (np_arr[:, :, :3] * 0.88).astype(np.uint8)
            final_pil = Image.fromarray(np_arr)
            
        if flip:
            final_pil = final_pil.transpose(Image.FLIP_LEFT_RIGHT)
            
        # Apply scaling
        g_scale_x = gesture_state.get("scale_x", 1.0) if gesture_state else 1.0
        g_scale_y = gesture_state.get("scale_y", 1.0) if gesture_state else 1.0
        walk_scale_mod = walk_state.get("scale_mod", 1.0) if walk_state else 1.0

        combined_scale_x = scale * g_scale_x * compress_x * walk_scale_mod
        combined_scale_y = scale * g_scale_y * walk_scale_mod
            
        if combined_scale_x != 1.0 or combined_scale_y != 1.0:
            nw = max(1, int(final_pil.width * combined_scale_x))
            nh = max(1, int(final_pil.height * combined_scale_y))
            final_pil = final_pil.resize((nw, nh), Image.Resampling.LANCZOS)
            
        return final_pil
