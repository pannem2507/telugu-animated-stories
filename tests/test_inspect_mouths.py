import os
import cv2
import numpy as np
from PIL import Image, ImageDraw

def render_character_mouth(base_img: Image.Image, char_id: str, mouth_cue: str, emotion: str = "neutral") -> Image.Image:
    base = base_img.copy()
    arr = np.array(base)
    h, w, _ = arr.shape
    
    if char_id == "kodalu":
        mc = (265, 168)
        rx, ry = 28.0, 13.0
        skin_sample = arr[150, 265, :3].astype(np.float32)
        lip_color = (168, 62, 58)
        seam_color = (95, 30, 28)
    else:
        mc = (330, 185)
        rx, ry = 30.0, 15.0
        skin_sample = arr[165, 330, :3].astype(np.float32)
        lip_color = (152, 60, 56)
        seam_color = (85, 28, 26)
        
    # 1. Smoothly erase the baked-in open smile on base.png with character skin tone
    y_coords, x_coords = np.ogrid[:h, :w]
    dist = ((x_coords - mc[0]) / rx) ** 2 + ((y_coords - mc[1]) / ry) ** 2
    mask = np.clip(1.0 - dist, 0.0, 1.0).astype(np.float32)
    mask = (3.0 * mask**2 - 2.0 * mask**3)[:, :, None]
    
    skin_patch = np.zeros_like(arr[:, :, :3], dtype=np.float32)
    skin_patch[:, :] = skin_sample
    
    cleaned_rgb = (arr[:, :, :3].astype(np.float32) * (1.0 - mask) + skin_patch * mask).astype(np.uint8)
    arr[:, :, :3] = cleaned_rgb
    cleaned_base = Image.fromarray(arr)
    
    # 2. Composite requested mouth shape
    m_cue_str = str(mouth_cue).lower().strip() if mouth_cue else "mouth_closed"
    
    # Check if a non-empty mouth sprite exists
    m_path = f"assets/characters/{char_id}/{m_cue_str}.png"
    mouth_sprite = None
    if os.path.exists(m_path):
        sp = Image.open(m_path).convert("RGBA")
        if np.array(sp)[:, :, 3].max() > 0: # not empty
            mouth_sprite = sp
            
    if mouth_sprite is not None:
        cleaned_base.alpha_composite(mouth_sprite)
    else:
        # High-quality clean closed mouth overlay for idle / silence
        draw = ImageDraw.Draw(cleaned_base)
        cx, cy = mc
        if emotion in ["sad", "cry", "weep", "cower"]:
            # Subtle downturned sad curve
            draw.arc([cx - 16, cy, cx + 16, cy + 12], start=200, end=340, fill=seam_color, width=2)
        else:
            # Gentle natural closed lip seam
            draw.line([(cx - 15, cy), (cx + 15, cy)], fill=seam_color, width=2)
            # Upper lip peak & lower lip subtle fullness
            draw.line([(cx - 8, cy - 1), (cx + 8, cy - 1)], fill=lip_color, width=1)
            draw.line([(cx - 9, cy + 2), (cx + 9, cy + 2)], fill=lip_color, width=1)
            
    return cleaned_base

def test_generate_perfect_mouth_previews():
    for char in ["kodalu", "atha"]:
        base = Image.open(f"assets/characters/{char}/base.png").convert("RGBA")
        
        im_closed = render_character_mouth(base, char, "mouth_closed")
        im_open = render_character_mouth(base, char, "mouth_open_a")
        im_sad = render_character_mouth(base, char, "mouth_closed", emotion="sad")
        
        cx, cy = (265, 168) if char == "kodalu" else (330, 185)
        crop_box = (cx - 70, cy - 50, cx + 70, cy + 50)
        
        c_closed = im_closed.crop(crop_box)
        c_open = im_open.crop(crop_box)
        c_sad = im_sad.crop(crop_box)
        
        row = Image.new("RGBA", (420, 100), (255, 255, 255, 255))
        row.paste(c_closed, (0, 0), c_closed)
        row.paste(c_open, (140, 0), c_open)
        row.paste(c_sad, (280, 0), c_sad)
        
        out_p = os.path.abspath(f"scratch/perfect_mouth_{char}.png")
        row.save(out_p)
        print(f"\nGenerated: {out_p}")
        assert os.path.exists(out_p)
