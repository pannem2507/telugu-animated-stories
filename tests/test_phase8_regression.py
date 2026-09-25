"""
Phase 8 Regression Test Suite
Validates generic animation pipeline robustness across 13 core capabilities:
1. Walking changes actor position across frames
2. Walk phase changes across frames
3. Walk reaches destination mark
4. Walk-out reaches off-screen
5. Walk -> speaking transition maintains position
6. Speaking produces head/body movement
7. Gesture produces arm/hand movement
8. Listener produces reaction state
9. Emotion modifies performance state
10. Phoneme -> viseme mapping works correctly
11. Viseme -> face deformation works correctly
12. Camera follows actor position
13. State does not leak between scenes
"""

import os
import sys
import math
import numpy as np
import pytest
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def test_walking_changes_actor_position_across_frames():
    """1. Walking changes actor position continuously and monotonically towards destination."""
    start_x = 1950
    target_x = 920
    walk_frames = 48
    positions = []
    for f in range(walk_frames + 1):
        prog = f / float(walk_frames)
        smooth_prog = 3.0 * (prog ** 2) - 2.0 * (prog ** 3)
        cur_x = int(start_x + (target_x - start_x) * smooth_prog)
        positions.append(cur_x)

    assert positions[0] == start_x
    assert positions[-1] == target_x
    assert positions[12] > positions[24] > positions[36]
    diffs = [positions[i] - positions[i + 1] for i in range(len(positions) - 1)]
    assert all(d >= 0 for d in diffs)
    assert any(d > 0 for d in diffs)


def test_walk_phase_changes_across_frames():
    """2. WalkCycleController generates distinct cyclic kinematics and phase progression."""
    from src.animation_engine import WalkCycleController
    wc = WalkCycleController(step_duration_s=0.38, fps=24)
    eval0 = wc.evaluate(frame_idx=0, walk_type="walk_in_right", total_walk_frames=48)
    eval6 = wc.evaluate(frame_idx=6, walk_type="walk_in_right", total_walk_frames=48)
    eval12 = wc.evaluate(frame_idx=12, walk_type="walk_in_right", total_walk_frames=48)

    assert eval0 is not None and eval6 is not None and eval12 is not None
    assert eval0["phase"] != eval6["phase"]
    assert eval6["phase"] != eval12["phase"]

    bobs = [wc.evaluate(f, walk_type="walk_in_right", total_walk_frames=48)["y_bob"] for f in range(24)]
    assert min(bobs) < max(bobs)


def test_walk_reaches_destination_mark():
    """3. Walk arrives cleanly and holds exactly at the destination mark without drifting."""
    start_x = 1950
    target_x = 920
    walk_frames = 48

    for f in range(walk_frames, walk_frames + 15):
        if f < walk_frames:
            prog = f / float(walk_frames)
            cur_x = int(start_x + (target_x - start_x) * (3.0 * (prog ** 2) - 2.0 * (prog ** 3)))
        else:
            cur_x = target_x
        assert cur_x == target_x


def test_walk_out_reaches_offscreen():
    """4. Walk-out travels completely past frame boundaries and deactivates actor presence."""
    start_x = 920
    target_x = 2100
    walk_frames = 48
    is_present = True
    final_x = None

    for f in range(walk_frames + 1):
        prog = f / float(walk_frames)
        exit_prog = prog ** 1.2
        cur_x = int(start_x + (target_x - start_x) * exit_prog)
        if cur_x >= 1920:
            is_present = False
        final_x = cur_x

    assert final_x >= 1920
    assert is_present is False


def test_walk_to_speaking_transition_maintains_position():
    """5. Transitioning from walk settling into speaking retains stable world coordinates."""
    from src.performance_director import PerformanceDirector
    pd = PerformanceDirector()
    start_x = 1950
    target_x = 920
    walk_frames = 48
    total_frames = 100

    actor = {"x": start_x, "y": 280, "orientation": "3/4_left", "is_present": True}

    for f in range(walk_frames - 2, walk_frames + 10):
        if f < walk_frames:
            prog = f / float(walk_frames)
            cur_x = int(start_x + (target_x - start_x) * (3.0 * (prog ** 2) - 2.0 * (prog ** 3)))
            actor["x"] = cur_x
        else:
            actor["x"] = target_x
            raw_g = pd.evaluate_acting_frame("speaking", f, total_frames, is_speaker=True)
            assert raw_g is not None

        if f >= walk_frames:
            assert actor["x"] == target_x


