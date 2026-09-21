"""
Localized Face Performance Engine for Telugu Animated Stories
Implements safe, localized deformation with strict lock masks:
- Locks hair, ears, glasses, bindi, and face boundaries
- Allows subtle feathered displacement of eyebrows, eyelids, mouth corners
- Curved organic tear trajectory (accumulate -> form -> flow -> wipe)
- Continuous emotion intensity (0.0 to 1.0)
"""

import os
import math
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter

class FacePerformanceEngine:
    """
    Safely animates character expressions using localized, bounded displacement fields
    and smooth feathered feature masks. Preserves base illustration fidelity.
    """
    
    # Character anatomical landmark registry
    LANDMARKS = {
        "atha": {
            "brow_l_inner": (332, 120),
            "brow_l_peak": (285, 115),
            "brow_l_outer": (255, 130),
            "brow_r_inner": (358, 120),
            "brow_r_peak": (395, 118),
            "brow_r_outer": (415, 132),
            "eye_l": (298, 142),
            "eye_r": (365, 144),
            "mouth_l": (324, 188),
            "mouth_c": (348, 185),
            "mouth_r": (372, 188),
            "bindi": (352, 124),
            "glasses_center": (335, 145),
            "glasses_box": (260, 115, 415, 175),
            "cheeks": ((298, 168), (365, 168)),
            "tear_origins": ((298, 160), (365, 160)),
            "tear_curves": [
                # Left eye tear path
                lambda t: (int(298 - 3.0 * math.sin(t * math.pi)), int(160 + 48 * t)),
                # Right eye tear path
                lambda t: (int(365 + 3.0 * math.sin(t * math.pi)), int(160 + 48 * t))
            ],
            "skin_color": (212, 148, 102),
            "has_glasses": True
        },
        "kodalu": {
            "brow_l_inner": (268, 116),
            "brow_l_peak": (235, 106),
            "brow_l_outer": (208, 118),
            "brow_r_inner": (284, 116),
            "brow_r_peak": (315, 110),
            "brow_r_outer": (342, 122),
            "eye_l": (239, 137),
            "eye_r": (298, 137),
            "mouth_l": (246, 174),
            "mouth_c": (268, 174),
            "mouth_r": (294, 171),
            "bindi": (268, 122),
            "glasses_box": None,
            "cheeks": ((238, 160), (300, 160)),
            "tear_origins": ((242, 146), (296, 146)),
            "tear_curves": [
                # Left cheek curved tear path
                lambda t: (int(242 - 2.5 * math.sin(t * math.pi * 0.8)), int(146 + 48 * t)),
                # Right cheek curved tear path
                lambda t: (int(296 + 2.5 * math.sin(t * math.pi * 0.8)), int(146 + 48 * t))
            ],
            "skin_color": (197, 128, 91),
            "has_glasses": False
        },
        "gent": {
            "brow_l_inner": (260, 110),
            "brow_l_peak": (235, 105),
            "brow_l_outer": (215, 115),
            "brow_r_inner": (285, 110),
            "brow_r_peak": (315, 105),
            "brow_r_outer": (335, 115),
            "eye_l": (235, 125),
            "eye_r": (300, 125),
            "mouth_l": (245, 165),
            "mouth_c": (275, 168),
            "mouth_r": (310, 165),
            "bindi": None,
            "glasses_box": None,
            "cheeks": ((230, 155), (310, 155)),
            "tear_origins": ((240, 135), (295, 135)),
            "tear_curves": [
                lambda t: (int(240 - 3.0 * math.sin(t * math.pi)), int(135 + 45 * t)),
                lambda t: (int(295 + 3.0 * math.sin(t * math.pi)), int(135 + 45 * t))
            ],
            "skin_color": (205, 140, 100),
            "has_glasses": False
        },
        "kanthamma": {
            "brow_l_inner": (268, 125),
            "brow_l_peak": (240, 115),
            "brow_l_outer": (215, 130),
            "brow_r_inner": (312, 125),
            "brow_r_peak": (340, 115),
            "brow_r_outer": (365, 130),
            "eye_l": (252, 165),
            "eye_r": (328, 165),
            "mouth_l": (260, 220),
            "mouth_c": (290, 220),
            "mouth_r": (320, 220),
            "bindi": (290, 135),
            "glasses_box": None,
            "cheeks": ((245, 185), (335, 185)),
            "tear_origins": ((252, 175), (328, 175)),
            "tear_curves": [
                lambda t: (int(252 - 2.5 * math.sin(t * math.pi)), int(175 + 45 * t)),
                lambda t: (int(328 + 2.5 * math.sin(t * math.pi)), int(175 + 45 * t))
            ],
            "skin_color": (205, 135, 95),
            "has_glasses": False
        },
        "maharshi": {
            "brow_l_inner": (265, 128),
            "brow_l_peak": (245, 120),
            "brow_l_outer": (225, 132),
            "brow_r_inner": (305, 128),
            "brow_r_peak": (325, 120),
            "brow_r_outer": (345, 132),
            "eye_l": (255, 148),
            "eye_r": (315, 148),
            "mouth_l": (265, 205),
            "mouth_c": (285, 205),
            "mouth_r": (305, 205),
            "bindi": (285, 115),
            "glasses_box": None,
            "cheeks": ((250, 170), (320, 170)),
            "tear_origins": ((255, 155), (315, 155)),
            "tear_curves": [
                lambda t: (int(255 - 2.0 * math.sin(t * math.pi)), int(155 + 45 * t)),
                lambda t: (int(315 + 2.0 * math.sin(t * math.pi)), int(155 + 45 * t))
            ],
            "skin_color": (215, 164, 123),
            "has_glasses": False
        },
        "kid": {
            "brow_l_inner": (275, 345),
            "brow_l_peak": (250, 335),
            "brow_l_outer": (225, 350),
            "brow_r_inner": (325, 345),
            "brow_r_peak": (350, 335),
            "brow_r_outer": (375, 350),
            "eye_l": (255, 380),
            "eye_r": (345, 380),
            "mouth_l": (270, 430),
            "mouth_c": (300, 430),
            "mouth_r": (330, 430),
            "bindi": (300, 345),
            "glasses_box": None,
            "cheeks": ((250, 400), (350, 400)),
            "tear_origins": ((255, 390), (345, 390)),
            "tear_curves": [
                lambda t: (int(255 - 2.0 * math.sin(t * math.pi)), int(390 + 40 * t)),
                lambda t: (int(345 + 2.0 * math.sin(t * math.pi)), int(390 + 40 * t))
            ],
            "skin_color": (205, 140, 100),
            "has_glasses": False
        },
        "father_in_law": {
            "brow_l_inner": (270, 150),
            "brow_l_peak": (245, 140),
            "brow_l_outer": (225, 152),
            "brow_r_inner": (330, 150),
            "brow_r_peak": (355, 140),
            "brow_r_outer": (375, 152),
            "eye_l": (255, 180),
            "eye_r": (345, 180),
            "mouth_l": (270, 240),
            "mouth_c": (300, 240),
            "mouth_r": (330, 240),
            "bindi": (300, 135),
            "glasses_center": (300, 180),
            "glasses_box": (220, 150, 380, 210),
            "cheeks": ((250, 205), (350, 205)),
            "tear_origins": ((255, 190), (345, 190)),
            "tear_curves": [
                lambda t: (int(255 - 2.0 * math.sin(t * math.pi)), int(190 + 45 * t)),
                lambda t: (int(345 + 2.0 * math.sin(t * math.pi)), int(190 + 45 * t))
            ],
            "skin_color": (215, 150, 105),
            "has_glasses": True
        }
    }
    
    @classmethod
    def get_landmarks(cls, char_id: str) -> dict:
        cid = char_id.lower() if char_id else "kodalu"
        if cid in cls.LANDMARKS:
            return cls.LANDMARKS[cid]
        alias_map = {
            "saroja": "kanthamma",
            "padma": "kanthamma",
            "sharada": "atha",
            "sudhakar": "gent",
            "ramesh": "gent",
            "husband": "gent",
            "son": "gent",
            "anamika": "kodalu",
            "harish": "kid",
            "kid_boy": "kid",
            "bhavya": "kid",
            "prasad": "father_in_law",
            "mamagaru": "father_in_law",
            "neighbor": "kanthamma",
            "neighbor_man": "gent"
        }
        mapped = alias_map.get(cid)
        if mapped and mapped in cls.LANDMARKS:
            return cls.LANDMARKS[mapped]
        if "padma" in cid:
            return cls.LANDMARKS["kanthamma"]
        if "atha" in cid:
            return cls.LANDMARKS["atha"]
        if "gent" in cid or "sudhakar" in cid or "ramesh" in cid:
            return cls.LANDMARKS["gent"]
        if "kanthamma" in cid or "saroja" in cid:
            return cls.LANDMARKS["kanthamma"]
        if "kid" in cid:
            return cls.LANDMARKS["kid"]
        if "father" in cid or "mamagaru" in cid:
            return cls.LANDMARKS["father_in_law"]
        if "maharshi" in cid:
            return cls.LANDMARKS["maharshi"]
        return cls.LANDMARKS["kodalu"]
    
    def __init__(self, max_displacement: float = 7.0):
        self.max_displacement = max_displacement
        
    def _build_safety_lock_mask(self, char_id: str, shape: tuple) -> np.ndarray:
        """
        Creates a float32 mask [0.0, 1.0] where 1.0 allows deformation and 0.0
        completely locks features (bindi, glasses frame, hair, ears, canvas edges).
        """
        h, w = shape[:2]
        mask = np.zeros((h, w), dtype=np.float32)
        lm = self.get_landmarks(char_id)
        
        # 1. Allow regions around brows (soft feather radius 32px)
        for key in ["brow_l_inner", "brow_l_peak", "brow_l_outer",
                    "brow_r_inner", "brow_r_peak", "brow_r_outer"]:
            pt = lm.get(key)
            if pt:
                cv2.circle(mask, pt, 30, 1.0, -1)
                
        # 2. Allow upper eyelid regions (soft radius 18px)
        for key in ["eye_l", "eye_r"]:
            pt = lm.get(key)
            if pt:
                cv2.circle(mask, (pt[0], pt[1] - 4), 18, 0.85, -1)
                
        # 3. Allow mouth corners and lips (radius 22px)
        for key in ["mouth_l", "mouth_c", "mouth_r"]:
            pt = lm.get(key)
            if pt:
                cv2.circle(mask, pt, 22, 0.90, -1)
                
        # 4. Feather the allowed mask smoothly
        mask = cv2.GaussianBlur(mask, (25, 25), 0)
        
        # 5. LOCK BINDI (set mask to 0 in bindi zone)
        bindi = lm.get("bindi")
        if bindi:
            bindi_lock = np.ones((h, w), dtype=np.float32)
            cv2.circle(bindi_lock, bindi, 14, 0.0, -1)
            bindi_lock = cv2.GaussianBlur(bindi_lock, (11, 11), 0)
            mask *= bindi_lock
            
        # 6. LOCK GLASSES if present (protect frames from bending)
        if lm.get("has_glasses") and lm.get("glasses_box"):
            gb = lm["glasses_box"]
            glasses_lock = np.ones((h, w), dtype=np.float32)
            cv2.rectangle(glasses_lock, (gb[0], gb[1]), (gb[2], gb[3]), 0.10, -1)
            glasses_lock = cv2.GaussianBlur(glasses_lock, (15, 15), 0)
            mask *= glasses_lock
            
        return np.clip(mask, 0.0, 1.0)
        
    def deform_face(self, base_img: Image.Image, char_id: str, emotion: str,
                    intensity: float = 1.0, audio_stress: float = 0.0,
                    frame_idx: int = 0, mouth_cue: str = "mouth_closed") -> Image.Image:
        """
        Deforms character face strictly within safe masked bounds.
        No full-head warping. Locks hair, glasses, bindi, ears.
        Seamlessly transforms base smiling mouth into authentic sorrow/fear expression.
        """
        if intensity <= 0.02 and emotion not in ["cry", "weep", "sad", "cower", "fear", "crying", "intense_crying"]:
            return base_img
            
        lm = self.get_landmarks(char_id)
            
        working_img = base_img.copy()
        
        # 1. SPECIAL ARTICULATION: Seamless Sorrow / Fear Mouth Replacement for Kodalu
        # When Kodalu (who has an open smiling mouth in base art) experiences sorrow or fear,
        # replace the smiling cavity with a feathered skin blend and draw a downturned sorrow lip seam.
        if char_id == "kodalu" and emotion in ["sad", "cry", "weep", "cower", "fear", "crying", "intense_crying"] and intensity > 0.08:
            arr_base = np.array(working_img)
            chin_skin = np.median(arr_base[186:192, 260:280, :3], axis=(0, 1)).astype(np.uint8)
            
            patch_mask = Image.new('L', working_img.size, 0)
            p_draw = ImageDraw.Draw(patch_mask)
            # Mask covering teeth and smile dimples
            p_draw.ellipse([238, 163, 298, 186], fill=int(255 * min(1.0, intensity * 1.3)))
            patch_mask = patch_mask.filter(ImageFilter.GaussianBlur(radius=3.0))
            
            patch_skin = Image.new('RGBA', working_img.size, (int(chin_skin[0]), int(chin_skin[1]), int(chin_skin[2]), 255))
            working_img = Image.composite(patch_skin, working_img, patch_mask)
            
            # Draw downturned sorrow lip seam
            c_draw = ImageDraw.Draw(working_img)
            quiver = math.sin(frame_idx * 1.8) * (0.8 * intensity)
            speech_open = (audio_stress * 3.2) if audio_stress > 0.05 else 0.0
            
            points = []
            for t_val in np.linspace(0, 1, 28):
                px = 248 + (288 - 248) * t_val
                py = 176 - (4.0 * intensity * math.sin(t_val * math.pi)) + quiver
                points.append((px, py))
                
            c_draw.line([(p[0], p[1]) for p in points], fill=(75, 25, 25, int(230 * intensity)), width=2)
            pout_pts = [(p[0], p[1] + 2.5 + speech_open) for p in points[6:22]]
            c_draw.line(pout_pts, fill=(140, 55, 55, int(170 * intensity)), width=2)
            
        img_np = np.array(working_img)
        h, w, c = img_np.shape
        
        safety_mask = self._build_safety_lock_mask(char_id, (h, w))
        
        grid_y, grid_x = np.mgrid[0:h, 0:w].astype(np.float32)
        dx = np.zeros((h, w), dtype=np.float32)
        dy = np.zeros((h, w), dtype=np.float32)
        
        def apply_radial_pull(cx: float, cy: float, radius: float, pull_x: float, pull_y: float):
            r_sq = (grid_x - cx) ** 2 + (grid_y - cy) ** 2
            m = np.clip(1.0 - np.sqrt(r_sq) / max(1.0, radius), 0.0, 1.0)
            smooth_m = (3.0 * m ** 2 - 2.0 * m ** 3)
            px = np.clip(pull_x, -self.max_displacement, self.max_displacement)
            py = np.clip(pull_y, -self.max_displacement, self.max_displacement)
            dx[...] -= smooth_m * px
            dy[...] -= smooth_m * py

        intensity = min(1.0, max(0.0, intensity))
        stress_scale = 1.0 + min(0.35, audio_stress * 0.35)
        eff_intensity = intensity * stress_scale
        
        # 2. ANGER / SCOLD DEFORMATION (Atha fierce scowl)
        if emotion in ["angry", "scold", "irritation", "peak_anger"]:
            pull_down = 5.5 * eff_intensity
            pull_in = 2.5 * eff_intensity
            apply_radial_pull(lm["brow_l_inner"][0], lm["brow_l_inner"][1], 26, pull_in, pull_down)
            apply_radial_pull(lm["brow_r_inner"][0], lm["brow_r_inner"][1], 26, -pull_in, pull_down)
            
            apply_radial_pull(lm["brow_l_outer"][0], lm["brow_l_outer"][1], 24, -1.0, -2.5 * eff_intensity)
            apply_radial_pull(lm["brow_r_outer"][0], lm["brow_r_outer"][1], 24, 1.0, -2.5 * eff_intensity)
            
            apply_radial_pull(lm["eye_l"][0], lm["eye_l"][1] - 4, 18, 0.0, 2.0 * eff_intensity)
            apply_radial_pull(lm["eye_r"][0], lm["eye_r"][1] - 4, 18, 0.0, 2.0 * eff_intensity)
            
            apply_radial_pull(lm["mouth_l"][0], lm["mouth_l"][1], 18, -2.0 * eff_intensity, -1.5 * eff_intensity)
            apply_radial_pull(lm["mouth_r"][0], lm["mouth_r"][1], 18, 2.0 * eff_intensity, -1.5 * eff_intensity)
            
        # 3. SADNESS / WEEP DEFORMATION (Kodalu grief brow arch)
        elif emotion in ["sad", "cry", "weep", "crying", "intense_crying"]:
            # Smooth full-brow grief arch (inward/inner lifts, outer sinks)
            apply_radial_pull(lm["brow_l_inner"][0], lm["brow_l_inner"][1], 36, 0.0, -4.5 * eff_intensity)
            apply_radial_pull(lm["brow_l_outer"][0], lm["brow_l_outer"][1], 30, 0.0, 3.0 * eff_intensity)
            
            apply_radial_pull(lm["brow_r_inner"][0], lm["brow_r_inner"][1], 36, 0.0, -4.5 * eff_intensity)
            apply_radial_pull(lm["brow_r_outer"][0], lm["brow_r_outer"][1], 30, 0.0, 3.0 * eff_intensity)
            
            # Heavy lids
            apply_radial_pull(lm["eye_l"][0], lm["eye_l"][1] - 2, 16, 0.0, 2.2 * eff_intensity)
            apply_radial_pull(lm["eye_r"][0], lm["eye_r"][1] - 2, 16, 0.0, 2.2 * eff_intensity)
            
        # 4. FEAR / COWER DEFORMATION
        elif emotion in ["cower", "fear"]:
            apply_radial_pull(lm["brow_l_inner"][0], lm["brow_l_inner"][1], 32, 0.0, -3.0 * eff_intensity)
            apply_radial_pull(lm["brow_r_inner"][0], lm["brow_r_inner"][1], 32, 0.0, -3.0 * eff_intensity)
            
            apply_radial_pull(lm["eye_l"][0], lm["eye_l"][1] - 2, 18, 0.0, 3.5 * eff_intensity)
            apply_radial_pull(lm["eye_r"][0], lm["eye_r"][1] - 2, 18, 0.0, 3.5 * eff_intensity)

        # 5. SURPRISE / WIDE EYES
        elif emotion in ["surprise", "shock"]:
            apply_radial_pull(lm["brow_l_inner"][0], lm["brow_l_inner"][1], 30, 0.0, -5.0 * eff_intensity)
            apply_radial_pull(lm["brow_r_inner"][0], lm["brow_r_inner"][1], 30, 0.0, -5.0 * eff_intensity)
            apply_radial_pull(lm["brow_l_outer"][0], lm["brow_l_outer"][1], 30, 0.0, -4.0 * eff_intensity)
            apply_radial_pull(lm["brow_r_outer"][0], lm["brow_r_outer"][1], 30, 0.0, -4.0 * eff_intensity)

        # 6. RELIEF / REVERENCE / JOY (Gentle softened brow and subtle upturn)
        elif emotion in ["relief", "reverence", "joy", "happy"]:
            if char_id == "atha":
                apply_radial_pull(lm["brow_l_inner"][0], lm["brow_l_inner"][1], 30, -1.0, -4.5 * eff_intensity)
                apply_radial_pull(lm["brow_r_inner"][0], lm["brow_r_inner"][1], 30, 1.0, -4.5 * eff_intensity)
                apply_radial_pull(lm["mouth_l"][0], lm["mouth_l"][1], 22, -2.5 * eff_intensity, 4.5 * eff_intensity)
                apply_radial_pull(lm["mouth_r"][0], lm["mouth_r"][1], 22, 2.5 * eff_intensity, 4.5 * eff_intensity)
            else:
                apply_radial_pull(lm["brow_l_inner"][0], lm["brow_l_inner"][1], 28, 0.0, -1.5 * eff_intensity)
                apply_radial_pull(lm["brow_r_inner"][0], lm["brow_r_inner"][1], 28, 0.0, -1.5 * eff_intensity)
                apply_radial_pull(lm["mouth_l"][0], lm["mouth_l"][1], 18, 0.0, 1.5 * eff_intensity)
                apply_radial_pull(lm["mouth_r"][0], lm["mouth_r"][1], 18, 0.0, 1.5 * eff_intensity)

        # 7. SPEECH VISUAL ARTICULATION & VISEMES (Telugu phoneme shapes A, O, E, teeth)
        mc = lm.get("mouth_c", (270, 175))
        ml = lm.get("mouth_l", (245, 175))
        mr = lm.get("mouth_r", (295, 175))
        v_stress = max(0.0, min(1.0, audio_stress))
        
        # When not already handling Kodalu crying mouth patch
        is_kodalu_crying = (char_id == "kodalu" and emotion in ["sad", "cry", "weep", "cower", "fear", "crying", "intense_crying"] and intensity > 0.08)
        if not is_kodalu_crying:
            if mouth_cue == "mouth_open_a":
                # Broad open vowel (Ah / Aa): pull lower lip down, slight upper lift
                open_depth = 4.5 + v_stress * 3.5
                apply_radial_pull(mc[0], mc[1] + 10, 18, 0.0, -open_depth)
                apply_radial_pull(mc[0], mc[1] - 4, 16, 0.0, open_depth * 0.35)
            elif mouth_cue == "mouth_open_o":
                # Pursed round vowel (Oh / Oo): lateral compression inward, vertical round opening
                pull_in = 3.0 + v_stress * 2.0
                round_depth = 3.5 + v_stress * 2.0
                apply_radial_pull(ml[0], ml[1], 16, pull_in, 0.0)
                apply_radial_pull(mr[0], mr[1], 16, -pull_in, 0.0)
                apply_radial_pull(mc[0], mc[1] + 8, 16, 0.0, -round_depth)
            elif mouth_cue in ["mouth_open_e", "mouth_wide"]:
                # Stretched wide vowel (Ee / Eh): pull mouth corners outward, moderate vertical separation
                pull_out = 3.8 + v_stress * 2.2
                open_e = 2.5 + v_stress * 1.8
                apply_radial_pull(ml[0], ml[1], 16, -pull_out, 0.0)
                apply_radial_pull(mr[0], mr[1], 16, pull_out, 0.0)
                apply_radial_pull(mc[0], mc[1] + 6, 16, 0.0, -open_e)
            elif mouth_cue == "mouth_teeth":
                # Sibilants / dental consonants: wide lateral stretch, tight vertical opening
                pull_out = 3.0 + v_stress * 1.5
                apply_radial_pull(ml[0], ml[1], 16, -pull_out, 0.0)
                apply_radial_pull(mr[0], mr[1], 16, pull_out, 0.0)
                apply_radial_pull(mc[0], mc[1] + 5, 14, 0.0, -1.8)
            elif v_stress > 0.08 and char_id != "kodalu":
                # Fallback audio stress opening
                speech_open = min(5.0, v_stress * 5.5)
                apply_radial_pull(mc[0], mc[1] + 8, 16, 0.0, -speech_open)
                apply_radial_pull(mc[0], mc[1] - 4, 16, 0.0, speech_open * 0.4)

        # Safety mask lock
        dx *= safety_mask
        dy *= safety_mask
        
        map_x = grid_x + dx
        map_y = grid_y + dy
        warped_np = cv2.remap(img_np, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        warped_img = Image.fromarray(warped_np, mode="RGBA")
        
        return warped_img

    def render_organic_tears(self, canvas: Image.Image, char_id: str,
                             tear_state: str = "flow", progress: float = 0.0,
                             intensity: float = 1.0) -> Image.Image:
        """
        Renders organic curved tears across the 4 physical states:
        - tear_accumulate: Glistening meniscus forms in lower eyelid
        - tear_form: Tear drop swells at inner canthus
        - tear_flow: Tear drop flows down curved cheek path leaving faint shimmering trail
        - tear_wipe: Hand wipes trail, leaving delicate fading sheen
        """
        if intensity <= 0.05 or tear_state == "none":
            return canvas
            
        lm = self.LANDMARKS.get(char_id, self.LANDMARKS["kodalu"])
        w, h = canvas.size
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        curves = lm.get("tear_curves", [])
        origins = lm.get("tear_origins", [])
        
        t = max(0.0, min(1.0, progress))
        
        if tear_state == "accumulate":
            for orig in origins:
                cx, cy = orig
                draw.arc([(cx - 10, cy - 3), (cx + 10, cy + 5)], start=10, end=170,
                         fill=(210, 240, 255, int(160 * intensity * t)), width=2)
                draw.ellipse([(cx - 2, cy), (cx + 2, cy + 3)],
                             fill=(255, 255, 255, int(220 * intensity * t)))
                             
        elif tear_state == "form":
            for orig in origins:
                cx, cy = orig
                radius = int(2 + 2.5 * t * intensity)
                draw.ellipse([(cx - radius, cy - radius), (cx + radius, cy + radius)],
                             fill=(170, 225, 255, int(220 * intensity)))
                draw.ellipse([(cx - 1, cy - 1), (cx + 1, cy + 1)],
                             fill=(255, 255, 255, 255))
                             
        elif tear_state == "flow":
            for curve_fn in curves:
                steps = max(4, int(15 * t))
                pts = [curve_fn(s / float(steps) * t) for s in range(steps + 1)]
                for i in range(len(pts) - 1):
                    p1, p2 = pts[i], pts[i+1]
                    draw.line([p1, p2], fill=(190, 230, 255, int(120 * intensity)), width=2)
                    draw.line([p1, p2], fill=(255, 255, 255, int(170 * intensity)), width=1)
                    
                drop_pos = curve_fn(t)
                dx, dy = drop_pos
                draw.ellipse([(dx - 3, dy - 3), (dx + 3, dy + 4)], fill=(160, 220, 255, int(235 * intensity)))
                draw.ellipse([(dx - 1, dy - 1), (dx + 1, dy + 1)], fill=(255, 255, 255, 255))
                
        elif tear_state == "wipe":
            wipe_alpha = int(100 * intensity * (1.0 - t))
            if wipe_alpha > 5:
                for curve_fn in curves:
                    steps = 12
                    pts = [curve_fn(s / float(steps)) for s in range(steps + 1)]
                    for i in range(len(pts) - 1):
                        p1, p2 = pts[i], pts[i+1]
                        draw.line([p1, p2], fill=(200, 235, 255, wipe_alpha), width=3)
                        
        canvas.alpha_composite(overlay)
        return canvas
