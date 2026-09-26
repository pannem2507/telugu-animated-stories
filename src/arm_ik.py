"""
2D Articulated Arm Inverse Kinematics (IK) System
Supports 2-link kinematic solver:
  Shoulder -> Upper Arm -> Elbow -> Forearm -> Wrist -> Hand
Handles target-directed poses:
  point, wave, wipe_face, pray, reach, give, receive, carry, cook
"""

import os
import math
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

class ArmIKSolver:
    """
    Analytic 2-link 2D Inverse Kinematics solver for character arm articulation.
    """
    def __init__(self, upper_arm_len: float = 110.0, forearm_len: float = 100.0):
        self.l1 = upper_arm_len
        self.l2 = forearm_len
        self.max_reach = self.l1 + self.l2
        self.min_reach = abs(self.l1 - self.l2) + 5.0
        
    def solve_ik(self, shoulder: tuple, target: tuple, elbow_dir: int = 1) -> dict:
        """
        Solves 2-link IK from shoulder (x0, y0) to target (xt, yt).
        elbow_dir: +1 for natural down/out bend, -1 for upward bend.
        Returns:
            {
                "shoulder": (x0, y0),
                "elbow": (xe, ye),
                "wrist": (xw, yw),
                "theta1": shoulder_angle_rad,
                "theta2": elbow_angle_rad,
                "reach_dist": distance
            }
        """
        x0, y0 = shoulder
        xt, yt = target
        dx = xt - x0
        dy = yt - y0
        dist = math.sqrt(dx * dx + dy * dy)
        
        # Clamp distance to reachable range
        clamped_dist = max(self.min_reach, min(self.max_reach * 0.98, dist))
        
        # Law of Cosines for elbow interior angle
        cos_theta2 = (clamped_dist**2 - self.l1**2 - self.l2**2) / (2.0 * self.l1 * self.l2)
        cos_theta2 = max(-1.0, min(1.0, cos_theta2))
        theta2 = elbow_dir * math.acos(cos_theta2)
        
        # Base angle to target
        alpha = math.atan2(dy, dx)
        # Angle offset to elbow
        beta = math.atan2(self.l2 * math.sin(theta2), self.l1 + self.l2 * math.cos(theta2))
        theta1 = alpha - beta
        
        # Forward kinematics
        xe = x0 + self.l1 * math.cos(theta1)
        ye = y0 + self.l1 * math.sin(theta1)
        xw = xe + self.l2 * math.cos(theta1 + theta2)
        yw = ye + self.l2 * math.sin(theta1 + theta2)
        
        return {
            "shoulder": (float(x0), float(y0)),
            "elbow": (float(xe), float(ye)),
            "wrist": (float(xw), float(yw)),
            "theta1": float(theta1),
            "theta2": float(theta2),
            "reach_dist": float(dist)
        }

