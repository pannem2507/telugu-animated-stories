"""
Generic Character Registry & Configuration Loader
Decouples character identities, anatomical landmarks, Arm IK parameters,
base illustration orientations, and voice profiles from the core engine.
"""

import os
import json

class CharacterRegistry:
    """
    Manages and loads character configuration manifests.
    Provides dynamic resolution with fallback defaults for backward compatibility.
    """
    
    # Universal fallback landmarks (in 600x900 canonical puppet canvas coordinates)
    DEFAULT_LANDMARKS = {
        "atha": {
            "brow_l_inner": (332, 120), "brow_l_peak": (285, 115), "brow_l_outer": (255, 130),
            "brow_r_inner": (358, 120), "brow_r_peak": (395, 118), "brow_r_outer": (415, 132),
            "eye_l": (298, 142), "eye_r": (365, 144),
            "mouth_l": (324, 188), "mouth_c": (348, 185), "mouth_r": (372, 188),
            "bindi": (352, 124), "glasses_box": (260, 115, 415, 175),
            "cheeks": ((298, 168), (365, 168)),
            "tear_origins": ((298, 160), (365, 160)),
            "has_glasses": True
        },
        "kodalu": {
            "brow_l_inner": (268, 116), "brow_l_peak": (235, 106), "brow_l_outer": (208, 118),
            "brow_r_inner": (284, 116), "brow_r_peak": (315, 110), "brow_r_outer": (342, 122),
            "eye_l": (239, 137), "eye_r": (298, 137),
            "mouth_l": (246, 174), "mouth_c": (268, 174), "mouth_r": (294, 171),
            "bindi": (268, 122), "glasses_box": None,
            "cheeks": ((238, 160), (300, 160)),
            "tear_origins": ((242, 146), (296, 146)),
            "has_glasses": False
        },
        "gent": {
            "brow_l_inner": (260, 110), "brow_l_peak": (235, 105), "brow_l_outer": (215, 115),
            "brow_r_inner": (285, 110), "brow_r_peak": (315, 105), "brow_r_outer": (335, 115),
            "eye_l": (235, 125), "eye_r": (300, 125),
            "mouth_l": (245, 165), "mouth_c": (275, 168), "mouth_r": (310, 165),
            "bindi": None, "glasses_box": None,
            "cheeks": ((230, 155), (310, 155)),
            "tear_origins": ((240, 135), (295, 135)),
            "has_glasses": False
        },
        "kanthamma": {
            "brow_l_inner": (268, 125), "brow_l_peak": (240, 115), "brow_l_outer": (215, 130),
            "brow_r_inner": (312, 125), "brow_r_peak": (340, 115), "brow_r_outer": (365, 130),
            "eye_l": (252, 165), "eye_r": (328, 165),
            "mouth_l": (260, 220), "mouth_c": (290, 220), "mouth_r": (320, 220),
            "bindi": (290, 135), "glasses_box": None,
            "cheeks": ((245, 185), (335, 185)),
            "tear_origins": ((252, 175), (328, 175)),
            "has_glasses": False
        },
        "maharshi": {
            "brow_l_inner": (265, 128), "brow_l_peak": (245, 120), "brow_l_outer": (225, 132),
            "brow_r_inner": (305, 128), "brow_r_peak": (325, 120), "brow_r_outer": (345, 132),
            "eye_l": (255, 148), "eye_r": (315, 148),
            "mouth_l": (265, 205), "mouth_c": (285, 205), "mouth_r": (305, 205),
            "bindi": (285, 115), "glasses_box": None,
            "cheeks": ((250, 170), (320, 170)),
            "tear_origins": ((255, 155), (315, 155)),
            "has_glasses": False
        },
        "kid": {
            "brow_l_inner": (275, 345), "brow_l_peak": (250, 335), "brow_l_outer": (225, 350),
            "brow_r_inner": (325, 345), "brow_r_peak": (350, 335), "brow_r_outer": (375, 350),
            "eye_l": (255, 380), "eye_r": (345, 380),
            "mouth_l": (270, 430), "mouth_c": (300, 430), "mouth_r": (330, 430),
            "bindi": (300, 345), "glasses_box": None,
            "cheeks": ((250, 400), (350, 400)),
            "tear_origins": ((255, 390), (345, 390)),
            "has_glasses": False
        }
    }

    # Universal fallback arm configurations
    DEFAULT_ARM_CONFIGS = {
        "atha": {
            "shoulder_r": (410, 310), "shoulder_l": (440, 315),
            "skin_color": (212, 148, 102), "sleeve_color": (0, 160, 215),
            "bangle_color": (230, 185, 45), "arm_thickness": 24
        },
        "kodalu": {
            "shoulder_r": (365, 290), "shoulder_l": (380, 280),
            "skin_color": (197, 127, 91), "sleeve_color": (205, 215, 45),
            "bangle_color": (225, 180, 40), "arm_thickness": 20,
            "has_occlusion_patch": True
        },
        "gent": {
            "shoulder_r": (360, 260), "shoulder_l": (390, 265),
            "skin_color": (205, 140, 100), "sleeve_color": (75, 130, 75),
            "bangle_color": None, "arm_thickness": 22
        }
    }

    # Universal base orientations
    DEFAULT_BASE_ORIENTATIONS = {
        "kodalu": "3/4_left",
        "anamika": "3/4_left",
        "atha": "3/4_right",
        "sharada": "3/4_right",
        "gent": "3/4_right",
        "kanthamma": "3/4_right",
        "padma": "3/4_right",
        "saroja": "3/4_right",
        "maharshi": "3/4_right",
        "kid": "3/4_right"
    }

    def __init__(self, project_dir: str = None):
        self.project_dir = project_dir
        self.loaded_characters = {}
        if project_dir:
            self._load_project_characters()

    def _load_project_characters(self):
        chars_dir = os.path.join(self.project_dir, "characters")
        if os.path.exists(chars_dir):
            for c_name in os.listdir(chars_dir):
                cfg_path = os.path.join(chars_dir, c_name, "character.json")
                if os.path.exists(cfg_path):
                    try:
                        with open(cfg_path, "r", encoding="utf-8") as f:
                            self.loaded_characters[c_name.lower()] = json.load(f)
                    except Exception:
                        pass

    def get_landmarks(self, char_id: str) -> dict:
        cid = char_id.lower() if char_id else "kodalu"
        if cid in self.loaded_characters and "landmarks" in self.loaded_characters[cid]:
            return self.loaded_characters[cid]["landmarks"]
            
        # Check alias / fallback map
        if cid in self.DEFAULT_LANDMARKS:
            return self.DEFAULT_LANDMARKS[cid]
        if "atha" in cid or "sharada" in cid:
            return self.DEFAULT_LANDMARKS["atha"]
        if "gent" in cid or "sudhakar" in cid or "ramesh" in cid:
            return self.DEFAULT_LANDMARKS["gent"]
        if "kanthamma" in cid or "saroja" in cid or "padma" in cid:
            return self.DEFAULT_LANDMARKS["kanthamma"]
        if "maharshi" in cid:
            return self.DEFAULT_LANDMARKS["maharshi"]
        if "kid" in cid:
            return self.DEFAULT_LANDMARKS["kid"]
        return self.DEFAULT_LANDMARKS["kodalu"]

    def get_arm_config(self, char_id: str) -> dict:
        cid = char_id.lower() if char_id else "kodalu"
        if cid in self.loaded_characters and "arm_ik" in self.loaded_characters[cid]:
            return self.loaded_characters[cid]["arm_ik"]
        if cid in self.DEFAULT_ARM_CONFIGS:
            return self.DEFAULT_ARM_CONFIGS[cid]
        if "atha" in cid or "sharada" in cid:
            return self.DEFAULT_ARM_CONFIGS["atha"]
        if "gent" in cid or "sudhakar" in cid or "ramesh" in cid:
            return self.DEFAULT_ARM_CONFIGS["gent"]
        return self.DEFAULT_ARM_CONFIGS["kodalu"]

    def get_base_orientation(self, char_id: str) -> str:
        cid = char_id.lower() if char_id else "kodalu"
        if cid in self.loaded_characters and "base_orientation" in self.loaded_characters[cid]:
            return self.loaded_characters[cid]["base_orientation"]
        return self.DEFAULT_BASE_ORIENTATIONS.get(cid, "3/4_right")

    def should_flip(self, char_id: str, target_orientation: str) -> bool:
        base_orient = self.get_base_orientation(char_id)
        if "left" in target_orientation:
            return base_orient != "3/4_left"
        elif "right" in target_orientation:
            return base_orient != "3/4_right"
        return False
