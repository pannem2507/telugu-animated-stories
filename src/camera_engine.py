"""
Camera Engine for Telugu Animated Stories
Handles shot types, camera interpolation, follow-walk tracking,
smooth transitions, over-the-shoulder framing, and object inserts.
Decoupled into ShotSpec configuration model (Phase 3).
"""

import os
import json
import math
from dataclasses import dataclass
from typing import Optional, Dict
from PIL import Image

@dataclass
class ShotSpec:
    """
    Specification for a cinematic camera shot framing.
    """
    name: str
    zoom: float = 1.0
    target_mode: str = "fixed"  # "fixed", "single_target", "two_shot", "object", "walk", "over_shoulder_left", "over_shoulder_right"
    offset_x: float = 0.0
    offset_y: float = 0.0
    center_ratio_x: float = 0.5
    center_ratio_y: float = 0.5

DEFAULT_SHOT_DEFS = {
    "establishing_wide": { "zoom": 1.0, "target_mode": "fixed", "center_ratio_x": 0.5, "center_ratio_y": 0.5 },
    "wide": { "zoom": 1.0, "target_mode": "fixed", "center_ratio_x": 0.5, "center_ratio_y": 0.5 },
    "static": { "zoom": 1.0, "target_mode": "fixed", "center_ratio_x": 0.5, "center_ratio_y": 0.5 },
    "wide_two_shot": { "zoom": 1.08, "target_mode": "two_shot", "offset_x": 300.0, "offset_y": 260.0 },
    "medium_two_shot": { "zoom": 1.15, "target_mode": "two_shot", "offset_x": 300.0, "offset_y": 260.0 },
    "two_shot": { "zoom": 1.15, "target_mode": "two_shot", "offset_x": 300.0, "offset_y": 260.0 },
    "medium_character": { "zoom": 1.25, "target_mode": "single_target", "offset_x": 300.0, "offset_y": 260.0 },
    "speaker_medium": { "zoom": 1.25, "target_mode": "single_target", "offset_x": 300.0, "offset_y": 260.0 },
    "speaker": { "zoom": 1.25, "target_mode": "single_target", "offset_x": 300.0, "offset_y": 260.0 },
    "kodalu_medium": { "zoom": 1.25, "target_mode": "single_target", "offset_x": 300.0, "offset_y": 260.0 },
    "maharshi_medium": { "zoom": 1.25, "target_mode": "single_target", "offset_x": 300.0, "offset_y": 260.0 },
    "speaker_closeup": { "zoom": 1.85, "target_mode": "single_target", "offset_x": 280.0, "offset_y": 150.0 },
    "closeup": { "zoom": 1.85, "target_mode": "single_target", "offset_x": 280.0, "offset_y": 150.0 },
    "kodalu_closeup": { "zoom": 1.85, "target_mode": "single_target", "offset_x": 280.0, "offset_y": 150.0 },
    "maharshi_closeup": { "zoom": 1.85, "target_mode": "single_target", "offset_x": 280.0, "offset_y": 150.0 },
    "reaction_closeup": { "zoom": 1.85, "target_mode": "single_target", "offset_x": 280.0, "offset_y": 150.0 },
    "maharshi_reaction": { "zoom": 1.85, "target_mode": "single_target", "offset_x": 280.0, "offset_y": 150.0 },
    "kodalu_reaction": { "zoom": 1.85, "target_mode": "single_target", "offset_x": 280.0, "offset_y": 150.0 },
    "insert_object": { "zoom": 1.38, "target_mode": "object", "center_ratio_x": 0.5, "center_ratio_y": 0.65 },
    "object_insert": { "zoom": 1.38, "target_mode": "object", "center_ratio_x": 0.5, "center_ratio_y": 0.65 },
    "magic_wide": { "zoom": 1.10, "target_mode": "fixed", "center_ratio_x": 0.5, "center_ratio_y": 0.52 },
    "follow_walk": { "zoom": 1.18, "target_mode": "walk", "offset_x": 300.0, "offset_y": 280.0 },
    "follow_exit": { "zoom": 1.18, "target_mode": "walk", "offset_x": 300.0, "offset_y": 280.0 },
    "over_shoulder_left": { "zoom": 1.28, "target_mode": "over_shoulder_left", "offset_x": 250.0, "offset_y": 240.0 },
    "over_shoulder_right": { "zoom": 1.28, "target_mode": "over_shoulder_right", "offset_x": 350.0, "offset_y": 240.0 }
}

