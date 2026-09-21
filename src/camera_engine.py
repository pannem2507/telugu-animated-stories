"""
Camera Engine for Telugu Animated Stories
Handles shot types, camera interpolation, follow-walk tracking,
smooth transitions, over-the-shoulder framing, and object inserts.
"""

import math
from PIL import Image

class CameraEngine:
    """
    Controls dynamic camera viewport, smooth framing, follow-cam, and shot sizes.
    Supported shots:
    - establishing_wide (1.0x)
    - wide (1.0x)
    - wide_two_shot (1.08x)
    - medium_two_shot / two_shot (1.15x)
    - medium_character / speaker_medium (1.25x)
    - speaker_closeup / closeup (1.35x)
    - reaction_closeup (1.35x)
    - insert_object / object_insert (1.38x)
    - magic_wide (1.10x)
    - follow_walk (1.18x)
    - follow_exit (1.15x)
    - over_shoulder_left / over_shoulder_right (1.25x)
    """
    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height
        self.current_zoom = 1.0
        self.current_cx = width / 2.0
        self.current_cy = height / 2.0
        self.target_zoom = 1.0
        self.target_cx = width / 2.0
        self.target_cy = height / 2.0
        
    def set_shot(self, shot_type: str, target_pos: tuple = None, two_shot_targets: list = None,
                 object_pos: tuple = None):
        shot = shot_type.lower()
        
        if shot in ["establishing_wide", "wide", "static"]:
            self.target_zoom = 1.0
            self.target_cx = self.width / 2.0
            self.target_cy = self.height / 2.0
            
        elif shot in ["wide_two_shot"]:
            self.target_zoom = 1.08
            if two_shot_targets and len(two_shot_targets) >= 2:
                x1, y1 = two_shot_targets[0]
                x2, y2 = two_shot_targets[1]
                self.target_cx = (x1 + x2) / 2.0 + 300.0
                self.target_cy = (y1 + y2) / 2.0 + 260.0
            else:
                self.target_cx = self.width / 2.0
                self.target_cy = self.height / 2.0
                
        elif shot in ["medium_two_shot", "two_shot"]:
            self.target_zoom = 1.15
            if two_shot_targets and len(two_shot_targets) >= 2:
                x1, y1 = two_shot_targets[0]
                x2, y2 = two_shot_targets[1]
                self.target_cx = (x1 + x2) / 2.0 + 300.0
                self.target_cy = (y1 + y2) / 2.0 + 260.0
            else:
                self.target_cx = self.width / 2.0
                self.target_cy = self.height / 2.0
                
        elif shot in ["medium_character", "speaker_medium", "speaker", "kodalu_medium", "maharshi_medium"] and target_pos:
            self.target_zoom = 1.25
            self.target_cx = target_pos[0] + 300.0
            self.target_cy = target_pos[1] + 260.0
            
        elif shot in ["speaker_closeup", "closeup", "kodalu_closeup", "maharshi_closeup"] and target_pos:
            self.target_zoom = 1.85
            self.target_cx = target_pos[0] + 280.0
            self.target_cy = target_pos[1] + 150.0
            
        elif shot in ["reaction_closeup", "maharshi_reaction", "kodalu_reaction"] and target_pos:
            self.target_zoom = 1.85
            self.target_cx = target_pos[0] + 280.0
            self.target_cy = target_pos[1] + 150.0
            
        elif shot in ["insert_object", "object_insert"]:
            self.target_zoom = 1.38
            if object_pos:
                self.target_cx = object_pos[0]
                self.target_cy = object_pos[1]
            elif target_pos:
                self.target_cx = target_pos[0] + 200.0
                self.target_cy = target_pos[1] + 450.0
            else:
                self.target_cx = self.width / 2.0
                self.target_cy = self.height * 0.65
                
        elif shot in ["magic_wide"]:
            self.target_zoom = 1.10
            self.target_cx = self.width / 2.0
            self.target_cy = self.height * 0.52
            
        elif shot in ["follow_walk", "follow_exit"] and target_pos:
            self.target_zoom = 1.18
            self.target_cx = target_pos[0] + 300.0
            self.target_cy = target_pos[1] + 280.0
            
        elif shot == "over_shoulder_left" and two_shot_targets and len(two_shot_targets) >= 2:
            self.target_zoom = 1.28
            # Focused on character 2 (right), looking past character 1 (left)
            x2, y2 = two_shot_targets[1]
            self.target_cx = x2 + 250.0
            self.target_cy = y2 + 240.0
            
        elif shot == "over_shoulder_right" and two_shot_targets and len(two_shot_targets) >= 2:
            self.target_zoom = 1.28
            x1, y1 = two_shot_targets[0]
            self.target_cx = x1 + 350.0
            self.target_cy = y1 + 240.0
            
        else:
            self.target_zoom = 1.0
            self.target_cx = self.width / 2.0
            self.target_cy = self.height / 2.0
            
    def update(self, smoothing: float = 0.12):
        """Smoothly interpolates current camera viewport towards target."""
        self.current_zoom += (self.target_zoom - self.current_zoom) * smoothing
        self.current_cx += (self.target_cx - self.current_cx) * smoothing
        self.current_cy += (self.target_cy - self.current_cy) * smoothing
        
    def apply(self, frame_img: Image.Image) -> Image.Image:
        zoom = self.current_zoom
        if zoom <= 1.01:
            return frame_img
            
        w, h = self.width, self.height
        crop_w = int(w / zoom)
        crop_h = int(h / zoom)
        
        cx = self.current_cx
        cy = self.current_cy
        
        # Clamp crop box within bounds
        left = int(max(0, min(w - crop_w, cx - crop_w / 2.0)))
        top = int(max(0, min(h - crop_h, cy - crop_h / 2.0)))
        right = left + crop_w
        bottom = top + crop_h
        
        cropped = frame_img.crop((left, top, right, bottom))
        return cropped.resize((w, h), Image.Resampling.BICUBIC)
