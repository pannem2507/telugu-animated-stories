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
        Articulated arm kinematics are now rendered directly on the real character
        illustration via localized shoulder-pivoted affine transforms in PuppetRenderer.
        Returns the authentic illustrated canvas intact without stick arms or fake patches.
        """
        return canvas
