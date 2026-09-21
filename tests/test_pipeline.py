"""
Automated unit tests for Telugu Animation System
Validates walk cycle kinematics, puppet articulation, camera transforms,
scene director blocking, and JSON script schema.
"""

import os
import sys
import unittest
import math
from PIL import Image

# Ensure project root is in path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.animation_engine import WalkCycleController, IdleController, GestureController, PuppetRenderer
from src.camera_engine import CameraEngine
from src.scene_director import SceneDirector
from src.script_parser import load_script, validate_script

class TestAnimationPipeline(unittest.TestCase):

    def test_walk_cycle_kinematics(self):
        wc = WalkCycleController(step_duration_s=0.4, fps=24)
        self.assertGreater(wc.cycle_frames, 0)
        
        # Test contact, recoil, and high point phases
        res_0 = wc.evaluate(0)
        res_quarter = wc.evaluate(wc.cycle_frames // 4)
        res_half = wc.evaluate(wc.cycle_frames // 2)
        
        self.assertIn('y_bob', res_0)
        self.assertIn('torso_roll', res_0)
        self.assertIn('stride_shear', res_0)
        self.assertIn('head_tilt', res_0)
        
        # Stride shear should oscillate symmetrically
        self.assertAlmostEqual(res_0['stride_shear'], 0.0, delta=1.0)
        self.assertGreater(abs(res_quarter['stride_shear']), 10.0)

    def test_idle_and_gesture(self):
        ic = IdleController()
        idle_res = ic.evaluate(15)
        self.assertTrue(0.98 <= idle_res['scale_y'] <= 1.02)
        
        # Test gestures
        shiver_res = GestureController.evaluate('shiver', 10, 50, True)
        self.assertNotEqual(shiver_res['jitter_x'], 0.0)
        
        angry_res = GestureController.evaluate('angry', 10, 50, True)
        self.assertGreater(angry_res['head_rot'], 0.0)

    def test_camera_engine(self):
        cam = CameraEngine(1920, 1080)
        cam.set_shot('wide')
        self.assertEqual(cam.target_zoom, 1.0)
        
        cam.set_shot('medium_character', target_pos=(400, 200))
        self.assertEqual(cam.target_zoom, 1.25)
        self.assertEqual(cam.target_cx, 700.0)
        
        # Test frame crop
        test_frame = Image.new("RGBA", (1920, 1080), (100, 150, 200, 255))
        cam.current_zoom = 1.25
        cam.current_cx = 700.0
        cam.current_cy = 460.0
        out_frame = cam.apply(test_frame)
        self.assertEqual(out_frame.size, (1920, 1080))

    def test_scene_director(self):
        director = SceneDirector()
        test_scene = {
            'dialogues': [
                {'character': 'atha', 'text': 'హలో'},
                {'character': 'kodalu', 'text': 'నమస్కారం'}
            ]
        }
        actors = director.setup_scene(test_scene)
        self.assertIn('atha', actors)
        self.assertIn('kodalu', actors)
        self.assertIn(actors['atha']['orientation'], ['three_quarter_right', '3/4_right'])
        self.assertIn(actors['kodalu']['orientation'], ['three_quarter_left', '3/4_left'])

    def test_script_validation(self):
        test_json = os.path.join(BASE_DIR, "examples", "test_animation_system.json")
        data = load_script(test_json)
        self.assertIn('scenes', data)
        self.assertGreater(len(data['scenes']), 0)

if __name__ == '__main__':
    unittest.main()
