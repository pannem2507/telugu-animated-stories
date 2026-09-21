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
from PIL import Image

from .face_engine import FacePerformanceEngine
from .arm_ik import ArmGestureRenderer

# Character anatomical anchor definitions (standard 600x900 canvas)
NECK_PIVOT = (300, 310)
HIP_PIVOT = (300, 540)
LEFT_SHOULDER = (200, 350)
RIGHT_SHOULDER = (400, 350)
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
                 total_walk_frames: int = None, is_stopping: bool = False) -> dict:
        phase = (frame_idx / float(self.cycle_frames)) * (2.0 * math.pi)
        
        # Determine dampening if coming to a stop (foot planting)
        dampen = 1.0
        if total_walk_frames and total_walk_frames > 0:
            remaining = total_walk_frames - frame_idx
            if remaining < 10:
                dampen = max(0.0, remaining / 10.0)
                
        # 1. Vertical Torso Bob (Highest at passing position, lowest at foot contact)
        # In screen coords (Y down): cos(2*phase) is +1 at contact (cushion down), -1 at passing (lift up)
        y_bob = (math.cos(2.0 * phase) * 8.5) * dampen
        
        # 2. Torso Pitch / Sway Roll
        torso_roll = (math.sin(phase) * 2.6) * dampen
        
        # 3. Head Counter-Stabilization
        head_tilt = (-torso_roll * 0.75 + math.sin(2.0 * phase) * 1.0) * dampen
        
        # 4. Alternating Arm Swing (opposite to leg stride)
        left_arm_angle = (math.sin(phase) * 22.0) * dampen
        right_arm_angle = (-math.sin(phase) * 22.0) * dampen
        
        # 5. Lower Saree / Leg Stride Shear
        stride_shear = (math.sin(phase) * 20.0) * dampen
        saree_wave = (math.sin(phase - 0.5) * 6.0) * dampen
        
        # 6. Foot contact heights
        left_foot_lift = max(0.0, -math.sin(phase)) * 8.0 * dampen
        right_foot_lift = max(0.0, math.sin(phase)) * 8.0 * dampen
        
        # 7. Perspective scale modulation (for toward/away walks)
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
            "dampen": dampen
        }

