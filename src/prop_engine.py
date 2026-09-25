"""
Generic Interactive Prop Engine
Decouples props, items, and artifacts from hardcoded engine logic.
Supports attachment points (waist carry, hand hold, head wear),
multi-ring divine/magic halo glow FX, and ground contact shadows.
"""

import os
import json
import math
import numpy as np
from typing import Optional, Dict, Any
from PIL import Image, ImageDraw

class GenericPropManager:
    """
    Manages stage props dynamically from configuration.
    Supports manifest loading, presence tracking, dynamic attachments,
    and configurable rendering (halos, shadows, sprite blending).
    """
    def __init__(self, props_dir: str = None):
        self.props: Dict[str, dict] = {}
        self.props_dir = props_dir
        if self.props_dir and os.path.isdir(self.props_dir):
            self.load_all_props_from_dir(self.props_dir)

    @property
    def objects(self) -> dict:
        """Alias for backward compatibility with ObjectManager."""
        return self.props

    def _resolve_props_directory(self) -> str:
        if self.props_dir and os.path.isdir(self.props_dir):
            return self.props_dir
        try:
            from .project_config import load_project_config
            cfg = load_project_config()
            return str(cfg.resolve_path("props"))
        except Exception:
            return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "props"))

    def load_prop_config(self, prop_data: dict) -> dict:
        """Load a prop from a dictionary manifest."""
        prop_id = prop_data.get("id", "prop")
        asset_name = prop_data.get("asset", f"{prop_id}.png")
        scale = float(prop_data.get("scale", 1.0))
        anchor = prop_data.get("anchor", [0, 0])
        x = anchor[0] if len(anchor) > 0 else 0
        y = anchor[1] if len(anchor) > 1 else 0

        # Attachment points
        att_pts = prop_data.get("attachment_points", {})
        att_offsets = {}
        for att_name, att_cfg in att_pts.items():
            right = (att_cfg.get("offset_x_right", att_cfg.get("offset_x", 185)), att_cfg.get("offset_y", 245))
            left = (att_cfg.get("offset_x_left", att_cfg.get("offset_x", 100)), att_cfg.get("offset_y", 245))
            att_offsets[att_name] = {"right": right, "left": left}

        # Effects
        effects = prop_data.get("effects", {})
        glow_cfg = effects.get("glow", {})
        glow_color = tuple(glow_cfg.get("color", [255, 215, 60]))

        prop_entry = {
            "id": prop_id,
            "asset_name": asset_name,
            "x": x,
            "y": y,
            "scale": scale,
            "alpha": 0.0,
            "glow_intensity": 0.0,
            "glow_color": glow_color,
            "is_held": False,
            "held_by": None,
            "attachment_type": "waist_carry",
            "visible": False,
            "attachment_offsets": att_offsets or {
                "waist_carry": {"right": (185, 245), "left": (100, 245)}
            },
            "effects": effects
        }
        self.props[prop_id] = prop_entry
        return prop_entry

    def load_prop_file(self, filepath: str) -> Optional[dict]:
        """Load prop definition from a JSON file."""
        if os.path.isfile(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return self.load_prop_config(data)
            except Exception:
                return None
        return None

    def load_prop_by_name(self, prop_name: str, props_dir: str = None) -> Optional[dict]:
        """
        Loads a prop manifest by name from props_dir or project config.
        Checks <props_dir>/<name>.json, <props_dir>/<name>/prop.json, and config/<name>.json.
        """
        if prop_name in self.props:
            return self.props[prop_name]

        p_dir = props_dir if props_dir and os.path.isdir(props_dir) else self._resolve_props_directory()
        candidates = [
            os.path.join(p_dir, f"{prop_name}.json"),
            os.path.join(p_dir, prop_name, "prop.json"),
            os.path.join(p_dir, prop_name, f"{prop_name}.json"),
            os.path.join(os.path.dirname(p_dir), "config", f"{prop_name}.json")
        ]

        for cand in candidates:
            if os.path.isfile(cand):
                loaded = self.load_prop_file(cand)
                if loaded:
                    return loaded
        return None

    def load_all_props_from_dir(self, props_dir: str = None) -> dict:
        """Loads all prop manifests found in the specified directory."""
        p_dir = props_dir or self._resolve_props_directory()
        if not os.path.isdir(p_dir):
            return self.props

        for entry in os.listdir(p_dir):
            full_path = os.path.join(p_dir, entry)
            if os.path.isfile(full_path) and entry.endswith(".json"):
                self.load_prop_file(full_path)
            elif os.path.isdir(full_path):
                manifest = os.path.join(full_path, "prop.json")
                if os.path.isfile(manifest):
                    self.load_prop_file(manifest)

        return self.props

    def register_prop(self, prop_id: str, asset_name: str, x: int = 0, y: int = 0,
                      scale: float = 1.0, glow_color: tuple = (255, 215, 60),
                      attachment_offsets: dict = None) -> dict:
        """Directly register a prop entry in-memory."""
        prop_entry = {
            "id": prop_id,
            "asset_name": asset_name,
            "x": x,
            "y": y,
            "scale": scale,
            "alpha": 0.0,
            "glow_intensity": 0.0,
            "glow_color": glow_color,
            "is_held": False,
            "held_by": None,
            "attachment_type": "waist_carry",
            "visible": False,
            "attachment_offsets": attachment_offsets or {
                "waist_carry": {"right": (185, 245), "left": (100, 245)}
            },
            "effects": {
                "glow": {"enabled": True, "color": list(glow_color)},
                "shadow": {"enabled": True}
            }
        }
        self.props[prop_id] = prop_entry
        return prop_entry

    def get_prop(self, prop_id: str, auto_load: bool = True) -> Optional[dict]:
        """Gets a prop by ID, optionally attempting to auto-load it from disk."""
        if prop_id not in self.props and auto_load:
            self.load_prop_by_name(prop_id)
        return self.props.get(prop_id)

    def reveal_prop(self, prop_id: str, progress: float):
        """Gradually reveals a prop on stage with organic glow flare."""
        prop = self.get_prop(prop_id)
        if prop:
            prop["visible"] = True
            prop["alpha"] = min(1.0, progress * 1.2)
            prop["glow_intensity"] = math.sin(min(1.0, progress) * math.pi) * 1.5 + 0.5

    def attach_to_character(self, prop_id: str, char_id: str, attachment_type: str = "waist_carry"):
        """Attaches a prop to a character's carrying/holding point."""
        prop = self.get_prop(prop_id)
        if prop:
            prop["is_held"] = True
            prop["held_by"] = char_id
            prop["attachment_type"] = attachment_type
            prop["visible"] = True
            prop["alpha"] = 1.0
            prop["glow_intensity"] = 0.35

    def detach_prop(self, prop_id: str, x: int = None, y: int = None):
        """Detaches a prop from a character and leaves it resting on stage."""
        prop = self.get_prop(prop_id)
        if prop:
            prop["is_held"] = False
            prop["held_by"] = None
            if x is not None:
                prop["x"] = x
            if y is not None:
                prop["y"] = y

    def update_held_position(self, prop_id: str, char_x: int, char_y: int,
                             y_bob: float = 0.0, orientation: str = "3/4_right",
                             scale: float = 1.0):
        """Updates held prop coordinates following character movement and walk bobbing."""
        prop = self.get_prop(prop_id)
        if prop and prop.get("is_held"):
            att_type = prop.get("attachment_type", "waist_carry")
            offsets = prop.get("attachment_offsets", {}).get(att_type, {})

            is_left = "left" in orientation
            off = offsets.get("left" if is_left else "right", (185, 245))

            prop["x"] = char_x + int(off[0] * scale)
            prop["y"] = char_y + int(off[1] * scale) + int(y_bob)
            prop["orientation"] = orientation
            prop["holder_scale"] = scale

    def render_prop(self, prop_id: str, canvas: Image.Image, prop_img: Image.Image, frame_idx: int = 0):
        """
        Renders a prop onto the stage canvas:
        1. Configurable halo glow (multi-ring golden flare)
        2. Ground contact shadow when resting
        3. Scaled, orientation-mirrored, alpha-blended sprite compositing
        """
        prop = self.props.get(prop_id)
        if not prop or not prop.get("visible") or prop.get("alpha", 0.0) <= 0.05 or not prop_img:
            return

        w, h = canvas.size
        s_alpha = prop["alpha"]
        s_x, s_y = prop["x"], prop["y"]
        glow_intensity = prop.get("glow_intensity", 0.0)
        effects = prop.get("effects", {})

        # 1. Halo Glow
        glow_cfg = effects.get("glow", {})
        glow_enabled = glow_cfg.get("enabled", True)
        glow_color = tuple(glow_cfg.get("color", prop.get("glow_color", (255, 215, 60))))

        if glow_enabled and glow_intensity > 0.05:
            glow_overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            g_draw = ImageDraw.Draw(glow_overlay)
            max_r = glow_cfg.get("max_radius", 180)
            halo_radius = int(max_r * glow_intensity + math.sin(frame_idx * 0.2) * 15)
            g_cx, g_cy = s_x + 150, s_y + 120

            rings = glow_cfg.get("rings", [
                {"radius_multiplier": 1.0, "alpha": 40},
                {"radius_multiplier": 0.7, "alpha": 80},
                {"radius_multiplier": 0.4, "alpha": 140}
            ])
            for ring in rings:
                r_step = int(halo_radius * ring.get("radius_multiplier", 1.0))
                alpha_step = ring.get("alpha", 60)
                c_alpha = int(alpha_step * min(1.0, glow_intensity))
                g_draw.ellipse([(g_cx - r_step, g_cy - r_step), (g_cx + r_step, g_cy + r_step)],
                               fill=(*glow_color, c_alpha))
            canvas.alpha_composite(glow_overlay)

        # 2. Ground shadow when resting
        shadow_cfg = effects.get("shadow", {})
        shadow_enabled = shadow_cfg.get("enabled", True)
        if shadow_enabled and not prop.get("is_held"):
            shadow_overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            sh_draw = ImageDraw.Draw(shadow_overlay)
            sh_draw.ellipse([(s_x + 60, s_y + 190), (s_x + 240, s_y + 225)],
                            fill=(20, 20, 25, int(70 * s_alpha)))
            canvas.alpha_composite(shadow_overlay)

        # 3. Prop Sprite
        rendered = prop_img
        # Mirror prop horizontally when held by character facing left
        if prop.get("is_held") and "left" in prop.get("orientation", ""):
            rendered = rendered.transpose(Image.FLIP_LEFT_RIGHT)

        # Apply combined scaling (prop scale * character scale)
        eff_scale = prop.get("scale", 1.0) * prop.get("holder_scale", 1.0)
        if abs(eff_scale - 1.0) > 0.01:
            nw = max(1, int(rendered.width * eff_scale))
            nh = max(1, int(rendered.height * eff_scale))
            rendered = rendered.resize((nw, nh), Image.Resampling.LANCZOS)

        if s_alpha < 0.98:
            p_copy = rendered.copy()
            p_arr = np.array(p_copy)
            p_arr[:, :, 3] = (p_arr[:, :, 3] * s_alpha).astype(np.uint8)
            rendered = Image.fromarray(p_arr)

        canvas.alpha_composite(rendered, dest=(s_x, s_y))