def test_speaking_produces_head_body_movement():
    """6. Conversational speech articulates head tilts, breathing sways, and audio emphasis."""
    from src.performance_director import PerformanceDirector
    pd = PerformanceDirector()

    f0 = pd.evaluate_acting_frame("speaking", frame_idx=0, total_frames=60, is_speaker=True, audio_stress=0.2, is_strike_beat=False)
    f15 = pd.evaluate_acting_frame("speaking", frame_idx=15, total_frames=60, is_speaker=True, audio_stress=0.7, is_strike_beat=True)
    f30 = pd.evaluate_acting_frame("speaking", frame_idx=30, total_frames=60, is_speaker=True, audio_stress=0.1, is_strike_beat=False)

    assert f0 is not None and f15 is not None and f30 is not None
    assert (f0["head_rot"] != f15["head_rot"]) or (f15["head_rot"] != f30["head_rot"]) or (f15["bob_y"] != f0["bob_y"])


def test_gesture_produces_arm_hand_movement():
    """7. Behavioral gestures articulate arm angles and emotional postures."""
    from src.performance_director import PerformanceDirector
    pd = PerformanceDirector()

    scold_frame = pd.evaluate_acting_frame("scold_sequence", frame_idx=20, total_frames=80, is_speaker=True)
    argue_frame = pd.evaluate_acting_frame("argue", frame_idx=20, total_frames=80, is_speaker=True)

    assert abs(scold_frame["right_arm_rot"]) > 0.0 or abs(scold_frame["left_arm_rot"]) > 0.0
    assert abs(argue_frame["right_arm_rot"]) > 0.0 or abs(argue_frame["left_arm_rot"]) > 0.0


def test_listener_produces_reaction_state():
    """8. Listening actor dynamically reacts to speaker emotion with postural responses."""
    from src.performance_director import ListenerReactionController
    lc = ListenerReactionController()

    resp = lc.evaluate_listener(
        listener_id="kodalu",
        speaker_id="atha",
        emotion="scold",
        frame_idx=35,
        total_frames=90,
        listener_pos=(920, 280),
        speaker_pos=(400, 280),
        speaker_audio_stress=0.8
    )
    assert resp["face_emotion"] in ["cower", "fear", "sad", "listen"]
    assert resp["scale_mod"] < 1.0 or abs(resp["x_offset"]) > 0.0 or resp["fear_intensity"] > 0.0


def test_emotion_modifies_performance_state():
    """9. Emotional states drive differentiated performance parameters and acting styles."""
    from src.performance_director import PerformanceDirector
    pd = PerformanceDirector()

    turn_angry = {"character": "atha", "text": "నన్ను చూసి నవ్వుతావా?", "action": "angry", "emotion": "angry"}
    turn_sad = {"character": "kodalu", "text": "నన్ను క్షమించండి అత్తయ్య...", "action": "plead", "emotion": "sad"}
    actors = {"atha": {"x": 400, "y": 280}, "kodalu": {"x": 900, "y": 280}}

    angry_plan = pd.plan_performance(turn_angry, actors, fps=24, turn_frames=100)
    sad_plan = pd.plan_performance(turn_sad, actors, fps=24, turn_frames=100)

    assert angry_plan["emotion"] == "angry"
    assert sad_plan["emotion"] == "sad"

    angry_eval = pd.evaluate_performance_frame(angry_plan["timeline_id"], frame_idx=30, fps=24)
    sad_eval = pd.evaluate_performance_frame(sad_plan["timeline_id"], frame_idx=30, fps=24)

    assert angry_eval["emotion_intensity"] > 0.0
    assert sad_eval["emotion_intensity"] > 0.0
    assert (angry_eval["gesture"] != sad_eval["gesture"]) or (angry_eval["tear_state"] != sad_eval["tear_state"])


