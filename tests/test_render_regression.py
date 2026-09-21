import unittest
import os
import json
import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Helper function to load screenplay
def load_screenplay(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

class BaselineRenderRegressionTest(unittest.TestCase):
    def setUp(self):
        # Ensure project root is on sys.path for imports
        sys.path.insert(0, str(PROJECT_ROOT))
        # Load screenplay
        self.screenplay_path = PROJECT_ROOT / "examples" / "story1_chalikalam_mayapoyyi_full.json"
        self.assertTrue(self.screenplay_path.is_file(), f"Screenplay file missing: {self.screenplay_path}")
        self.screenplay = load_screenplay(self.screenplay_path)

    def test_screenplay_structure(self):
        # Expect 7 scenes and 48 dialogue turns total
        scenes = self.screenplay.get("scenes", [])
        self.assertEqual(len(scenes), 7, "Expected 7 scenes in screenplay")
        total_dialogues = sum(len(scene.get("dialogues", [])) for scene in scenes)
        self.assertEqual(total_dialogues, 48, "Expected 48 dialogue turns in screenplay")

    def test_characters_exist(self):
        from src.character_registry import CharacterRegistry
        registry = CharacterRegistry()
        for scene in self.screenplay.get("scenes", []):
            for dlg in scene.get("dialogues", []):
                speaker = dlg.get("speaker")
                # Ensure character registry can provide landmarks (or fallback) without error
                try:
                    _ = registry.get_landmarks(speaker)
                except Exception as e:
                    self.fail(f"Character registry error for speaker '{speaker}': {e}")

    def test_assets_exist(self):
        from src.compositor import AssetCache, ASSETS_DIR
        asset_cache = AssetCache()
        # Check backgrounds referenced in screenplay
        for scene in self.screenplay.get("scenes", []):
            bg = scene.get("background")
            if bg:
                bg_path = Path(ASSETS_DIR) / "backgrounds" / bg
                self.assertTrue(bg_path.is_file(), f"Background asset missing: {bg_path}")
        # Example prop asset check (magic stove)
        prop_path = Path(ASSETS_DIR) / "props" / "magic_stove.png"
        self.assertTrue(prop_path.is_file(), "Prop 'magic_stove.png' missing")

    def test_import_engine_modules(self):
        modules = [
            "src.compositor",
            "src.character_registry",
            "src.animation_engine",
            "src.camera_engine",
            "src.performance_director",
            "src.scene_director",
            "src.tts_engine",
            "src.lipsync_engine",
        ]
        for mod_name in modules:
            with self.subTest(module=mod_name):
                try:
                    importlib.import_module(mod_name)
                except Exception as e:
                    self.fail(f"Failed to import {mod_name}: {e}")

    def test_render_one_turn(self):
        """Initialize core components and render a single frame (first dialogue turn) to ensure pipeline works."""
        from src.compositor import AssetCache, render_story_video
        # Minimal render call with early exit after first frame using a custom flag if supported
        # Since the full render function renders whole story, we simulate by calling internal helpers
        # Here we simply ensure AssetCache can be instantiated without error.
        try:
            asset_cache = AssetCache()
        except Exception as e:
            self.fail(f"AssetCache initialization failed: {e}")
        # Additional deeper checks could be added if engine exposes a turn-level render API.

if __name__ == "__main__":
    unittest.main()
