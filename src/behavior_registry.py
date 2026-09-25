"""
Behavior Registry for Telugu Animated Stories
Decouples turn actions, blocking movements, and performance routines
from hardcoded engine logic (Phase 4).
"""

import os
import json
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class BehaviorDescriptor:
    name: str
    behavior_type: str = "movement"  # "movement", "action", "speech"
    start_x: Optional[int] = None
    target_x: Optional[int] = None
    start_mode: str = "fixed"        # "fixed", "actor_x"
    target_mode: str = "fixed"       # "fixed", "actor_x", "named_target"
    walk_type: str = "walk_right"
    orientation: str = "3/4_right"
    duration_s: float = 2.0
    set_present: bool = False
    performance: Optional[str] = None
    prop_trigger: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_movement(self) -> bool:
        return self.behavior_type == "movement"

    @property
    def is_entry(self) -> bool:
        if self.set_present:
            return True
        clean = self.name.lower()
        if clean.startswith("walk_in") or clean.startswith("enter") or clean.startswith("appear"):
            return True
        if (self.behavior_type == "movement" and self.target_mode == "actor_x"
                and self.start_x is not None and (self.start_x < 0 or self.start_x > 1920)):
            return True
        return False

    @property
    def is_exit(self) -> bool:
        clean = self.name.lower()
        if clean.startswith("walk_out") or clean.startswith("exit") or clean.startswith("leave"):
            return True
        if (self.behavior_type == "movement" and self.target_x is not None
                and (self.target_x < 0 or self.target_x > 1920)):
            return True
        return False

    @property
    def entry_side(self) -> Optional[str]:
        clean = self.name.lower()
        if "left" in clean or (self.start_x is not None and self.start_x < 0):
            return "left"
        if "right" in clean or (self.start_x is not None and self.start_x > 1280):
            return "right"
        return None


