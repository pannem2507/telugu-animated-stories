"""
Script Parser for Telugu Animated Stories
Validates and parses JSON and plain-text story scripts into structured scene objects.
"""

import os
import sys
import json

# Fix Windows console UTF-8 printing
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def load_script(script_path: str) -> dict:
    """Loads and validates a script from JSON or converts a structured text format."""
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Script file not found: {script_path}")
        
    if script_path.endswith(".json"):
        with open(script_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        # Simple plain-text fallback parser
        data = parse_text_script(script_path)
        
    validate_script(data)
    return data

def parse_text_script(txt_path: str) -> dict:
    """Parses a simple line-by-line script format:
    # Title: My Story
    [Scene: village_kitchen]
    Atha: ఏమే కోడలా!
    Kodalu: ఇదిగో అత్తయ్య గారు!
    """
    with open(txt_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
        
    title = "Telugu Story"
    scenes = []
    current_scene = {
        "scene_id": 1,
        "background": "village_kitchen",
        "bgm": "village_bgm",
        "dialogues": []
    }
    
    for line in lines:
        if line.startswith("# Title:"):
            title = line.replace("# Title:", "").strip()
        elif line.startswith("[Scene:") and line.endswith("]"):
            bg_name = line[7:-1].strip()
            if current_scene["dialogues"]:
                scenes.append(current_scene)
                current_scene = {
                    "scene_id": len(scenes) + 1,
                    "background": bg_name,
                    "bgm": "village_bgm",
                    "dialogues": []
                }
            else:
                current_scene["background"] = bg_name
        elif ":" in line:
            char_name, text = line.split(":", 1)
            char_name = char_name.strip().lower()
            text = text.strip()
            current_scene["dialogues"].append({
                "character": char_name,
                "text": text,
                "action": "speaking"
            })
            
    if current_scene["dialogues"]:
        scenes.append(current_scene)
        
    return {
        "title": title,
        "scenes": scenes
    }

def validate_script(data: dict):
    if "scenes" not in data or not isinstance(data["scenes"], list):
        raise ValueError("Script must contain a 'scenes' list.")
    if len(data["scenes"]) == 0:
        raise ValueError("Script must contain at least one scene.")
        
    for s_idx, scene in enumerate(data["scenes"]):
        if "dialogues" not in scene or not isinstance(scene["dialogues"], list):
            raise ValueError(f"Scene {s_idx + 1} must contain a 'dialogues' list.")
        for d_idx, d in enumerate(scene["dialogues"]):
            if "character" not in d or "text" not in d:
                raise ValueError(f"Scene {s_idx + 1}, dialogue {d_idx + 1} missing character or text.")

if __name__ == "__main__":
    print("Script parser module loaded successfully.")