class ArmGestureRenderer:
    """
    Renders articulated arm geometry and hand poses on the character canvas.
    Matches character skin, sleeve, and bangle styling.
    """
    # Character anatomical arm defaults (600x900 canvas)
    CHAR_ARM_CONFIG = {
        "atha": {
            "shoulder_r": (410, 310), # Atha's right arm (viewer's left side on 3/4 right)
            "shoulder_l": (440, 315),
            "skin_color": (212, 148, 102),
            "sleeve_color": (0, 160, 215), # Blue blouse
            "bangle_color": (230, 185, 45), # Gold bangles
            "arm_thickness": 24
        },
        "kodalu": {
            "shoulder_r": (365, 290),
            "shoulder_l": (380, 280),
            "skin_color": (197, 127, 91),
            "sleeve_color": (205, 215, 45), # Yellow blouse
            "bangle_color": (225, 180, 40), # Gold bangles
            "arm_thickness": 20
        },
        "gent": {
            "shoulder_r": (360, 260),
            "shoulder_l": (390, 265),
            "skin_color": (205, 140, 100),
            "sleeve_color": (75, 130, 75), # Green shirt
            "bangle_color": None,
            "arm_thickness": 22
        },
        "kanthamma": {
            "shoulder_r": (370, 310),
            "shoulder_l": (420, 315),
            "skin_color": (200, 135, 95),
            "sleeve_color": (180, 50, 60), # Maroon blouse
            "bangle_color": (220, 180, 40),
            "arm_thickness": 22
        },
        "saroja": {
            "shoulder_r": (370, 310),
            "shoulder_l": (420, 315),
            "skin_color": (200, 135, 95),
            "sleeve_color": (180, 50, 60),
            "bangle_color": (220, 180, 40),
            "arm_thickness": 22
        },
        "maharshi": {
            "shoulder_r": (370, 300),
            "shoulder_l": (420, 305),
            "skin_color": (195, 130, 85),
            "sleeve_color": (220, 110, 40), # Saffron robe
            "bangle_color": None,
            "arm_thickness": 22
        },
        "padma": {
            "shoulder_r": (365, 290),
            "shoulder_l": (385, 285),
            "skin_color": (200, 130, 90),
            "sleeve_color": (50, 140, 160),
            "bangle_color": (220, 180, 40),
            "arm_thickness": 20
        },
        "kid": {
            "shoulder_r": (320, 420),
            "shoulder_l": (360, 420),
            "skin_color": (210, 145, 105),
            "sleeve_color": (210, 80, 50),
            "bangle_color": None,
            "arm_thickness": 16
        }
    }
    
    def __init__(self):
        self.solver = ArmIKSolver(upper_arm_len=96.0, forearm_len=104.0)
        
    def get_gesture_target(self, gesture: str, char_id: str,
                           actor_pos: tuple = (0, 0),
                           world_target: tuple = None,
                           progress: float = 1.0,
                           audio_stress: float = 0.0) -> tuple:
        """
        Computes local (x, y) target coordinates within character canvas (600x900)
        for a desired gesture.
        """
        cfg = self.CHAR_ARM_CONFIG.get(char_id, self.CHAR_ARM_CONFIG["kodalu"])
        sh_x, sh_y = cfg["shoulder_r"]
        
        if gesture == "point":
            # Outstretched accusing arm pointing towards target / listener
            # Jabs forward on audio stress peaks
            jab = audio_stress * 22.0
            tx = sh_x + 160.0 + jab
            ty = sh_y + 45.0 - (audio_stress * 12.0)
            return (tx, ty)
            
        elif gesture == "wipe_face":
            # Hand reaches to cheek tear line (Kodalu cheek ~ 235, 175)
            # Gentle dabbing movement
            dab = math.sin(progress * math.pi * 3.0) * 8.0
            tx = 240.0 + dab
            ty = 175.0 + math.cos(progress * math.pi * 2.0) * 5.0
            return (tx, ty)
            
        elif gesture == "pray":
            # Both hands at center chest
            return (280.0, 310.0)
            
        elif gesture == "carry":
            # Both hands holding object at waist
            return (285.0, 420.0)
            
        elif gesture == "reach" or gesture == "give":
            # Extending forward at waist level
            return (sh_x + 140.0 * min(1.0, progress * 1.5), sh_y + 110.0)
            
        elif gesture == "receive":
            # Cupped hands slightly lower
            return (sh_x + 110.0, sh_y + 130.0)
            
        elif gesture == "cook":
            # Stirring motion over stove
            stir_x = math.cos(progress * math.pi * 4.0) * 14.0
            stir_y = math.sin(progress * math.pi * 4.0) * 8.0
            return (sh_x + 5.0 + stir_x, sh_y + 145.0 + stir_y)
            
        elif gesture == "wave":
            wave_x = math.sin(progress * math.pi * 4.0) * 25.0
            return (sh_x + 90.0 + wave_x, sh_y - 80.0)
            
        # Default idle arm position
        return (sh_x + 35.0, sh_y + 175.0)
        
    _rig_cache = {}

    @staticmethod
    def _clean_sprite_borders(im: Image.Image, border_px: int = 4) -> Image.Image:
        arr = np.array(im).astype(np.float32)
        h, w, _ = arr.shape
        y_idx, x_idx = np.mgrid[:h, :w]
        dist_edge = np.minimum(
            np.minimum(x_idx, w - 1 - x_idx),
            np.minimum(y_idx, h - 1 - y_idx)
        ).astype(np.float32)
        edge_alpha = np.clip(dist_edge / float(border_px), 0.0, 1.0)
        edge_alpha = 3.0 * edge_alpha**2 - 2.0 * edge_alpha**3
        arr[:, :, 3] *= edge_alpha
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    def _get_kodalu_rig_parts(self):
        if "kodalu" not in self._rig_cache:
            rig_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "characters", "kodalu", "rig"))
            if os.path.exists(rig_dir):
                upper_l = Image.open(os.path.join(rig_dir, "upper_arm_l.png")).convert("RGBA")
                forearm_l = Image.open(os.path.join(rig_dir, "forearm_l.png")).convert("RGBA")
                hand_l = Image.open(os.path.join(rig_dir, "hand_l.png")).convert("RGBA")
                
                # 0. Clean outer sprite image borders to prevent any rectangular box lines when rotated
                upper_l = self._clean_sprite_borders(upper_l, border_px=2)
                forearm_l = self._clean_sprite_borders(forearm_l, border_px=2)
                hand_l = self._clean_sprite_borders(hand_l, border_px=2)
                
                # Soft alpha feathering at joint boundaries to eliminate visible seam lines
                # 1. Upper arm bottom edge (elbow overlap): feather bottom 4 pixels
                u_arr = np.array(upper_l).astype(np.float32)
                uh = u_arr.shape[0]
                y_u = np.arange(uh)[:, None]
                feather_u_bot = np.clip((uh - y_u) / 4.0, 0.0, 1.0)
                feather_u_bot = 3.0 * (feather_u_bot ** 2) - 2.0 * (feather_u_bot ** 3)
                u_arr[:, :, 3] *= feather_u_bot
                upper_l = Image.fromarray(np.clip(u_arr, 0, 255).astype(np.uint8))

                # 2. Forearm top edge (elbow overlap) and bottom edge (wrist overlap)
                f_arr = np.array(forearm_l).astype(np.float32)
                fh = f_arr.shape[0]
                y_f = np.arange(fh)[:, None]
                feather_f_top = np.clip(y_f / 4.0, 0.0, 1.0)
                feather_f_top = 3.0 * (feather_f_top ** 2) - 2.0 * (feather_f_top ** 3)
                feather_f_bot = np.clip((fh - y_f) / 4.0, 0.0, 1.0)
                feather_f_bot = 3.0 * (feather_f_bot ** 2) - 2.0 * (feather_f_bot ** 3)
                f_arr[:, :, 3] *= (feather_f_top * feather_f_bot)
                forearm_l = Image.fromarray(np.clip(f_arr, 0, 255).astype(np.uint8))

                # 3. Hand top edge (wrist overlap): feather top 4 pixels into bangles
                h_arr = np.array(hand_l).astype(np.float32)
                hh = h_arr.shape[0]
                y_h = np.arange(hh)[:, None]
                feather_h_top = np.clip(y_h / 4.0, 0.0, 1.0)
                feather_h_top = 3.0 * (feather_h_top ** 2) - 2.0 * (feather_h_top ** 3)
                h_arr[:, :, 3] *= feather_h_top
                hand_l = Image.fromarray(np.clip(h_arr, 0, 255).astype(np.uint8))
                
                # Assemble lower arm using true alpha compositing: hand joins forearm at bangles (56, 101)
                low_w = max(forearm_l.width, 56 + hand_l.width)
                low_h = max(forearm_l.height, 101 + hand_l.height)
                lower_l = Image.new("RGBA", (low_w, low_h), (0, 0, 0, 0))
                lower_l.alpha_composite(forearm_l, (0, 0))
                lower_l.alpha_composite(hand_l, (56, 101))
                lower_l = self._clean_sprite_borders(lower_l, border_px=2)
                
                lower_r = lower_l.transpose(Image.FLIP_LEFT_RIGHT)
                upper_r = upper_l.transpose(Image.FLIP_LEFT_RIGHT)
                
                self._rig_cache["kodalu"] = {
                    "upper_l": upper_l,
                    "lower_l": lower_l,
                    "upper_r": upper_r,
                    "lower_r": lower_r,
                    "low_w": low_w
                }
            else:
                self._rig_cache["kodalu"] = None
        return self._rig_cache.get("kodalu")

    @staticmethod
    def _get_affine_matrix(local_pivot, world_dest, angle_rad):
        px, py = local_pivot
        wx, wy = world_dest
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        tx = wx - (px * cos_a - py * sin_a)
        ty = wy - (px * sin_a + py * cos_a)
        return np.array([[cos_a, -sin_a, tx],
                         [sin_a,  cos_a, ty]], dtype=np.float32)

    def render_arm_overlay(self, canvas: Image.Image, char_id: str,
                           gesture: str = "idle", progress: float = 1.0,
                           audio_stress: float = 0.0,
                           world_target: tuple = None,
                           walk_state: dict = None,
                           torso_layer: Image.Image = None) -> Image.Image:
        """
        Renders 2-link IK articulated arms for character puppet.
        For Kodalu: Hierarchically rotates upper_arm at shoulder pivot,
        then forearm+hand at elbow pivot in the upper arm's rotated coordinate frame.
        Composites onto canvas at the z-index order defined in character_rig.json.
        Always renders arm overlays unconditionally in every frame (idle, walk, gestures).
        """
        if char_id != "kodalu":
            return canvas
            
        parts = self._get_kodalu_rig_parts()
        if not parts:
            return canvas
            
        w, h = canvas.size
        
        # 1. Shoulder anchors (track torso roll and bob dynamically)
        sh_l = (225.0, 285.0)
        sh_r = (370.0, 290.0)
        
        y_bob = walk_state.get("y_bob", 0.0) if walk_state else 0.0
        torso_roll = walk_state.get("torso_roll", 0.0) if walk_state else 0.0
        if abs(torso_roll) > 0.01 or abs(y_bob) > 0.01:
            hip_pivot = (300.0, 540.0)
            rad_t = math.radians(torso_roll)
            cos_t = math.cos(rad_t)
            sin_t = math.sin(rad_t)
            sh_l = (
                hip_pivot[0] + (sh_l[0] - hip_pivot[0]) * cos_t - (sh_l[1] - hip_pivot[1]) * sin_t,
                hip_pivot[1] + (sh_l[0] - hip_pivot[0]) * sin_t + (sh_l[1] - hip_pivot[1]) * cos_t + y_bob
            )
            sh_r = (
                hip_pivot[0] + (sh_r[0] - hip_pivot[0]) * cos_t - (sh_r[1] - hip_pivot[1]) * sin_t,
                hip_pivot[1] + (sh_r[0] - hip_pivot[0]) * sin_t + (sh_r[1] - hip_pivot[1]) * cos_t + y_bob
            )
        
        # 2. Determine arm targets
        swing_r = 0.0
        swing_l = 0.0
        if walk_state and abs(walk_state.get("dampen", 1.0)) > 0.01:
            swing_r = walk_state.get("right_arm_angle", 0.0)
            swing_l = walk_state.get("left_arm_angle", 0.0)
            
        # Resting arm targets (unconditional fallback for resting pose)
        ang_r = math.atan2(192.0, 8.0) + math.radians(swing_r)
        target_r = (sh_r[0] + 192.2 * math.cos(ang_r), sh_r[1] + 192.2 * math.sin(ang_r))
        ang_l = math.atan2(192.0, -8.0) - math.radians(swing_l)
        target_l = (sh_l[0] + 192.2 * math.cos(ang_l), sh_l[1] + 192.2 * math.sin(ang_l))

        # Active gestures override resting pose on active limbs
        if gesture and gesture not in ["idle", "walk", "walk_left", "walk_right", "walk_left_to_right", "walk_right_to_left"]:
            if gesture in ["pray"]:
                target_r = (280.0, 310.0)
                target_l = (280.0, 310.0)
            elif gesture in ["carry"]:
                target_r = (285.0, 420.0)
                target_l = (285.0, 420.0)
            else:
                target_r = self.get_gesture_target(gesture, char_id, world_target=world_target, progress=progress, audio_stress=audio_stress)
            
        # 3. Solve 2-link IK
        ik_l = self.solver.solve_ik(sh_l, target_l, elbow_dir=-1)
        ik_r = self.solver.solve_ik(sh_r, target_r, elbow_dir=1)
        
        # 4. Warp Left Arm (z-index 5, 6, 7)
        upper_l = parts["upper_l"]
        lower_l = parts["lower_l"]
        low_w = parts["low_w"]
        
        rot1_l = ik_l["theta1"] - math.pi / 2.0
        pu_l = (27.0, 5.0)
        M_u_l = self._get_affine_matrix(pu_l, sh_l, rot1_l)
        warped_u_l = cv2.warpAffine(np.array(upper_l), M_u_l, (w, h), flags=cv2.INTER_LINEAR)
        
        rot2_l = (ik_l["theta1"] + ik_l["theta2"]) - 0.9954
        M_low_l = self._get_affine_matrix((21.0, 10.0), ik_l["elbow"], rot2_l)
        warped_low_l = cv2.warpAffine(np.array(lower_l), M_low_l, (w, h), flags=cv2.INTER_LINEAR)
        
        # 5. Warp Right Arm (z-index 15, 16, 17)
        upper_r = parts["upper_r"]
        lower_r = parts["lower_r"]
        
        rot1_r = ik_r["theta1"] - math.pi / 2.0
        pu_r = (27.0, 5.0)
        M_u_r = self._get_affine_matrix(pu_r, sh_r, rot1_r)
        warped_u_r = cv2.warpAffine(np.array(upper_r), M_u_r, (w, h), flags=cv2.INTER_LINEAR)
        
        rot2_r = (ik_r["theta1"] + ik_r["theta2"]) - 2.1462
        M_low_r = self._get_affine_matrix((low_w - 21.0, 10.0), ik_r["elbow"], rot2_r)
        warped_low_r = cv2.warpAffine(np.array(lower_r), M_low_r, (w, h), flags=cv2.INTER_LINEAR)
        
        # 6. Composite in z-index order
        res = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        # Left arm behind torso (z-index 5, 6, 7)
        res.alpha_composite(Image.fromarray(warped_u_l))
        res.alpha_composite(Image.fromarray(warped_low_l))
        
        # Canvas / Lower body (z-index 6..8)
        if canvas is not None:
            res.alpha_composite(canvas)

        # Torso / Head (z-index 10)
        if torso_layer is not None:
            res.alpha_composite(torso_layer)
            
        # Right arm in front of torso (z-index 15..17)
        res.alpha_composite(Image.fromarray(warped_u_r))
        res.alpha_composite(Image.fromarray(warped_low_r))
        
        return res
