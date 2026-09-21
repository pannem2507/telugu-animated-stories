"""
Generic Interactive Prop Engine
Decouples props, items, and artifacts from hardcoded engine logic.
Supports attachment points (waist carry, hand hold, head wear),
multi-ring divine/magic halo glow FX, and ground contact shadows.
"""

import math
from PIL import Image, ImageDraw

class GenericPropManager:
    """
    Manages stage props dynamically from configuration.
    """
    def __init__(self):
        self.props = {}

    def register_prop(self, prop_id: str, asset_name: str, x: int = 0, y: int = 0,
                      scale: float = 1.0, glow_color: tuple = (255, 215, 60),
                      attachment_offsets: dict = None):
        self.props[prop_id] = {
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
            }
        }

    def get_prop(self, prop_id: str) -> dict:
        return self.props.get(prop_id)

    def reveal_prop(self, prop_id: str, progress: float):
        if prop_id in self.props:
            prop = self.props[prop_id]
            prop["visible"] = True
            prop["alpha"] = min(1.0, progress * 1.2)
            prop["glow_intensity"] = math.sin(min(1.0, progress) * math.pi) * 1.5 + 0.5

    def attach_to_character(self, prop_id: str, char_id: str, attachment_type: str = "waist_carry"):
        if prop_id in self.props:
            prop = self.props[prop_id]
            prop["is_held"] = True
            prop["held_by"] = char_id
            prop["attachment_type"] = attachment_type
            prop["visible"] = True
            prop["alpha"] = 1.0
            prop["glow_intensity"] = 0.35

    def detach_prop(self, prop_id: str, x: int = None, y: int = None):
        if prop_id in self.props:
            prop = self.props[prop_id]
            prop["is_held"] = False
            prop["held_by"] = None
            if x is not None:
                prop["x"] = x
            if y is not None:
                prop["y"] = y

    def update_held_position(self, prop_id: str, char_x: int, char_y: int,
                             y_bob: float = 0.0, orientation: str = "3/4_right",
                             scale: float = 1.0):
        if prop_id in self.props and self.props[prop_id]["is_held"]:
            prop = self.props[prop_id]
            att_type = prop.get("attachment_type", "waist_carry")
            offsets = prop.get("attachment_offsets", {}).get(att_type, {})
            
            is_left = "left" in orientation
            off = offsets.get("left" if is_left else "right", (185, 245))
            
            prop["x"] = char_x + int(off[0] * scale)
            prop["y"] = char_y + int(off[1] * scale) + int(y_bob)

    def render_prop(self, prop_id: str, canvas: Image.Image, prop_img: Image.Image, frame_idx: int = 0):
        prop = self.props.get(prop_id)
        if not prop or not prop.get("visible") or prop.get("alpha", 0.0) <= 0.05 or not prop_img:
            return

        w, h = canvas.size
        s_alpha = prop["alpha"]
        s_x, s_y = prop["x"], prop["y"]
        glow_intensity = prop.get("glow_intensity", 0.0)
        glow_color = prop.get("glow_color", (255, 215, 60))

        # 1. Halo Glow
        if glow_intensity > 0.05:
            glow_overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            g_draw = ImageDraw.Draw(glow_overlay)
            halo_radius = int(180 * glow_intensity + math.sin(frame_idx * 0.2) * 15)
            g_cx, g_cy = s_x + 150, s_y + 120
            for r_step, alpha_step in [(halo_radius, 40), (int(halo_radius * 0.7), 80), (int(halo_radius * 0.4), 140)]:
                c_alpha = int(alpha_step * min(1.0, glow_intensity))
                g_draw.ellipse([(g_cx - r_step, g_cy - r_step), (g_cx + r_step, g_cy + r_step)],
                               fill=(*glow_color, c_alpha))
            canvas.alpha_composite(glow_overlay)

        # 2. Ground shadow when resting
        if not prop.get("is_held"):
            shadow_overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            sh_draw = ImageDraw.Draw(shadow_overlay)
            sh_x = s_x + 150
            sh_y = s_y + 240
            sh_draw.ellipse([(sh_x - 140, sh_y - 20), (sh_x + 140, sh_y + 20)], fill=(20, 20, 25, 75))
            canvas.alpha_composite(shadow_overlay)

        # 3. Prop Sprite
        if s_alpha < 0.98:
            p_copy = prop_img.copy()
            p_arr = np.array(p_copy)
            p_arr[:, :, 3] = (p_arr[:, :, 3] * s_alpha).astype(np.uint8)
            rendered = Image.fromarray(p_arr, mode="RGBA")
        else:
            rendered = prop_img

        canvas.alpha_composite(rendered, dest=(s_x, s_y))