class CameraEngine:
    """
    Controls dynamic camera viewport, smooth framing, follow-cam, and shot sizes.
    Driven by decoupled ShotSpec definitions.
    """
    def __init__(self, width: int = 1920, height: int = 1080, shot_defs: dict = None):
        self.width = width
        self.height = height
        self.current_zoom = 1.0
        self.current_cx = width / 2.0
        self.current_cy = height / 2.0
        self.target_zoom = 1.0
        self.target_cx = width / 2.0
        self.target_cy = height / 2.0
        
        self.shot_specs: Dict[str, ShotSpec] = {}
        self._init_shot_specs(shot_defs)

    def _init_shot_specs(self, custom_defs: dict = None):
        defs = dict(DEFAULT_SHOT_DEFS)
        if custom_defs:
            defs.update(custom_defs)
        else:
            # Try loading from project config if available
            try:
                from .project_config import load_project_config
                cfg = load_project_config()
                if hasattr(cfg, "shots") and cfg.shots:
                    defs.update(cfg.shots)
            except Exception:
                pass

        for name, data in defs.items():
            self.shot_specs[name] = ShotSpec(
                name=name,
                zoom=data.get("zoom", 1.0),
                target_mode=data.get("target_mode", "fixed"),
                offset_x=data.get("offset_x", 0.0),
                offset_y=data.get("offset_y", 0.0),
                center_ratio_x=data.get("center_ratio_x", 0.5),
                center_ratio_y=data.get("center_ratio_y", 0.5)
            )

    def register_shot(self, spec: ShotSpec):
        """Register or override a shot specification."""
        self.shot_specs[spec.name.lower()] = spec

    def apply_shot_spec(self, spec: ShotSpec, target_pos: tuple = None,
                        two_shot_targets: list = None, object_pos: tuple = None):
        """Apply target parameters directly from a ShotSpec."""
        self.target_zoom = spec.zoom
        mode = spec.target_mode

        if mode == "fixed":
            self.target_cx = self.width * spec.center_ratio_x
            self.target_cy = self.height * spec.center_ratio_y

        elif mode == "two_shot":
            if two_shot_targets and len(two_shot_targets) >= 2:
                x1, y1 = two_shot_targets[0]
                x2, y2 = two_shot_targets[1]
                self.target_cx = (x1 + x2) / 2.0 + spec.offset_x
                self.target_cy = (y1 + y2) / 2.0 + spec.offset_y
            else:
                self.target_cx = self.width / 2.0
                self.target_cy = self.height / 2.0

        elif mode in ["single_target", "walk"]:
            if target_pos:
                self.target_cx = target_pos[0] + spec.offset_x
                self.target_cy = target_pos[1] + spec.offset_y
            else:
                self.target_cx = self.width / 2.0
                self.target_cy = self.height / 2.0

        elif mode == "object":
            if object_pos:
                self.target_cx = object_pos[0]
                self.target_cy = object_pos[1]
            elif target_pos:
                self.target_cx = target_pos[0] + 200.0
                self.target_cy = target_pos[1] + 450.0
            else:
                self.target_cx = self.width * spec.center_ratio_x
                self.target_cy = self.height * spec.center_ratio_y

        elif mode == "over_shoulder_left":
            if two_shot_targets and len(two_shot_targets) >= 2:
                x2, y2 = two_shot_targets[1]
                self.target_cx = x2 + spec.offset_x
                self.target_cy = y2 + spec.offset_y
            else:
                self.target_cx = self.width / 2.0
                self.target_cy = self.height / 2.0

        elif mode == "over_shoulder_right":
            if two_shot_targets and len(two_shot_targets) >= 2:
                x1, y1 = two_shot_targets[0]
                self.target_cx = x1 + spec.offset_x
                self.target_cy = y1 + spec.offset_y
            else:
                self.target_cx = self.width / 2.0
                self.target_cy = self.height / 2.0

        else:
            self.target_cx = self.width / 2.0
            self.target_cy = self.height / 2.0

    def set_shot(self, shot_type: str, target_pos: tuple = None,
                 two_shot_targets: list = None, object_pos: tuple = None):
        """Sets target camera framing based on named shot type."""
        shot_key = shot_type.lower()
        spec = self.shot_specs.get(shot_key)
        if spec is None:
            spec = self.shot_specs.get("wide", ShotSpec(name="wide", zoom=1.0, target_mode="fixed"))
        self.apply_shot_spec(spec, target_pos=target_pos,
                            two_shot_targets=two_shot_targets,
                            object_pos=object_pos)

    def snap_to_target(self):
        """Instantly cuts camera viewport to target values without interpolation (for scene cuts)."""
        self.current_zoom = self.target_zoom
        self.current_cx = self.target_cx
        self.current_cy = self.target_cy

    def reset(self):
        """Resets camera to default wide shot centered viewport."""
        self.target_zoom = 1.0
        self.target_cx = self.width / 2.0
        self.target_cy = self.height / 2.0
        self.snap_to_target()

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