class IdleController:
    """Subtle realistic idle secondary motion: breathing, weight shifting, head drift."""
    def __init__(self, seed: int = 0):
        self.phase_offset = seed * 1.3
        
    def evaluate(self, frame_idx: int) -> dict:
        t = frame_idx * 0.08 + self.phase_offset
        # Gentle diaphragm breathing (2.5 - 3.0s full breath cycle)
        breath_scale_y = 1.0 + math.sin(t * 0.4) * 0.014
        breath_scale_x = 1.0 - math.sin(t * 0.4) * 0.005
        # Subtle posture sway
        sway_x = math.sin(t * 0.25) * 1.5
        head_idle_nod = math.sin(t * 0.5) * 1.2
        
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
    def evaluate(action: str, frame_idx: int, total_frames: int, is_speaker: bool) -> dict:
        action = action.lower() if action else "idle"
        prog = min(1.0, frame_idx / max(1, total_frames))
        
        head_rot = 0.0
        left_arm_rot = 0.0
        right_arm_rot = 0.0
        body_jitter_x = 0.0
        body_jitter_y = 0.0
        bob_y = 0.0
        torso_roll = 0.0
        scale_x = 1.0
        scale_y = 1.0
        
        # 1. Emotional & Reactive States
        if action == "shiver":
            # Rapid winter cold tremor
            body_jitter_x = math.sin(frame_idx * 1.8) * 4.0
            body_jitter_y = math.cos(frame_idx * 2.2) * 2.5
            head_rot = math.sin(frame_idx * 2.0) * 2.0
            left_arm_rot = 12.0
            right_arm_rot = -12.0
            
        elif action in ["angry", "scold"]:
            # Aggressive forward lean, scolding hand gesture
            head_rot = 5.0 + math.sin(frame_idx * 0.6) * 4.0
            bob_y = math.sin(frame_idx * 0.5) * 4.0
            right_arm_rot = -28.0 + math.sin(frame_idx * 0.4) * 12.0
            torso_roll = 3.5
            
        elif action in ["cry", "weep"]:
            # Head bowed deeply, weeping rhythmic shoulder heaving
            head_rot = 10.0
            bob_y = math.sin(frame_idx * 0.8) * 3.5
            left_arm_rot = 18.0
            right_arm_rot = -25.0
            body_jitter_y = math.sin(frame_idx * 1.5) * 1.5
            
        elif action in ["sad", "worry", "distress"]:
            # Downcast head and slumped posture
            head_rot = 7.0
            bob_y = 4.0
            torso_roll = 1.5
            left_arm_rot = 8.0
            right_arm_rot = -8.0
            
        elif action in ["happy", "joy", "excited"]:
            # Upright energetic bounce and head tilt
            head_rot = -3.0 + math.sin(frame_idx * 0.4) * 3.0
            bob_y = -math.sin(frame_idx * 0.6) * 5.0
            right_arm_rot = -20.0 + math.sin(frame_idx * 0.5) * 10.0
            left_arm_rot = 15.0
            
        elif action in ["surprised", "shock"]:
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
        elif action in ["cook", "stir", "use_stove"]:
            # Tending the chulha stove, rhythmic stirring
            bob_y = math.sin(frame_idx * 0.35) * 5.0
            right_arm_rot = math.sin(frame_idx * 0.4) * 18.0
            head_rot = 4.0
            
        elif action in ["warm_hands"]:
            # Rubbing hands together over campfire/heater
            bob_y = math.sin(frame_idx * 0.3) * 3.0
            right_arm_rot = -26.0 + math.sin(frame_idx * 1.2) * 5.0
            left_arm_rot = 26.0 - math.sin(frame_idx * 1.2) * 5.0
            head_rot = 4.0
            
        elif action in ["light_fire"]:
            # Leaning down towards stove/hearth
            bob_y = 12.0
            torso_roll = 5.0
            head_rot = 8.0
            right_arm_rot = -35.0
            
        elif action in ["eat"]:
            # Hand to mouth rhythmic motion
            right_arm_rot = -35.0 + math.sin(frame_idx * 0.4) * 15.0
            head_rot = 3.0 + math.sin(frame_idx * 0.4) * 2.5
            bob_y = 2.0
            
        elif action in ["sleep"]:
            # Resting down, head tilted
            head_rot = 14.0
            bob_y = 16.0
            torso_roll = 8.0
            scale_y = 0.95
            
        elif action in ["wake"]:
            # Rising upright
            ease = min(1.0, frame_idx / 16.0)
            head_rot = 14.0 * (1.0 - ease)
            bob_y = 16.0 * (1.0 - ease)
            
        elif action in ["knock_door"]:
            # Rhythmic knocking on wooden door
            right_arm_rot = -55.0 + math.sin(frame_idx * 1.6) * 10.0
            head_rot = 2.0
            
        elif action in ["open_door", "close_door"]:
            # Reaching arm
            right_arm_rot = -35.0 * math.sin(prog * math.pi)
            
        elif action in ["carry", "hold_object"]:
            # Carrying stove / vessel at waist
            right_arm_rot = -24.0
            left_arm_rot = 24.0
            bob_y = 2.0
            
        elif action in ["give_object"]:
            # Offering object forward
            ease = math.sin(prog * math.pi)
            right_arm_rot = -35.0 * ease
            left_arm_rot = 25.0 * ease
            
        elif action in ["receive_object", "pick_up"]:
            # Cupped hands accepting
            ease = math.sin(prog * math.pi)
            right_arm_rot = -28.0 * ease
            left_arm_rot = 28.0 * ease
            bob_y = 6.0 * ease
            
        elif action in ["pray", "namaste"]:
            # Folded hands at chest, respectful head bow
            head_rot = 5.0
            right_arm_rot = -20.0
            left_arm_rot = 20.0
            bob_y = 2.0
            
        elif action in ["meditate"]:
            # Serene steady seated meditation
            head_rot = 0.0
            bob_y = math.sin(frame_idx * 0.15) * 1.5
            torso_roll = 0.0
            
        elif action in ["bend"]:
            bob_y = 18.0
            torso_roll = 10.0
            head_rot = 8.0
            
        elif action in ["sit"]:
            bob_y = 14.0
            scale_y = 0.94
            
        elif action in ["stand"]:
            bob_y = 0.0
            scale_y = 1.0
            
        elif action in ["point", "accuse"]:
            ease = math.sin(prog * math.pi) if prog < 0.9 else 0.0
            right_arm_rot = -35.0 * ease
            head_rot = 3.0 * ease
            
        elif action in ["turn", "look_left"]:
            head_rot = -8.0
            
        elif action in ["look_right"]:
            head_rot = 8.0
            
        elif is_speaker:
            # Natural talking articulation
            head_rot = math.sin(frame_idx * 0.45) * 3.5
            bob_y = math.sin(frame_idx * 0.45) * 3.0
            right_arm_rot = math.sin(frame_idx * 0.3) * 6.0
            
        else:
            # Alive listener: subtle attentive nodding
            if (frame_idx % 48) < 14:
                head_rot = math.sin(((frame_idx % 48) / 14.0) * math.pi) * 3.0
                
        return {
            "head_rot": head_rot,
            "left_arm_rot": left_arm_rot,
            "right_arm_rot": right_arm_rot,
            "jitter_x": body_jitter_x,
            "jitter_y": body_jitter_y,
            "bob_y": bob_y,
            "torso_roll": torso_roll,
            "scale_x": scale_x,
            "scale_y": scale_y
        }