class BehaviorRegistry:
    """
    Central registry for scene actor behaviors and movement dynamics.
    """
    def __init__(self, behavior_defs: dict = None):
        self.behaviors: Dict[str, BehaviorDescriptor] = {}
        self._load_behaviors(behavior_defs)

    def _load_behaviors(self, custom_defs: dict = None):
        defs = {}
        if custom_defs:
            defs.update(custom_defs)
        else:
            # Attempt to load from project configuration
            try:
                from .project_config import load_project_config
                cfg = load_project_config()
                if hasattr(cfg, "behaviors") and cfg.behaviors:
                    defs.update(cfg.behaviors)
            except Exception:
                pass

        # If still empty, attempt direct read from config/behaviors.json
        if not defs:
            config_path = os.path.join(os.path.dirname(__file__), "..", "config", "behaviors.json")
            if os.path.isfile(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        defs = raw.get("behaviors", raw)
                except Exception:
                    pass

        for name, data in defs.items():
            self.register(name, data)

    def register(self, name: str, data: dict) -> BehaviorDescriptor:
        """Register or override a behavior descriptor dynamically."""
        desc = BehaviorDescriptor(
            name=name.lower(),
            behavior_type=data.get("type", "movement"),
            start_x=data.get("start_x"),
            target_x=data.get("target_x"),
            start_mode=data.get("start_mode", "fixed"),
            target_mode=data.get("target_mode", "fixed"),
            walk_type=data.get("walk_type", "walk_right"),
            orientation=data.get("orientation", "3/4_right"),
            duration_s=data.get("duration_s", 2.0),
            set_present=data.get("set_present", False),
            performance=data.get("performance"),
            prop_trigger=data.get("prop_trigger"),
            extra=data
        )
        self.behaviors[name.lower()] = desc
        return desc

    def get(self, action_name: str) -> Optional[BehaviorDescriptor]:
        if not action_name:
            return None
        clean = action_name.lower().strip()
        if clean in self.behaviors:
            return self.behaviors[clean]
        # Check underscore vs hyphen
        alt = clean.replace("-", "_")
        if alt in self.behaviors:
            return self.behaviors[alt]
        return None

    def is_movement_action(self, action_name: str) -> bool:
        if not action_name:
            return False
        desc = self.get(action_name)
        if desc:
            return desc.is_movement
        clean = action_name.lower().strip()
        return any(clean.startswith(prefix) for prefix in ["walk", "enter", "exit", "move", "run"])

    def is_entry_action(self, action_name: str) -> bool:
        if not action_name:
            return False
        desc = self.get(action_name)
        if desc:
            return desc.is_entry
        clean = action_name.lower().strip()
        return clean.startswith("walk_in") or clean.startswith("enter") or clean.startswith("appear")

    def is_exit_action(self, action_name: str) -> bool:
        if not action_name:
            return False
        desc = self.get(action_name)
        if desc:
            return desc.is_exit
        clean = action_name.lower().strip()
        return clean.startswith("walk_out") or clean.startswith("exit") or clean.startswith("leave")

    def get_entry_side(self, action_name: str) -> Optional[str]:
        if not action_name:
            return None
        desc = self.get(action_name)
        if desc and desc.entry_side:
            return desc.entry_side
        clean = action_name.lower().strip()
        if "left" in clean:
            return "left"
        if "right" in clean or clean in ["walk_in", "enter"]:
            return "right"
        return None

    def plan_movement(self, action_name: str, phys_actor: str, actors: dict,
                      target_tag: str, fps: int, turn_frames: int) -> dict:
        """
        Calculates movement plan based on registered BehaviorDescriptor.
        """
        desc = self.get(action_name)
        if not desc or desc.behavior_type != "movement" or not phys_actor or phys_actor not in actors:
            return {
                "is_walking": False,
                "walk_actor": None,
                "walk_type": "walk_right",
                "start_x": 0,
                "target_x": 0,
                "walk_frames": 0,
                "walk_orientation": "3/4_right"
            }

        cur_actor = actors[phys_actor]
        if desc.set_present:
            cur_actor["is_present"] = True

        # Determine start_x
        if desc.start_mode == "actor_x":
            start_x = cur_actor.get("x", 0)
        elif desc.start_x is not None:
            start_x = desc.start_x
        else:
            start_x = cur_actor.get("x", 0)

        # Determine target_x and orientation
        if desc.target_mode == "actor_x":
            target_x = cur_actor.get("x", 0)
            walk_orient = desc.orientation
            walk_type = desc.walk_type
        elif desc.target_mode == "named_target":
            if target_tag and target_tag in actors:
                target_actor_x = actors[target_tag]["x"]
                target_x = target_actor_x - 200 if target_actor_x > start_x else target_actor_x + 200
            elif target_tag == "door":
                target_x = 1500
            elif target_tag == "stove":
                target_x = 280
            else:
                target_x = 660
            walk_orient = "3/4_right" if target_x >= start_x else "3/4_left"
            walk_type = "walk_right" if target_x >= start_x else "walk_left"
        elif desc.target_mode == "relative":
            delta = desc.extra.get("delta_x", 320)
            target_x = max(80, min(1720, start_x + delta))
            walk_orient = desc.orientation if desc.orientation else ("3/4_right" if delta >= 0 else "3/4_left")
            walk_type = desc.walk_type if desc.walk_type else ("walk_right" if delta >= 0 else "walk_left")
        elif desc.name in ["walk_left", "walk_rl"]:
            target_x = max(80, start_x - 320)
            walk_orient = "3/4_left"
            walk_type = "walk_left"
        elif desc.name in ["walk_right", "walk_lr"]:
            target_x = min(1720, start_x + 320)
            walk_orient = "3/4_right"
            walk_type = "walk_right"
        elif desc.name == "walk":
            cur_orient = cur_actor.get("orientation", "3/4_right")
            if "left" in cur_orient:
                target_x = max(80, start_x - 300)
                walk_orient = "3/4_left"
                walk_type = "walk_left"
            else:
                target_x = min(1720, start_x + 300)
                walk_orient = "3/4_right"
                walk_type = "walk_right"
        elif desc.target_x is not None:
            target_x = desc.target_x
            walk_orient = desc.orientation
            walk_type = desc.walk_type
        else:
            target_x = cur_actor.get("x", 0)
            walk_orient = desc.orientation
            walk_type = desc.walk_type

        # Update actor orientation if set
        if desc.set_present or desc.is_movement:
            cur_actor["orientation"] = walk_orient

        if desc.is_exit:
            walk_frames = turn_frames
        elif desc.is_entry:
            pref_frames = int(desc.duration_s * fps)
            ratio_frames = int(turn_frames * 0.70)
            walk_frames = min(turn_frames, max(pref_frames, ratio_frames))
        else:
            walk_frames = min(turn_frames, int(desc.duration_s * fps))

        return {
            "is_walking": True,
            "walk_actor": phys_actor,
            "walk_type": walk_type,
            "start_x": start_x,
            "target_x": target_x,
            "walk_frames": walk_frames,
            "walk_orientation": walk_orient
        }
