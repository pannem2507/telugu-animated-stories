"""
Telugu Animated Stories - Command Line Generator
Usage:
    python generate.py --script examples/sample_atha_kodalu.json --output output/atha_kodalu_animated.mp4
"""

import os
import sys
import argparse

# Fix Windows console UTF-8 printing
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from src.script_parser import load_script
from src.compositor import render_story_video
from src.asset_generator import create_backgrounds, create_character_puppets, create_sample_audio_assets

def main():
    parser = argparse.ArgumentParser(description="Automated Telugu 2D Animated Stories Video Generator")
    parser.add_argument("--script", type=str, default="examples/sample_atha_kodalu.json", help="Path to Telugu story JSON or TXT script")
    parser.add_argument("--output", type=str, default="output/atha_kodalu_animated.mp4", help="Path for rendered MP4 video")
    parser.add_argument("--fps", type=int, default=24, help="Frames per second (default: 24)")
    args = parser.parse_args()

    print("=" * 60)
    print("  🎬 TELUGU ANIMATED STORIES AUTOMATION PIPELINE")
    print("=" * 60)

    # 1. Ensure all assets exist
    print("\n[Step 1/3] Verifying character puppets, backgrounds, and audio...")
    create_backgrounds()
    create_character_puppets()
    create_sample_audio_assets()

    # 2. Parse and validate script
    print(f"\n[Step 2/3] Loading script: {args.script}")
    script_data = load_script(args.script)
    print(f"Title: {script_data.get('title', 'Untitled')}")
    print(f"Scenes count: {len(script_data['scenes'])}")

    # 3. Render video
    print(f"\n[Step 3/3] Generating voiceovers, lip-syncing, and rendering video...")
    output_path = render_story_video(script_data, output_mp4=args.output, fps=args.fps)

    print("\n" + "=" * 60)
    print("  ✅ COMPLETED SUCCESSFULLY!")
    print(f"  Exported Video: {output_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
