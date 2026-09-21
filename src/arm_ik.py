"""
2D Articulated Arm Inverse Kinematics (IK) System
Supports 2-link kinematic solver:
  Shoulder -> Upper Arm -> Elbow -> Forearm -> Wrist -> Hand
Handles target-directed poses:
  point, wave, wipe_face, pray, reach, give, receive, carry, cook
"""

import math
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
        }
    }
    
    def __init__(self):
        self.solver = ArmIKSolver(upper_arm_len=105.0, forearm_len=95.0)
        
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
        
    def render_arm_overlay(self, canvas: Image.Image, char_id: str,
                           gesture: str, progress: float = 1.0,
                           audio_stress: float = 0.0,
                           world_target: tuple = None) -> Image.Image:
        """
        Renders articulated arm overlay onto the character canvas.
        Only renders for active gestures that diverge from the base illustrated pose.
        """
        if gesture in ["idle", "stand", "walk", "none"] or not gesture:
            return canvas
            
        # 1. Folded hands occlusion patch for Kodalu to prevent 3rd arm artifact
        working_canvas = canvas.copy()
        if char_id == "kodalu" and gesture in ["cook", "reach", "give", "receive", "point", "wave", "wipe_face"]:
            w, h = working_canvas.size
            patch_mask = Image.new("L", (w, h), 0)
            p_draw = ImageDraw.Draw(patch_mask)
            p_draw.polygon([(225, 395), (360, 395), (365, 485), (220, 485)], fill=255)
            patch_mask = patch_mask.filter(ImageFilter.GaussianBlur(radius=5.0))

            saree_patch = Image.new("RGBA", (w, h), (155, 38, 42, 255))
            pd = ImageDraw.Draw(saree_patch)
            pd.line([(240, 400), (280, 485)], fill=(130, 28, 32, 255), width=4)
            pd.line([(285, 395), (325, 485)], fill=(185, 145, 40, 180), width=3)
            pd.line([(310, 395), (350, 480)], fill=(130, 28, 32, 255), width=3)
            working_canvas = Image.composite(saree_patch, working_canvas, patch_mask)

        cfg = self.CHAR_ARM_CONFIG.get(char_id, self.CHAR_ARM_CONFIG["kodalu"])
        shoulder = cfg["shoulder_r"]
        target = self.get_gesture_target(gesture, char_id, progress=progress, audio_stress=audio_stress)
        
        # Solve IK
        elbow_bend = 1 if gesture not in ["wipe_face", "wave"] else -1
        ik_res = self.solver.solve_ik(shoulder, target, elbow_dir=elbow_bend)
        
        p0 = (int(ik_res["shoulder"][0]), int(ik_res["shoulder"][1]))
        pe = (int(ik_res["elbow"][0]), int(ik_res["elbow"][1]))
        pw = (int(ik_res["wrist"][0]), int(ik_res["wrist"][1]))
        
        w, h = working_canvas.size
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        skin = (*cfg["skin_color"], 255)
        skin_dark = (max(0, skin[0]-35), max(0, skin[1]-30), max(0, skin[2]-25), 255)
        sleeve = (*cfg["sleeve_color"], 255)
        arm_thick = cfg["arm_thickness"]
        
        # 1. Upper Arm (Shoulder to Elbow)
        # Upper portion covered by blouse/sleeve
        draw.line([p0, pe], fill=sleeve, width=arm_thick + 4)
        draw.ellipse([(p0[0] - arm_thick//2 - 2, p0[1] - arm_thick//2 - 2),
                      (p0[0] + arm_thick//2 + 2, p0[1] + arm_thick//2 + 2)], fill=sleeve)
                      
        # Lower portion of upper arm (skin)
        sleeve_end = (int(p0[0] + (pe[0] - p0[0]) * 0.45), int(p0[1] + (pe[1] - p0[1]) * 0.45))
        draw.line([sleeve_end, pe], fill=skin, width=arm_thick)
        draw.ellipse([(pe[0] - arm_thick//2, pe[1] - arm_thick//2),
                      (pe[0] + arm_thick//2, pe[1] + arm_thick//2)], fill=skin)
                      
        # 2. Forearm (Elbow to Wrist)
        draw.line([pe, pw], fill=skin, width=int(arm_thick * 0.85))
        
        # 3. Bangles at wrist if female character
        if cfg["bangle_color"]:
            bangle = (*cfg["bangle_color"], 255)
            # Draw 3 golden rings at wrist
            for b_idx in [-6, -2, 2]:
                bx = int(pe[0] + (pw[0] - pe[0]) * 0.88) + b_idx
                by = int(pe[1] + (pw[1] - pe[1]) * 0.88)
                draw.ellipse([(bx - 10, by - 6), (bx + 10, by + 6)], outline=bangle, width=2)
                
        # 4. Hand Poses
        hw_dir_x = pw[0] - pe[0]
        hw_dir_y = pw[1] - pe[1]
        hand_len = math.sqrt(hw_dir_x**2 + hw_dir_y**2)
        if hand_len > 1e-4:
            nx = hw_dir_x / hand_len
            ny = hw_dir_y / hand_len
        else:
            nx, ny = 1.0, 0.0
            
        if gesture == "point":
            # Outstretched index finger pointing sharply along hand axis
            palm_pos = pw
            finger_tip = (int(pw[0] + nx * 38.0), int(pw[1] + ny * 38.0))
            draw.ellipse([(palm_pos[0] - 8, palm_pos[1] - 8), (palm_pos[0] + 8, palm_pos[1] + 8)], fill=skin)
            draw.line([palm_pos, finger_tip], fill=skin, width=7)
            draw.line([palm_pos, finger_tip], fill=skin_dark, width=1)
            draw.ellipse([(palm_pos[0] - 5, palm_pos[1] + 3), (palm_pos[0] + 5, palm_pos[1] + 12)], fill=skin_dark)
            
        elif gesture == "wipe_face":
            # Curled fingers gently dabbing cheek
            draw.ellipse([(pw[0] - 10, pw[1] - 10), (pw[0] + 10, pw[1] + 10)], fill=skin)
            draw.arc([(pw[0] - 12, pw[1] - 12), (pw[0] + 12, pw[1] + 12)], start=20, end=160, fill=skin_dark, width=2)
            
        elif gesture == "pray":
            # Two folded palms in Namaste
            draw.ellipse([(pw[0] - 8, pw[1] - 16), (pw[0] + 8, pw[1] + 16)], fill=skin)
            draw.line([(pw[0], pw[1] - 18), (pw[0], pw[1] + 14)], fill=skin_dark, width=2)
            
        elif gesture == "cook":
            # Hand holding wooden/metal spoon stirring in pot
            draw.ellipse([(pw[0] - 10, pw[1] + 4), (pw[0] + 10, pw[1] + 22)], fill=skin)
            draw.line([(pw[0], pw[1] + 10), (pw[0] + 35, pw[1] + 45)], fill=(170, 170, 170, 255), width=5)
            
        else:
            # Natural soft cupped hand
            hand_end = (int(pw[0] + nx * 24.0), int(pw[1] + ny * 24.0))
            draw.line([pw, hand_end], fill=skin, width=12)
            draw.ellipse([(hand_end[0] - 6, hand_end[1] - 6), (hand_end[0] + 6, hand_end[1] + 6)], fill=skin)

        working_canvas.alpha_composite(overlay)
        return working_canvas
