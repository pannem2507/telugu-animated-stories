import os
import sys
import math
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import shutil

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.animation_engine import WalkCycleController, IdleController, PuppetRenderer

ARTIFACT_DIR = r"C:\Users\Admin\.gemini\antigravity\brain\59b44c48-3dff-4df1-957f-2fe161cb485c"

def load_kodalu_parts():
    char_dir = os.path.join(ROOT_DIR, "assets", "characters", "kodalu")
    base_file = os.path.join(char_dir, "base.png")
    base_img = Image.open(base_file).convert("RGBA") if os.path.exists(base_file) else Image.new("RGBA", (600, 900), (0,0,0,0))
    
    clean_file = os.path.join(char_dir, "base_clean.png")
    eyes_blink_file = os.path.join(char_dir, "eyes_blink.png")
    eyes_open_file = os.path.join(char_dir, "eyes_open.png")
    
    parts = {
        "base": base_img,
        "base_clean": Image.open(clean_file).convert("RGBA") if os.path.exists(clean_file) else None,
        "eyes_open": Image.open(eyes_open_file).convert("RGBA") if os.path.exists(eyes_open_file) else None,
        "eyes_blink": Image.open(eyes_blink_file).convert("RGBA") if os.path.exists(eyes_blink_file) else None,
        "mouths": {}
    }
    for m in ["mouth_closed", "mouth_open_a", "mouth_open_e", "mouth_open_o", "mouth_teeth", "mouth_wide", "mouth_sad", "mouth_angry"]:
        m_path = os.path.join(char_dir, f"{m}.png")
        if os.path.exists(m_path):
            parts["mouths"][m] = Image.open(m_path).convert("RGBA")
    return parts

def load_background(width=1920, height=1080):
    bg_path = os.path.join(ROOT_DIR, "assets", "backgrounds", "village_winter_porch.png")
    if not os.path.exists(bg_path):
        bg_path = os.path.join(ROOT_DIR, "assets", "backgrounds", "village_kitchen.png")
    if os.path.exists(bg_path):
        bg = Image.open(bg_path).convert("RGBA")
        if bg.size != (width, height):
            bg = bg.resize((width, height), Image.Resampling.LANCZOS)
        return bg
    return Image.new("RGBA", (width, height), (135, 175, 185, 255))