class PuppetRenderer:
    """
    Composes full animated character by applying anatomical transforms:
    - FACE Channel: Localized mask deformation (Brows, Eyes, Mouth, Tears)
    - BODY Channel: Torso lean/puff/sink, Head rotation/accent, Lower Saree stride shear
    - HANDS Channel: 2D Arm IK articulation (Pointing jab, Wipe tears, Pray, Cook)
    - Orientation control (front, 3/4_left, 3/4_right, side_left, side_right, back)
    """
    face_engine = FacePerformanceEngine(max_displacement=7.0)
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
        else:
            base = parts["base"].copy()
        is_back = (orientation == "back")
        
        # 1. FACE CHANNEL: Blink, Localized Safe Deformation, Organic Tears
        if not is_back:
            # Composite blink overlay if active with dynamic facial landmark anchoring
            if is_blinking and parts.get("eyes_blink"):
                blink_img = parts["eyes_blink"]
                lm = PuppetRenderer.face_engine.get_landmarks(char_id)
                eye_l = lm.get("eye_l", (245, 140))
                eye_r = lm.get("eye_r", (315, 140))
                target_cy = (eye_l[1] + eye_r[1]) / 2.0
                target_cx = (eye_l[0] + eye_r[0]) / 2.0
                
                if blink_img.size == base.size:
                    # Full-canvas overlay: verify non-zero pixels fall within anatomical eye band
                    arr_b = np.array(blink_img)
                    nz = np.argwhere(arr_b[:, :, 3] > 10)
                    if len(nz) > 0:
                        ymin, xmin = nz.min(axis=0)
                        ymax, xmax = nz.max(axis=0)
                        cy_nz = (ymin + ymax) / 2.0
                        # Strict safety bounds: eyelid must fall within +/- 35px of anatomical eye center
                        if abs(cy_nz - target_cy) <= 35:
                            base.alpha_composite(blink_img)
                        # Else safely skip rather than drawing on cheeks/mouth!
                else:
                    # Cropped sprite: compute destination dynamically from eye center
                    bw, bh = blink_img.size
                    dest_x = int(target_cx - bw / 2.0)
                    dest_y = int(target_cy - bh / 2.0)
                    # Bounds verification: check if dest_y centers on eye level
                    if abs(dest_y + bh / 2.0 - target_cy) <= 25:
                        base.alpha_composite(blink_img, dest=(dest_x, dest_y))
                    
            # Apply safe localized deformation (Brows, Eyelids, Mouth corners & multi-axis viseme articulation)
            # Active for all expressive states as well as speaking phonemes
            if emotion in ["angry", "scold", "irritation", "peak_anger", "sad", "cry", "weep", "crying", "intense_crying", "cower", "fear", "happy", "joy", "relief", "reverence", "surprise", "shock"] or audio_stress > 0.05 or (mouth_cue and mouth_cue != "mouth_closed"):
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

        # 2. HANDS CHANNEL: 2D Arm IK for active object & mudra gestures
        # Characters have naturally drawn hands, so pray, carry, point, cook, and face wipe use expressive body/face channel
        if gesture_pose and gesture_pose not in ["idle", "stand", "walk", "none", "point", "wipe_face", "pray", "carry", "cook"] and not is_back:
            base = PuppetRenderer.arm_renderer.render_arm_overlay(
                canvas=base,
                char_id=char_id,
                gesture=gesture_pose,
                progress=tear_progress if gesture_pose == "wipe_face" else 1.0,
                audio_stress=audio_stress
            )
            
        np_base = np.array(base)
        h, w, c = np_base.shape
        
        # 3. BODY CHANNEL: Torso Lean/Puff/Sink, Head Rotation/Accent, Stride Shear
        head_rot = 0.0
        torso_roll = 0.0
        stride_shear = 0.0
        y_bob = 0.0
        
        if idle_state:
            head_rot += idle_state.get("head_nod", 0.0)
            
        if gesture_state:
            head_rot += gesture_state.get("head_rot", 0.0)
            y_bob += gesture_state.get("bob_y", 0.0)
            torso_roll += gesture_state.get("torso_roll", 0.0)
            
        if walk_state:
            y_bob += walk_state.get("y_bob", 0.0)
            torso_roll += walk_state.get("torso_roll", 0.0)
            head_rot += walk_state.get("head_tilt", 0.0)
            stride_shear += walk_state.get("stride_shear", 0.0)
            
        if emotion in ["angry", "scold"]:
            torso_roll += 3.5 * emotion_intensity
        elif emotion in ["sad", "cry", "weep"]:
            torso_roll += 1.2 * emotion_intensity
            y_bob += math.sin(frame_idx * 1.5) * 2.2 * emotion_intensity # rhythmic sobbing tremor
            
        # Segment 1: Lower Saree & Legs (y from 520 to 900)
        if abs(stride_shear) > 0.5:
            shear_factor = stride_shear / 360.0
            M_lower = np.array([
                [1.0, shear_factor, -shear_factor * 540.0],
                [0.0, 1.0, 0.0]
            ], dtype=np.float32)
            lower_part = cv2.warpAffine(np_base, M_lower, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        else:
            lower_part = np_base.copy()
            
        # Segment 2: Torso & Arms (y from 300 to 540)
        if abs(torso_roll) > 0.1:
            M_torso = cv2.getRotationMatrix2D(HIP_PIVOT, torso_roll, 1.0)
            torso_part = cv2.warpAffine(np_base, M_torso, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        else:
            torso_part = np_base.copy()
            
        # Segment 3: Head & Neck (y from 0 to 320)
        if abs(head_rot) > 0.1:
            M_head = cv2.getRotationMatrix2D(NECK_PIVOT, head_rot, 1.0)
            head_part = cv2.warpAffine(np_base, M_head, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        else:
            head_part = np_base.copy()
            
        # Seamless vertical gradient blending across segments
        grad_lower = np.clip((np.arange(h)[:, None] - 500) / 40.0, 0.0, 1.0).astype(np.float32)
        grad_head = np.clip((330 - np.arange(h)[:, None]) / 40.0, 0.0, 1.0).astype(np.float32)
        grad_torso = 1.0 - np.maximum(grad_lower, grad_head)
        
        blended = (head_part * grad_head[:, :, None] +
                   torso_part * grad_torso[:, :, None] +
                   lower_part * grad_lower[:, :, None]).astype(np.uint8)
                   
        final_pil = Image.fromarray(blended, mode="RGBA")
        
        # Orientation & perspective handling
        # Support: front, 3/4_left, 3/4_right, side_left, side_right, back
        flip = False
        compress_x = 1.0
        
        if orientation in ["three_quarter_left", "3/4_left", "side_left"]:
            # Kodalu base art already faces 3/4 left! Do not flip her.
            flip = (char_id != "kodalu")
            if "side" in orientation:
                compress_x = 0.85
        elif orientation in ["three_quarter_right", "3/4_right", "side_right"]:
            # If Kodalu is asked to face right, flip her. Atha already faces right.
            flip = (char_id == "kodalu")
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
            final_pil = Image.fromarray(np_arr, mode="RGBA")
            
        if flip:
            final_pil = final_pil.transpose(Image.FLIP_LEFT_RIGHT)
            
        # Apply scaling
        combined_scale = scale
        if walk_state and "scale_mod" in walk_state:
            combined_scale *= walk_state["scale_mod"]
            
        if compress_x != 1.0 or combined_scale != 1.0:
            nw = int(final_pil.width * combined_scale * compress_x)
            nh = int(final_pil.height * combined_scale)
            final_pil = final_pil.resize((nw, nh), Image.Resampling.LANCZOS)
            
        return final_pil
