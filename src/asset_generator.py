"""
Asset Generator for Telugu Animated Stories Pipeline
Procedurally generates starter character puppet parts (base body, eyes, mouth shapes)
and traditional Indian village backgrounds if not already present.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))

def create_backgrounds():
    bg_dir = os.path.join(ASSETS_DIR, "backgrounds")
    os.makedirs(bg_dir, exist_ok=True)
    
    # 1. Village Kitchen (Atha Kodalu Cooking Scene)
    kitchen_path = os.path.join(bg_dir, "village_kitchen.png")
    if not os.path.exists(kitchen_path):
        w, h = 1920, 1080
        img = Image.new("RGBA", (w, h), (245, 235, 220, 255))
        draw = ImageDraw.Draw(img)
        
        # Wall gradient/shading (warm mud/ochre wall)
        for y in range(int(h * 0.75)):
            color = (235 - int(y * 0.05), 215 - int(y * 0.05), 185 - int(y * 0.05), 255)
            draw.line([(0, y), (w, y)], fill=color)
            
        # Floor (Red oxide / polished village earthen floor)
        floor_y = int(h * 0.72)
        for y in range(floor_y, h):
            ratio = (y - floor_y) / (h - floor_y)
            r = int(170 + ratio * 30)
            g = int(55 + ratio * 20)
            b = int(45 + ratio * 20)
            draw.line([(0, y), (w, y)], fill=(r, g, b, 255))
            
        # Wall base skirting line
        draw.rectangle([(0, floor_y - 20), (w, floor_y)], fill=(120, 40, 30, 255))
        
        # Wooden shelf on top left
        draw.rectangle([(80, 260), (700, 290)], fill=(95, 55, 30, 255))
        # Brass / Clay pots on shelf
        for i in range(4):
            x = 120 + i * 140
            # Jar body
            draw.ellipse([(x, 170), (x + 90, 265)], fill=(210, 140, 50, 255), outline=(130, 80, 20), width=3)
            # Jar neck
            draw.rectangle([(x + 25, 150), (x + 65, 175)], fill=(230, 160, 60, 255), outline=(130, 80, 20), width=2)
            # Lid
            draw.ellipse([(x + 20, 145), (x + 70, 158)], fill=(190, 120, 40, 255))
            
        # Traditional Indian Clay Stove (Chulha / Poyyi) in the background center
        chulha_x = int(w * 0.5) - 150
        chulha_y = floor_y - 60
        draw.rounded_rectangle([(chulha_x, chulha_y), (chulha_x + 300, chulha_y + 110)], radius=30, fill=(160, 110, 80, 255), outline=(90, 60, 40), width=4)
        # Hearth opening (fire glow)
        draw.ellipse([(chulha_x + 80, chulha_y + 35), (chulha_x + 220, chulha_y + 95)], fill=(50, 30, 25, 255))
        draw.ellipse([(chulha_x + 110, chulha_y + 45), (chulha_x + 190, chulha_y + 85)], fill=(255, 110, 20, 255))
        draw.ellipse([(chulha_x + 130, chulha_y + 55), (chulha_x + 170, chulha_y + 80)], fill=(255, 230, 60, 255))
        
        # Cooking pot on top of stove
        draw.ellipse([(chulha_x + 60, chulha_y - 45), (chulha_x + 240, chulha_y + 25)], fill=(80, 85, 90, 255), outline=(40, 45, 50), width=3)
        draw.ellipse([(chulha_x + 80, chulha_y - 40), (chulha_x + 220, chulha_y - 20)], fill=(120, 125, 130, 255))
        
        # Big South Indian Clay Pickle Jars (Jaadis / Bharanis) on the floor
        for idx, pos in enumerate([(140, floor_y + 40), (280, floor_y + 20), (w - 380, floor_y + 30), (w - 240, floor_y + 50)]):
            jx, jy = pos
            # Bottom white body
            draw.ellipse([(jx, jy + 30), (jx + 120, jy + 180)], fill=(245, 240, 230, 255), outline=(80, 50, 30), width=3)
            # Top brown ceramic glazed shoulder
            draw.chord([(jx, jy + 25), (jx + 120, jy + 135)], start=180, end=360, fill=(140, 65, 20, 255), outline=(80, 50, 30), width=3)
            # Neck & Lid
            draw.rectangle([(jx + 35, jy), (jx + 85, jy + 30)], fill=(140, 65, 20, 255), outline=(80, 50, 30), width=2)
            draw.ellipse([(jx + 30, jy - 8), (jx + 90, jy + 12)], fill=(160, 75, 25, 255), outline=(80, 50, 30), width=2)
            
        # Traditional hanging garlic / dried chili garlands
        for gx in [900, 1050]:
            draw.line([(gx, 0), (gx, 220)], fill=(100, 60, 30, 255), width=3)
            for gy in range(60, 210, 25):
                draw.ellipse([(gx - 12, gy), (gx + 12, gy + 22)], fill=(200, 40, 30, 255))
                
        img.save(kitchen_path, "PNG")
        print(f"[Assets] Generated background: {kitchen_path}")

    # 2. Village Porch / Veranda (Arugu)
    porch_path = os.path.join(bg_dir, "village_porch.png")
    if not os.path.exists(porch_path):
        w, h = 1920, 1080
        img = Image.new("RGBA", (w, h), (140, 200, 240, 255)) # Sky
        draw = ImageDraw.Draw(img)
        
        # Distant village trees & greenery
        draw.ellipse([(-100, 350), (600, 750)], fill=(60, 130, 60, 255))
        draw.ellipse([(450, 320), (1200, 750)], fill=(80, 150, 70, 255))
        draw.ellipse([(1000, 300), (2000, 750)], fill=(50, 120, 50, 255))
        
        # Distant village house roofs
        draw.polygon([(200, 450), (450, 360), (700, 450)], fill=(185, 75, 45, 255))
        draw.rectangle([(230, 450), (670, 560)], fill=(235, 215, 180, 255))
        
        # Veranda floor
        floor_y = int(h * 0.65)
        for y in range(floor_y, h):
            ratio = (y - floor_y) / (h - floor_y)
            r = int(180 + ratio * 35)
            g = int(70 + ratio * 20)
            b = int(50 + ratio * 20)
            draw.line([(0, y), (w, y)], fill=(r, g, b, 255))
            
        # Veranda wooden pillars (Traditional South Indian style)
        for px in [180, w - 240]:
            # Stone base
            draw.rectangle([(px - 25, floor_y - 30), (px + 65, floor_y + 80)], fill=(120, 120, 125, 255), outline=(70, 70, 75), width=3)
            # Wooden carved pillar
            draw.rectangle([(px, 0), (px + 40, floor_y - 30)], fill=(105, 55, 25, 255), outline=(65, 30, 15), width=3)
            # Decorative capital
            draw.polygon([(px - 30, 120), (px + 70, 120), (px + 20, 160)], fill=(130, 70, 35, 255))
            
        # Mangalore tiled roof overhang on top
        draw.rectangle([(0, 0), (w, 90)], fill=(185, 70, 35, 255), outline=(100, 40, 20), width=4)
        for rx in range(0, w, 40):
            draw.line([(rx, 0), (rx, 90)], fill=(140, 50, 25, 255), width=3)
            
        img.save(porch_path, "PNG")
        print(f"[Assets] Generated background: {porch_path}")


def create_character_puppets():
    chars = {
        "atha": {
            "skin": (220, 165, 130),
            "saree": (30, 130, 75),       # Green traditional saree
            "saree_border": (225, 180, 40), # Gold border
            "blouse": (180, 30, 40),      # Red blouse
            "bindi": (180, 20, 20),       # Big red vermillion bindi
            "is_elder": True,
            "hair": (35, 35, 40)
        },
        "kodalu": {
            "skin": (235, 185, 145),
            "saree": (210, 40, 90),       # Vibrant Magenta/Pink saree
            "saree_border": (235, 200, 50),
            "blouse": (25, 120, 175),     # Blue blouse
            "bindi": (190, 20, 30),       # Cute round bindi
            "is_elder": False,
            "hair": (20, 20, 25)
        },
        "narrator": {
            "skin": (210, 155, 120),
            "saree": (225, 220, 200),     # Traditional white dhoti/shirt
            "saree_border": (190, 140, 30),
            "blouse": (210, 70, 40),      # Kurta
            "bindi": (200, 160, 40),
            "is_elder": True,
            "hair": (40, 40, 45)
        }
    }
    
    char_w, char_h = 600, 900
    
    for name, c in chars.items():
        cdir = os.path.join(ASSETS_DIR, "characters", name)
        os.makedirs(cdir, exist_ok=True)
        
        # 1. Base Body & Head (Without mouth and eyes)
        base_path = os.path.join(cdir, "base.png")
        if not os.path.exists(base_path):
            img = Image.new("RGBA", (char_w, char_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            skin_color = (*c["skin"], 255)
            skin_shadow = (max(0, c["skin"][0] - 35), max(0, c["skin"][1] - 35), max(0, c["skin"][2] - 35), 255)
            
            # --- Body / Saree ---
            saree_color = (*c["saree"], 255)
            saree_border = (*c["saree_border"], 255)
            blouse_color = (*c["blouse"], 255)
            
            # Torso & Shoulders
            draw.polygon([(180, 500), (420, 500), (450, 880), (150, 880)], fill=saree_color)
            # Saree Pallu across chest (diagonal drape)
            draw.polygon([(190, 500), (410, 570), (430, 880), (220, 880)], fill=saree_border)
            draw.polygon([(210, 510), (390, 580), (410, 880), (240, 880)], fill=saree_color)
            
            # Arms
            # Left arm
            draw.polygon([(180, 500), (130, 680), (190, 700), (220, 520)], fill=blouse_color)
            draw.polygon([(130, 680), (150, 820), (200, 810), (190, 700)], fill=skin_color)
            # Right arm (bent forward gesture)
            draw.polygon([(420, 500), (470, 670), (410, 690), (380, 520)], fill=blouse_color)
            draw.polygon([(470, 670), (450, 810), (390, 800), (410, 690)], fill=skin_color)
            # Gold bangles
            for by in [790, 800]:
                draw.rectangle([(145, by), (195, by + 5)], fill=(240, 200, 40, 255))
                draw.rectangle([(395, by), (445, by + 5)], fill=(240, 200, 40, 255))
                
            # Neck
            draw.rectangle([(260, 410), (340, 500)], fill=skin_color)
            draw.ellipse([(250, 480), (350, 515)], fill=skin_shadow)
            # Gold necklace (Mangalsutra / Thali)
            draw.arc([(240, 420), (360, 510)], start=20, end=160, fill=(240, 200, 50, 255), width=5)
            draw.ellipse([(290, 505), (310, 525)], fill=(230, 180, 30, 255))
            
            # --- Head & Face ---
            head_cx, head_cy = 300, 310
            # Hair back bun
            hair_color = (*c["hair"], 255)
            draw.ellipse([(head_cx - 130, head_cy - 120), (head_cx + 130, head_cy + 130)], fill=hair_color)
            if c["is_elder"]:
                # Jasmine flowers in bun
                for angle in range(0, 180, 30):
                    fx = head_cx - 100 + int(20 * math.cos(math.radians(angle)))
                    fy = head_cy - 40 + int(50 * math.sin(math.radians(angle)))
                    draw.ellipse([(fx, fy), (fx + 18, fy + 18)], fill=(255, 255, 240, 255), outline=(220, 220, 180), width=1)
                    
            # Face Oval
            draw.ellipse([(head_cx - 85, head_cy - 90), (head_cx + 85, head_cy + 105)], fill=skin_color, outline=(80, 50, 35, 120), width=2)
            
            # Front Hair Bangs
            draw.chord([(head_cx - 88, head_cy - 105), (head_cx + 88, head_cy + 10)], start=180, end=360, fill=hair_color)
            
            # Ears & Gold Jhumkas (Earrings)
            for ex in [head_cx - 95, head_cx + 85]:
                draw.ellipse([(ex, head_cy - 10), (ex + 14, head_cy + 25)], fill=skin_color)
                # Jhumka
                draw.ellipse([(ex + 2, head_cy + 25), (ex + 12, head_cy + 35)], fill=(245, 200, 40, 255))
                draw.polygon([(ex - 2, head_cy + 35), (ex + 16, head_cy + 35), (ex + 7, head_cy + 52)], fill=(245, 200, 40, 255))
                
            # Eyebrows
            brow_y = head_cy - 22
            if c["is_elder"]:
                draw.arc([(head_cx - 65, brow_y - 8), (head_cx - 15, brow_y + 12)], start=200, end=350, fill=hair_color, width=4)
                draw.arc([(head_cx + 15, brow_y - 8), (head_cx + 65, brow_y + 12)], start=190, end=340, fill=hair_color, width=4)
            else:
                draw.arc([(head_cx - 60, brow_y - 5), (head_cx - 15, brow_y + 10)], start=200, end=350, fill=hair_color, width=3)
                draw.arc([(head_cx + 15, brow_y - 5), (head_cx + 60, brow_y + 10)], start=190, end=340, fill=hair_color, width=3)
                
            # Nose
            draw.line([(head_cx - 2, head_cy - 5), (head_cx + 4, head_cy + 22)], fill=(160, 100, 70, 255), width=3)
            draw.arc([(head_cx - 14, head_cy + 15), (head_cx + 12, head_cy + 28)], start=30, end=170, fill=(160, 100, 70, 255), width=2)
            
            # Bindi (Bottu)
            bindi_y = head_cy - 25
            bindi_size = 11 if c["is_elder"] else 7
            draw.ellipse([(head_cx - bindi_size, bindi_y - bindi_size), (head_cx + bindi_size, bindi_y + bindi_size)], fill=(*c["bindi"], 255))
            
            img.save(base_path, "PNG")
            print(f"[Assets] Generated character base: {base_path}")
            
        # 2. Eyes States
        eyes_w, eyes_h = 180, 60
        
        # Eyes Open
        eyes_open_path = os.path.join(cdir, "eyes_open.png")
        if not os.path.exists(eyes_open_path):
            e_img = Image.new("RGBA", (eyes_w, eyes_h), (0, 0, 0, 0))
            e_draw = ImageDraw.Draw(e_img)
            # Left Eye
            e_draw.ellipse([(20, 15), (70, 45)], fill=(255, 255, 255, 255), outline=(30, 25, 30), width=2)
            e_draw.ellipse([(35, 18), (57, 42)], fill=(40, 25, 20, 255))
            e_draw.ellipse([(43, 23), (52, 32)], fill=(10, 10, 10, 255))
            e_draw.ellipse([(41, 21), (46, 26)], fill=(255, 255, 255, 255))
            
            # Right Eye
            e_draw.ellipse([(110, 15), (160, 45)], fill=(255, 255, 255, 255), outline=(30, 25, 30), width=2)
            e_draw.ellipse([(123, 18), (145, 42)], fill=(40, 25, 20, 255))
            e_draw.ellipse([(128, 23), (137, 32)], fill=(10, 10, 10, 255))
            e_draw.ellipse([(126, 21), (131, 26)], fill=(255, 255, 255, 255))
            
            # Kajal / Eyeliner
            e_draw.arc([(18, 12), (72, 43)], start=190, end=350, fill=(20, 20, 25, 255), width=3)
            e_draw.arc([(108, 12), (162, 43)], start=190, end=350, fill=(20, 20, 25, 255), width=3)
            e_img.save(eyes_open_path, "PNG")
            
        # Eyes Blink / Closed
        eyes_blink_path = os.path.join(cdir, "eyes_blink.png")
        if not os.path.exists(eyes_blink_path):
            b_img = Image.new("RGBA", (eyes_w, eyes_h), (0, 0, 0, 0))
            b_draw = ImageDraw.Draw(b_img)
            b_draw.arc([(20, 25), (70, 48)], start=20, end=160, fill=(35, 25, 30, 255), width=3)
            b_draw.arc([(110, 25), (160, 48)], start=20, end=160, fill=(35, 25, 30, 255), width=3)
            b_img.save(eyes_blink_path, "PNG")
            
        # 3. Mouth Shapes
        mw, mh = 120, 80
        mouth_types = {
            "mouth_closed": "closed",
            "mouth_open_a": "open_a",
            "mouth_open_e": "open_e",
            "mouth_open_o": "open_o",
            "mouth_teeth": "teeth",
            "mouth_wide": "wide"
        }
        
        for fname, mtype in mouth_types.items():
            m_path = os.path.join(cdir, f"{fname}.png")
            if not os.path.exists(m_path):
                m_img = Image.new("RGBA", (mw, mh), (0, 0, 0, 0))
                m_draw = ImageDraw.Draw(m_img)
                cx, cy = mw // 2, mh // 2
                
                lip_color = (195, 65, 80, 255) if not c["is_elder"] else (170, 75, 75, 255)
                mouth_inner = (80, 20, 25, 255)
                
                if mtype == "closed":
                    m_draw.arc([(cx - 30, cy - 8), (cx + 30, cy + 18)], start=20, end=160, fill=lip_color, width=4)
                    m_draw.arc([(cx - 28, cy - 14), (cx + 28, cy + 10)], start=20, end=160, fill=lip_color, width=3)
                elif mtype == "open_a":
                    m_draw.ellipse([(cx - 28, cy - 18), (cx + 28, cy + 22)], fill=lip_color)
                    m_draw.ellipse([(cx - 22, cy - 12), (cx + 22, cy + 16)], fill=mouth_inner)
                    m_draw.ellipse([(cx - 15, cy + 5), (cx + 15, cy + 18)], fill=(220, 90, 105, 255))
                    m_draw.rectangle([(cx - 16, cy - 12), (cx + 16, cy - 4)], fill=(255, 255, 255, 255))
                elif mtype == "open_e":
                    m_draw.rounded_rectangle([(cx - 38, cy - 14), (cx + 38, cy + 16)], radius=8, fill=lip_color)
                    m_draw.rounded_rectangle([(cx - 32, cy - 8), (cx + 32, cy + 10)], radius=4, fill=(255, 255, 255, 255), outline=mouth_inner, width=2)
                    m_draw.line([(cx - 30, cy + 1), (cx + 30, cy + 1)], fill=(180, 180, 180, 255), width=2)
                elif mtype == "open_o":
                    m_draw.ellipse([(cx - 18, cy - 22), (cx + 18, cy + 22)], fill=lip_color)
                    m_draw.ellipse([(cx - 12, cy - 16), (cx + 12, cy + 16)], fill=mouth_inner)
                elif mtype == "teeth":
                    m_draw.chord([(cx - 32, cy - 12), (cx + 32, cy + 18)], start=0, end=180, fill=lip_color)
                    m_draw.chord([(cx - 26, cy - 6), (cx + 26, cy + 14)], start=0, end=180, fill=(255, 255, 255, 255), outline=mouth_inner, width=2)
                elif mtype == "wide":
                    m_draw.ellipse([(cx - 38, cy - 26), (cx + 38, cy + 28)], fill=lip_color)
                    m_draw.ellipse([(cx - 30, cy - 18), (cx + 30, cy + 20)], fill=mouth_inner)
                    m_draw.rectangle([(cx - 22, cy - 18), (cx + 22, cy - 8)], fill=(255, 255, 255, 255))
                    m_draw.ellipse([(cx - 18, cy + 4), (cx + 18, cy + 20)], fill=(230, 95, 110, 255))
                    
                m_img.save(m_path, "PNG")

    print("[Assets] All character puppets and facial components generated successfully.")

def create_sample_audio_assets():
    """Generates a pleasant village background music loop if not present."""
    import numpy as np
    import wave
    
    audio_dir = os.path.join(ASSETS_DIR, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    bgm_path = os.path.join(audio_dir, "village_bgm.wav")
    
    if not os.path.exists(bgm_path):
        sample_rate = 44100
        duration = 16.0
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        
        notes = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25]
        audio_data = np.zeros_like(t)
        
        beat_len = 0.5
        total_beats = int(duration / beat_len)
        
        for b in range(total_beats):
            freq = notes[b % len(notes)]
            t_start = b * beat_len
            idx_start = int(t_start * sample_rate)
            idx_end = int((t_start + beat_len * 1.5) * sample_rate)
            if idx_end > len(t):
                idx_end = len(t)
            seg_t = t[idx_start:idx_end] - t_start
            
            envelope = np.exp(-seg_t * 4.0)
            tone = (0.6 * np.sin(2 * np.pi * freq * seg_t) +
                    0.3 * np.sin(2 * np.pi * freq * 2 * seg_t) +
                    0.1 * np.sin(2 * np.pi * freq * 3 * seg_t))
            audio_data[idx_start:idx_end] += tone * envelope * 0.15
            
        drone = (0.05 * np.sin(2 * np.pi * 130.81 * t) +
                 0.03 * np.sin(2 * np.pi * 196.00 * t))
        audio_data += drone
        
        audio_data = np.clip(audio_data, -0.9, 0.9)
        int16_data = (audio_data * 32767).astype(np.int16)
        
        with wave.open(bgm_path, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(int16_data.tobytes())
            
        print(f"[Assets] Generated acoustic village BGM: {bgm_path}")

if __name__ == "__main__":
    create_backgrounds()
    create_character_puppets()
    create_sample_audio_assets()
