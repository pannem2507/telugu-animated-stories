"""
Project Scaffolder for Telugu Animated Stories
Creates, validates, and manages animation project workspaces from starter templates (Phase 5).
"""

import os
import shutil
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

def create_project(target_dir: str, project_name: str = "New Animation Project",
                   template_dir: str = None) -> Path:
    """
    Creates a new standalone animation project by copying the template directory
    and populating a custom project.json manifest.
    """
    target_path = Path(target_dir).resolve()
    
    if template_dir:
        template_path = Path(template_dir).resolve()
    else:
        # Resolve templates/blank_animation_project relative to repository root
        template_path = Path(__file__).resolve().parent.parent / "templates" / "blank_animation_project"
        
    if not template_path.is_dir():
        raise FileNotFoundError(f"Template directory not found: {template_path}")
        
    # Copy directory tree
    os.makedirs(target_path, exist_ok=True)
    shutil.copytree(template_path, target_path, dirs_exist_ok=True)
    
    # Ensure all standard directories exist
    standard_dirs = ["assets", "characters", "props", "environments", "scenes", "audio", "output", "subtitles", "voices", "config"]
    for d in standard_dirs:
        (target_path / d).mkdir(parents=True, exist_ok=True)

    # Populate customized project.json
    project_json_path = target_path / "project.json"
    data = {}
    if project_json_path.is_file():
        try:
            with open(project_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
            
    if "project" not in data:
        data["project"] = {}
        
    data["project"]["name"] = project_name
    data["project"]["version"] = "0.1"
    data["project"]["schema_version"] = 1
    data["title"] = project_name
    
    if "paths" not in data:
        data["paths"] = {}
    for p in ["assets", "characters", "props", "environments", "scenes", "audio", "subtitles", "voices"]:
        if p not in data["paths"]:
            data["paths"][p] = p
            
    with open(project_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
        
    return target_path


def validate_project(project_dir: str) -> Dict[str, Any]:
    """
    Validates that a project workspace has a valid manifest, required directory
    structure, character definitions, and screenplays.
    """
    path = Path(project_dir).resolve()
    errors: List[str] = []
    warnings: List[str] = []
    dirs_checked: List[str] = []
    characters_found: List[str] = []
    scenes_count = 0
    proj_name = ""

    if not path.is_dir():
        return {
            "valid": False,
            "project_name": "",
            "errors": [f"Project directory does not exist: {path}"],
            "warnings": warnings,
            "directories_checked": dirs_checked,
            "characters_found": characters_found,
            "scenes_found": 0
        }

    # 1. Check project.json
    manifest_path = path / "project.json"
    if not manifest_path.is_file():
        errors.append(f"Missing required manifest: {manifest_path}")
    else:
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                mdata = json.load(f)
            proj_name = mdata.get("project", {}).get("name", mdata.get("title", ""))
            if not proj_name:
                warnings.append("No project name or title defined in project.json")
            if "paths" not in mdata and "characters" not in mdata:
                warnings.append("project.json does not define explicit paths")
        except Exception as e:
            errors.append(f"Invalid JSON in {manifest_path}: {e}")

    # 2. Check standard directories
    expected_dirs = ["characters", "props", "environments", "scenes"]
    for ed in expected_dirs:
        ed_path = path / ed
        dirs_checked.append(ed)
        if not ed_path.is_dir():
            warnings.append(f"Standard directory not found: {ed}/")

    # 3. Check character definitions
    chars_dir = path / "characters"
    if chars_dir.is_dir():
        for item in chars_dir.iterdir():
            if item.is_dir():
                c_json = item / "character.json"
                if c_json.is_file():
                    characters_found.append(item.name)
                else:
                    warnings.append(f"Character directory '{item.name}' missing character.json")

    # 4. Check screenplay / scenes
    scenes_dir = path / "scenes"
    if scenes_dir.is_dir():
        for s_file in scenes_dir.glob("*.json"):
            try:
                with open(s_file, "r", encoding="utf-8") as f:
                    sdata = json.load(f)
                if "scenes" in sdata and isinstance(sdata["scenes"], list):
                    scenes_count += len(sdata["scenes"])
            except Exception:
                warnings.append(f"Failed to parse screenplay file: {s_file.name}")

    is_valid = len(errors) == 0

    return {
        "valid": is_valid,
        "project_name": proj_name,
        "errors": errors,
        "warnings": warnings,
        "directories_checked": dirs_checked,
        "characters_found": characters_found,
        "scenes_found": scenes_count
    }


def list_templates(templates_dir: str = None) -> List[Dict[str, Any]]:
    """
    Returns a list of available project starter templates.
    """
    if templates_dir:
        t_path = Path(templates_dir).resolve()
    else:
        t_path = Path(__file__).resolve().parent.parent / "templates"

    results = []
    if t_path.is_dir():
        for item in t_path.iterdir():
            if item.is_dir() and (item / "project.json").is_file():
                meta = {}
                try:
                    with open(item / "project.json", "r", encoding="utf-8") as f:
                        meta = json.load(f)
                except Exception:
                    pass
                name = meta.get("project", {}).get("name", meta.get("title", item.name))
                results.append({
                    "id": item.name,
                    "name": name,
                    "path": str(item)
                })
    return results


def add_character(project_dir: str, char_id: str, char_name: str = None,
                  orientation: str = "3/4_right", scale: float = 1.0,
                  voice_model: str = "en-US-GuyNeural") -> Path:
    """
    Scaffolds a new character folder under characters/<char_id>/ with character.json.
    """
    path = Path(project_dir).resolve()
    char_dir = path / "characters" / char_id
    char_dir.mkdir(parents=True, exist_ok=True)
    (char_dir / "mouths").mkdir(exist_ok=True)

    char_data = {
        "id": char_id,
        "name": char_name or char_id.replace("_", " ").title(),
        "base_orientation": orientation,
        "scale": scale,
        "voice": {
            "provider": "edge-tts",
            "model": voice_model,
            "pitch": "+0Hz",
            "rate": "+0%"
        },
        "subtitle_color": [240, 240, 240],
        "arm_ik": {
            "shoulder_r": [380, 290],
            "shoulder_l": [420, 290],
            "skin_color": [215, 160, 120],
            "sleeve_color": [60, 100, 180],
            "arm_thickness": 22
        },
        "landmarks": {
            "brow_l_inner": [270, 115],
            "brow_l_peak": [245, 108],
            "brow_l_outer": [220, 120],
            "brow_r_inner": [300, 115],
            "brow_r_peak": [325, 108],
            "brow_r_outer": [350, 120],
            "eye_l": [250, 138],
            "eye_r": [310, 138],
            "mouth_c": [280, 175],
            "mouth_l": [255, 175],
            "mouth_r": [305, 175]
        }
    }

    with open(char_dir / "character.json", "w", encoding="utf-8") as f:
        json.dump(char_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return char_dir


def add_prop(project_dir: str, prop_id: str, prop_name: str = None,
             scale: float = 1.0) -> Path:
    """
    Scaffolds a new prop folder under props/<prop_id>/ with prop.json.
    """
    path = Path(project_dir).resolve()
    prop_dir = path / "props" / prop_id
    prop_dir.mkdir(parents=True, exist_ok=True)

    prop_data = {
        "id": prop_id,
        "name": prop_name or prop_id.replace("_", " ").title(),
        "asset": f"{prop_id}.png",
        "scale": scale,
        "attachment_points": {
            "waist_carry": {"offset_x": 160, "offset_y": 220},
            "hand_hold": {"offset_x": 140, "offset_y": 120}
        },
        "effects": {}
    }

    with open(prop_dir / "prop.json", "w", encoding="utf-8") as f:
        json.dump(prop_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return prop_dir


def add_scene(project_dir: str, scene_id: int = None,
              background: str = "default_stage", dialogues: list = None) -> Dict[str, Any]:
    """
    Appends a new scene to scenes/screenplay.json.
    """
    path = Path(project_dir).resolve()
    scenes_dir = path / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    screenplay_file = scenes_dir / "screenplay.json"

    if screenplay_file.is_file():
        try:
            with open(screenplay_file, "r", encoding="utf-8") as f:
                sp_data = json.load(f)
        except Exception:
            sp_data = {"scenes": []}
    else:
        sp_data = {"scenes": []}

    if "scenes" not in sp_data:
        sp_data["scenes"] = []

    actual_id = scene_id if scene_id is not None else len(sp_data["scenes"]) + 1
    new_scene = {
        "scene_id": actual_id,
        "background": background,
        "dialogues": dialogues or []
    }
    sp_data["scenes"].append(new_scene)

    with open(screenplay_file, "w", encoding="utf-8") as f:
        json.dump(sp_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return new_scene