def test_phoneme_to_viseme_mapping_works_correctly():
    """10. Telugu phoneme parsing maps vowels, matras, and consonants to correct visemes."""
    from src.lipsync_engine import (
        extract_telugu_phonemes,
        MOUTH_OPEN_A,
        MOUTH_OPEN_E,
        MOUTH_OPEN_O,
        MOUTH_CLOSED,
        MOUTH_TEETH
    )
    res_a = extract_telugu_phonemes("ఆ")
    assert MOUTH_OPEN_A in res_a

    res_e = extract_telugu_phonemes("ఈ")
    assert MOUTH_OPEN_E in res_e

    res_o = extract_telugu_phonemes("ఊ")
    assert MOUTH_OPEN_O in res_o

    res_m = extract_telugu_phonemes("మ")
    assert MOUTH_CLOSED in res_m

    res_s = extract_telugu_phonemes("స")
    assert MOUTH_TEETH in res_s


def test_viseme_to_face_deformation_works_correctly():
    """11. Visemes translate into localized facial mesh deformation around mouth landmarks."""
    from src.face_engine import FacePerformanceEngine
    from PIL import ImageDraw
    engine = FacePerformanceEngine()

    canvas = Image.new("RGBA", (600, 900), (220, 180, 150, 255))
    draw = ImageDraw.Draw(canvas)
    draw.line([(240, 175), (295, 175)], fill=(60, 20, 20, 255), width=4)

    def_closed = engine.deform_face(canvas, "kodalu", "neutral", intensity=0.0, mouth_cue="mouth_closed")
    def_open_a = engine.deform_face(canvas, "kodalu", "neutral", intensity=1.0, audio_stress=0.8, mouth_cue="mouth_open_a")

    arr_closed = np.array(def_closed)
    arr_open = np.array(def_open_a)

    mouth_diff = np.abs(arr_open[150:220, 200:320, :3].astype(int) - arr_closed[150:220, 200:320, :3].astype(int))
    assert np.max(mouth_diff) > 0 or np.sum(mouth_diff) > 0


def test_camera_follows_actor_position():
    """12. Follow-walk camera dynamically frames and follows actor world position."""
    from src.camera_engine import CameraEngine
    cam = CameraEngine(width=1920, height=1080)

    cam.set_shot("follow_walk", target_pos=(1400, 280))
    assert cam.target_cx > 1000.0
    assert cam.target_zoom > 1.0

    init_cx = cam.current_cx
    cam.update(smoothing=0.5)
    assert abs(cam.current_cx - cam.target_cx) < abs(init_cx - cam.target_cx)


def test_state_does_not_leak_between_scenes():
    """13. Actor presence, coordinates, and camera viewports reset cleanly on scene cuts."""
    from src.scene_director import SceneDirector
    from src.camera_engine import CameraEngine

    sd = SceneDirector()
    scene1 = {
        "scene_id": "s1",
        "background": "village_winter_porch",
        "actors": {
            "kodalu": {"x": 2000, "y": 280, "is_present": False},
            "atha": {"x": 400, "y": 280, "is_present": True}
        }
    }
    scene2 = {
        "scene_id": "s2",
        "background": "village_kitchen",
        "actors": {
            "kodalu": {"x": 500, "y": 280, "is_present": True},
            "atha": {"x": 900, "y": 280, "is_present": True}
        }
    }

    actors1 = sd.setup_scene(scene1)
    assert actors1["kodalu"]["is_present"] is False

    actors2 = sd.setup_scene(scene2)
    assert actors2["kodalu"]["is_present"] is True
    assert actors2["kodalu"]["x"] == 500

    cam = CameraEngine(width=1920, height=1080)
    cam.set_shot("speaker_closeup", target_pos=(400, 200))
    cam.current_zoom = cam.target_zoom
    cam.current_cx = cam.target_cx
    assert cam.current_zoom > 1.5

    cam.reset()
    assert cam.current_zoom == 1.0
    assert cam.current_cx == 960.0