def render_test_clip():
    out_dir = os.path.join(ROOT_DIR, "output")
    frames_dir = os.path.join(out_dir, "phase8_frames")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(frames_dir, exist_ok=True)
    
    out_video_path = os.path.join(out_dir, "phase8_kodalu_rig_test_v2.mp4")

    print(f"Initializing render: target -> {out_video_path}", flush=True)
    parts = load_kodalu_parts()
    bg = load_background(1920, 1080)
    
    walk_engine = WalkCycleController(fps=24)
    idle_controller = IdleController(seed=42, char_id="kodalu")
    
    fps = 24
    width, height = 1920, 1080
    total_frames = 240 # 10 seconds total

    # Video writer setup
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(out_video_path, fourcc, fps, (width, height))
    
    snapshots = {}

    print("Beginning frame composition loop...", flush=True)
    for f_idx in range(total_frames):
        frame_bg = bg.copy()
        
        # Section determination
        if f_idx < 48:
            # 1. IDLE (0..47, 2.0s)
            section_title = "1. IDLE - Breathing Sway, Resting Arms (Unconditional Overlay)"
            cur_x = 480
            cur_y = 180
            walk_state = None
            idle_state = idle_controller.evaluate(f_idx)
            gesture_state = None
            gesture_pose = "idle"
            orient = "3/4_right"
            
        elif f_idx < 120:
            # 2. WALK LEFT TO RIGHT (48..119, 3.0s)
            section_title = "2. WALK LEFT-TO-RIGHT - Saree Wave/Shear & Foot Ground Contact"
            walk_f = f_idx - 48
            start_x = 300
            target_x = 980
            t = walk_f / 72.0
            smooth_t = 3.0 * (t ** 2) - 2.0 * (t ** 3)
            cur_x = int(start_x + (target_x - start_x) * smooth_t)
            travel_dist = float(target_x - start_x)
            
            walk_state = walk_engine.evaluate(walk_f, walk_type="walk_right", total_walk_frames=72, char_id="kodalu", travel_distance=travel_dist)
            idle_state = None
            gesture_state = None
            gesture_pose = "walk"
            cur_y = 180 + int(walk_state.get("y_bob", 0.0))
            orient = "3/4_right"
            
        elif f_idx < 180:
            # 3. WAVE (120..179, 2.5s)
            section_title = "3. WAVE - Articulated Right Arm IK with Natural Elbow Bend"
            cur_x = 980
            cur_y = 180
            wave_f = f_idx - 120
            prog = wave_f / 60.0
            walk_state = None
            idle_state = idle_controller.evaluate(f_idx)
            gesture_state = {"progress": prog}
            gesture_pose = "wave"
            orient = "3/4_right"
            
        else:
            # 4. REACH (180..239, 2.5s)
            section_title = "4. REACH - Outstretched Arm at Waist Height with 2-Link IK Flex"
            cur_x = 980
            cur_y = 180
            reach_f = f_idx - 180
            t_reach = min(1.0, reach_f / 35.0)
            smooth_reach = 3.0 * (t_reach ** 2) - 2.0 * (t_reach ** 3)
            walk_state = None
            idle_state = idle_controller.evaluate(f_idx)
            gesture_state = {"progress": smooth_reach}
            gesture_pose = "reach"
            orient = "3/4_right"

        # Ambient ground shadow
        shadow_img = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
        sh_draw = ImageDraw.Draw(shadow_img)
        sh_cx = cur_x + 300
        sh_cy = cur_y + 865
        sh_w = 150
        sh_h = 24
        sh_draw.ellipse([sh_cx - sh_w // 2, sh_cy - sh_h // 2, sh_cx + sh_w // 2, sh_cy + sh_h // 2], fill=(20, 20, 30, 95))
        frame_bg.alpha_composite(shadow_img)
        
        # Render puppet
        is_blinking = ((f_idx + 12) % 65) in [0, 1, 2]
        sprite = PuppetRenderer.render_puppet(
            parts=parts,
            mouth_cue="mouth_closed",
            is_blinking=is_blinking,
            char_id="kodalu",
            emotion="neutral",
            emotion_intensity=0.5,
            gesture_pose=gesture_pose,
            frame_idx=f_idx,
            walk_state=walk_state,
            idle_state=idle_state,
            gesture_state=gesture_state,
            orientation=orient,
            scale=1.0
        )
        
        # Paste puppet onto frame background
        frame_bg.paste(sprite, (cur_x, cur_y), sprite)
        
        # Draw clean subtitle/info banner
        draw = ImageDraw.Draw(frame_bg)
        banner_h = 75
        banner_y = height - banner_h - 25
        draw.rectangle([(280, banner_y), (1640, banner_y + banner_h)], fill=(15, 20, 30, 210), outline=(230, 190, 70, 255), width=2)
        
        # Banner text
        title_text = f"Phase 8 Segmented Rig Test v2: {section_title}"
        frame_text = f"Frame {f_idx:03d}/240 ({(f_idx/24.0):.2f}s)"
        draw.text((310, banner_y + 14), title_text, fill=(255, 255, 255, 255))
        draw.text((310, banner_y + 44), frame_text, fill=(225, 215, 120, 255))
        
        # Save key snapshots
        if f_idx == 24:
            snapshots["frame_01_idle"] = frame_bg.copy()
        elif f_idx == 84:
            snapshots["frame_02_walk"] = frame_bg.copy()
        elif f_idx == 150:
            snapshots["frame_03_wave"] = frame_bg.copy()
        elif f_idx == 215:
            snapshots["frame_04_reach"] = frame_bg.copy()
            
        # Write to video
        bgr_frame = cv2.cvtColor(np.array(frame_bg.convert("RGB")), cv2.COLOR_RGB2BGR)
        writer.write(bgr_frame)
        
        if f_idx % 40 == 0:
            print(f"Rendered frame {f_idx}/{total_frames} ({f_idx*100//total_frames}%)", flush=True)

    writer.release()
    print(f"Video render complete: {out_video_path}", flush=True)
    
    # Save individual snapshots to output/phase8_frames/
    for name, img in snapshots.items():
        png_path = os.path.join(frames_dir, f"{name}.png")
        img.save(png_path)
        print(f"Saved snapshot: {png_path}", flush=True)
        
        # Also copy to artifact directory for embedding and inspection
        art_path = os.path.join(ARTIFACT_DIR, f"{name}.png")
        try:
            shutil.copy2(png_path, art_path)
            print(f"Copied snapshot to artifact dir: {art_path}", flush=True)
        except Exception as e:
            print(f"Warning: could not copy to artifact dir: {e}", flush=True)

if __name__ == "__main__":
    render_test_clip()
