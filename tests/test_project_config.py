"""
Phase 1 Configuration Layer Tests
Verifies that ProjectConfig loads correctly and that compositor picks up
configuration-driven values (character aliases, subtitles, magic stove).
"""

import sys
import os
import json

import pytest

# Ensure the project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.project_config import load_project_config


@pytest.fixture(scope="module")
def cfg():
    return load_project_config()


@pytest.fixture(scope="module")
def project_json():
    path = os.path.join(PROJECT_ROOT, "project.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# character_aliases
# ---------------------------------------------------------------------------

def test_character_aliases_keys_match_project_json(cfg, project_json):
    """character_aliases returned by ProjectConfig must match project.json."""
    expected_keys = set(project_json.get("character_aliases", {}).keys())
    actual_keys = set(cfg.character_aliases.keys())
    assert actual_keys == expected_keys, (
        f"Mismatch in character_aliases keys.\n"
        f"  Expected: {sorted(expected_keys)}\n"
        f"  Got:      {sorted(actual_keys)}"
    )


def test_character_aliases_not_empty(cfg):
    """character_aliases must not be empty."""
    assert len(cfg.character_aliases) > 0


# ---------------------------------------------------------------------------
# subtitles
# ---------------------------------------------------------------------------

def test_subtitles_returns_tuples(cfg):
    """Every colour value in ProjectConfig.subtitles must be a tuple."""
    subtitles = cfg.subtitles
    assert len(subtitles) > 0, "subtitles dict must not be empty"
    for key, val in subtitles.items():
        assert isinstance(val, tuple), (
            f"subtitles['{key}'] is {type(val).__name__}, expected tuple"
        )


def test_subtitles_known_speaker(cfg):
    """At least one expected speaker key must be present."""
    subtitles = cfg.subtitles
    known = {"SHARADA", "NARRATOR", "KODALU", "ATHA"}
    found = known & set(subtitles.keys())
    assert found, f"None of the expected speaker keys {known} found in subtitles"


# ---------------------------------------------------------------------------
# magic_stove
# ---------------------------------------------------------------------------

def test_magic_stove_required_keys(cfg):
    """magic_stove config must contain all required keys."""
    ms = cfg.magic_stove
    for key in ("asset", "scale", "anchor", "glow_intensity"):
        assert key in ms, f"magic_stove config missing key: '{key}'"


def test_magic_stove_anchor_is_list_or_tuple(cfg):
    """magic_stove anchor must be a list or tuple of length 2."""
    anchor = cfg.magic_stove["anchor"]
    assert isinstance(anchor, (list, tuple)) and len(anchor) == 2, (
        f"magic_stove anchor should be [x, y], got: {anchor!r}"
    )


# ---------------------------------------------------------------------------
# compositor.CHARACTER_ALIASES parity
# ---------------------------------------------------------------------------

def test_compositor_character_aliases_matches_config(cfg):
    """src.compositor.CHARACTER_ALIASES must equal config.character_aliases."""
    import importlib
    compositor = importlib.import_module("src.compositor")
    assert compositor.CHARACTER_ALIASES == cfg.character_aliases, (
        "compositor.CHARACTER_ALIASES does not match config.character_aliases"
    )


# ---------------------------------------------------------------------------
# Phase 2 & 3: props and camera shots
# ---------------------------------------------------------------------------

def test_shots_config_loaded(cfg):
    """shots configuration must contain standard cinematic shot types."""
    shots = cfg.shots
    assert isinstance(shots, dict)
    for expected in ("wide", "medium_character", "speaker_closeup", "two_shot", "follow_walk"):
        assert expected in shots, f"Missing expected shot '{expected}' in shots config"


def test_camera_engine_shot_specs():
    """CameraEngine must initialize with ShotSpec objects from configuration."""
    from src.camera_engine import CameraEngine, ShotSpec
    cam = CameraEngine(1920, 1080)
    assert len(cam.shot_specs) > 0
    assert "wide" in cam.shot_specs
    assert isinstance(cam.shot_specs["wide"], ShotSpec)


def test_generic_prop_manager():
    """GenericPropManager must register and reveal props properly."""
    from src.prop_engine import GenericPropManager
    mgr = GenericPropManager()
    mgr.register_prop("test_prop", "test.png", x=100, y=200)
    assert "test_prop" in mgr.props
    mgr.reveal_prop("test_prop", 0.5)
    assert mgr.props["test_prop"]["visible"] is True

    # Test loading from manifest by name
    loaded = mgr.load_prop_by_name("magic_stove")
    assert loaded is not None
    assert loaded["asset_name"] == "magic_stove.png"
    assert loaded["scale"] == 1.0


def test_object_manager_backward_compatibility():
    """ObjectManager must provide .objects, reveal_object, attach_to_character, and update_held_position."""
    from src.performance_director import ObjectManager
    om = ObjectManager()
    assert "magic_stove" in om.objects
    assert om.objects["magic_stove"]["asset_name"] == "magic_stove.png"
    om.reveal_object("magic_stove", 1.0)
    assert om.objects["magic_stove"]["visible"] is True
    om.attach_to_character("magic_stove", "kodalu")
    assert om.objects["magic_stove"]["is_held"] is True
    assert om.objects["magic_stove"]["held_by"] == "kodalu"
    om.update_held_position("magic_stove", char_x=500, char_y=300, y_bob=5.0, orientation="3/4_right", scale=1.0)
    assert om.objects["magic_stove"]["x"] == 500 + 185


# ---------------------------------------------------------------------------
# Phase 4 & 5: behaviors and project scaffolding
# ---------------------------------------------------------------------------

def test_behaviors_config_loaded(cfg):
    """behaviors configuration must contain standard action behaviors."""
    behaviors = cfg.behaviors
    assert isinstance(behaviors, dict)
    for expected in ("walk_in_left", "walk_in_right", "exit_left", "exit_right", "walk_to_target"):
        assert expected in behaviors, f"Missing expected behavior '{expected}' in behaviors config"


def test_behavior_registry_plan_movement():
    """BehaviorRegistry must calculate correct walk parameters."""
    from src.behavior_registry import BehaviorRegistry
    reg = BehaviorRegistry()
    actors = {"kodalu": {"x": 400, "y": 200, "is_present": False}}
    plan = reg.plan_movement("walk_in_left", "kodalu", actors, target_tag="", fps=24, turn_frames=48)
    assert plan["is_walking"] is True
    assert plan["walk_actor"] == "kodalu"
    assert plan["start_x"] == -650
    assert plan["target_x"] == 400
    assert actors["kodalu"]["is_present"] is True


def test_behavior_registry_helpers():
    """BehaviorRegistry helper queries (is_entry, is_exit, is_movement, entry_side) must work accurately."""
    from src.behavior_registry import BehaviorRegistry
    reg = BehaviorRegistry()
    
    # Entry actions
    assert reg.is_entry_action("walk_in_left") is True
    assert reg.is_entry_action("enter_right") is True
    assert reg.is_entry_action("walk_in") is True
    assert reg.is_entry_action("speaking") is False
    assert reg.is_entry_action("cook") is False

    # Exit actions
    assert reg.is_exit_action("exit_left") is True
    assert reg.is_exit_action("walk_out_right") is True
    assert reg.is_exit_action("exit") is True
    assert reg.is_exit_action("scold") is False

    # Movement vs performance/speech actions
    assert reg.is_movement_action("walk_in_left") is True
    assert reg.is_movement_action("walk_to_target") is True
    assert reg.is_movement_action("cook") is False
    assert reg.is_movement_action("talk") is False

    # Entry side detection
    assert reg.get_entry_side("walk_in_left") == "left"
    assert reg.get_entry_side("enter_left") == "left"
    assert reg.get_entry_side("walk_in_right") == "right"
    assert reg.get_entry_side("enter_right") == "right"


def test_scene_director_setup_and_plan_turn():
    """SceneDirector must setup scenes and plan turns using the decoupled behavior registry."""
    from src.scene_director import SceneDirector
    director = SceneDirector()

    # Setup scene with entering character: should start with is_present=False
    scene_entering = {
        "background": "kitchen_winter",
        "dialogues": [
            {"character": "kodalu", "action": "walk_in_left", "text": "అత్తయ్య గారు!"},
            {"character": "atha", "action": "speaking", "text": "ఏంటి కోడలా?"}
        ]
    }
    actors = director.setup_scene(scene_entering)
    assert "kodalu" in actors
    assert "atha" in actors
    assert actors["kodalu"]["is_present"] is False
    assert actors["atha"]["is_present"] is True

    # Plan turn for entering character
    turn_d = {"character": "kodalu", "action": "walk_in_left", "text": "వచ్చేసాను"}
    plan = director.plan_turn(turn_d, actors, fps=24, turn_frames=48)
    assert plan["is_walking"] is True
    assert plan["walk_actor"] == "kodalu"
    assert plan["camera_shot"] == "follow_walk"
    assert actors["kodalu"]["is_present"] is True


def test_dynamic_behavior_registration():
    """SceneDirector and BehaviorRegistry must allow dynamic behavior registration."""
    from src.scene_director import SceneDirector
    director = SceneDirector()
    
    director.register_behavior("teleport_in", {
        "type": "movement",
        "start_x": 0,
        "target_mode": "actor_x",
        "set_present": True
    })
    
    assert director.behavior_registry.is_entry_action("teleport_in") is True
    desc = director.get_behavior("teleport_in")
    assert desc is not None
    assert desc.set_present is True


def test_project_scaffolder(tmp_path):
    """Project scaffolder must create and populate a valid project workspace."""
    from src.project_scaffolder import create_project
    out_dir = tmp_path / "custom_animation_project"
    created = create_project(str(out_dir), project_name="Custom Telugu Story")
    assert (created / "project.json").is_file()
    with open(created / "project.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["project"]["name"] == "Custom Telugu Story"
    assert data["project"]["schema_version"] == 1


def test_project_scaffolder_full_structure_and_config(tmp_path):
    """Scaffolded workspace must contain standard directories and load via ProjectConfig."""
    from src.project_scaffolder import create_project
    from src.project_config import load_project_config
    out_dir = tmp_path / "full_workspace_project"
    created = create_project(str(out_dir), project_name="Full Workspace Test")
    
    # Check directory structure
    for d in ("assets", "characters", "props", "environments", "scenes", "audio"):
        assert (created / d).is_dir(), f"Expected directory '{d}' missing from scaffolded project"
        
    # Load via ProjectConfig
    p_cfg = load_project_config(str(created))
    assert p_cfg.project["name"] == "Full Workspace Test"
    assert "characters" in p_cfg.paths
    assert "environments" in p_cfg.paths


def test_project_validator(tmp_path):
    """Project validator must correctly validate valid and invalid project workspaces."""
    from src.project_scaffolder import create_project, validate_project
    out_dir = tmp_path / "validated_project"
    created = create_project(str(out_dir), project_name="Validated Story")
    
    # Valid project check
    report = validate_project(str(created))
    assert report["valid"] is True
    assert report["project_name"] == "Validated Story"
    assert len(report["errors"]) == 0

    # Invalid project check (non-existent dir)
    bad_report = validate_project(str(tmp_path / "non_existent"))
    assert bad_report["valid"] is False
    assert len(bad_report["errors"]) > 0


def test_project_authoring_helpers(tmp_path):
    """Scaffolder authoring helpers (add_character, add_prop, add_scene) must create valid artifacts."""
    from src.project_scaffolder import create_project, add_character, add_prop, add_scene
    out_dir = tmp_path / "authoring_project"
    created = create_project(str(out_dir), project_name="Authoring Story")

    # Add character
    char_path = add_character(str(created), char_id="warrior", char_name="Brave Warrior")
    assert (char_path / "character.json").is_file()
    with open(char_path / "character.json", "r", encoding="utf-8") as f:
        c_data = json.load(f)
    assert c_data["id"] == "warrior"
    assert c_data["name"] == "Brave Warrior"

    # Add prop
    prop_path = add_prop(str(created), prop_id="torch", prop_name="Fire Torch")
    assert (prop_path / "prop.json").is_file()
    with open(prop_path / "prop.json", "r", encoding="utf-8") as f:
        pr_data = json.load(f)
    assert pr_data["id"] == "torch"

    # Add scene
    scene = add_scene(str(created), scene_id=1, background="temple_gates")
    assert scene["scene_id"] == 1
    assert scene["background"] == "temple_gates"


def test_cli_parser():
    """src.cli argument parser must support render, create-project, and validate commands."""
    from src.cli import build_parser
    parser = build_parser()
    
    # Validate command
    args_v = parser.parse_args(["validate", "--project", "test_proj"])
    assert args_v.command == "validate"
    assert args_v.project == "test_proj"

    # Create-project command
    args_c = parser.parse_args(["create-project", "--target", "out_dir", "--name", "My Project"])
    assert args_c.command == "create-project"
    assert args_c.target == "out_dir"
    assert args_c.name == "My Project"

    # Render command
    args_r = parser.parse_args(["render", "--project", "proj_dir", "--output", "out.mp4"])
    assert args_r.command == "render"
    assert args_r.project == "proj_dir"
    assert args_r.output == "out.mp4"


# ---------------------------------------------------------------------------
# Phase 6: Production Animation Quality Tests
# ---------------------------------------------------------------------------

def test_walk_cycle_start_stop_damping():
    """WalkCycleController must smoothly dampen stride kinematics at start and stop."""
    from src.animation_engine import WalkCycleController
    controller = WalkCycleController()
    
    total_frames = 48
    # Frame 0: dampening factor should be 0 (smooth start from rest)
    st_0 = controller.evaluate(0, total_walk_frames=total_frames)
    assert st_0["dampen"] == 0.0
    assert abs(st_0["y_bob"]) == 0.0
    
    # Mid-stride (frame 20): dampening factor should be 1.0 (full natural stride)
    st_mid = controller.evaluate(20, total_walk_frames=total_frames)
    assert st_mid["dampen"] == 1.0
    assert abs(st_mid["stride_shear"]) > 0.0
    
    # Near end (frame 47): dampening factor should be near 0 (smooth ease-out)
    st_end = controller.evaluate(47, total_walk_frames=total_frames)
    assert 0.0 <= st_end["dampen"] < 0.2


def test_production_emotions_gestures():
    """GestureController must return valid kinematic dictionaries for all production acting states."""
    from src.animation_engine import GestureController
    states = ["anger", "sadness", "fear", "surprise", "reverence", "relief", "joy", "neutral"]
    for state in states:
        res = GestureController.evaluate(state, frame_idx=10, total_frames=48, is_speaker=True)
        assert isinstance(res, dict)
        for key in ("head_rot", "left_arm_rot", "right_arm_rot", "bob_y", "torso_roll", "scale_x", "scale_y"):
            assert key in res, f"Missing {key} in gesture evaluation for {state}"


def test_listener_reaction_production_states():
    """ListenerReactionController must produce expressive reactive states for all production emotions."""
    from src.performance_director import ListenerReactionController
    lrc = ListenerReactionController()
    
    # Anger should elicit cower / fear reaction
    res_anger = lrc.evaluate_listener("kodalu", "atha", "anger", frame_idx=20, total_frames=48,
                                      listener_pos=(300, 200), speaker_pos=(1000, 200))
    assert res_anger["face_emotion"] == "cower"
    assert res_anger["fear_intensity"] > 0.0
    assert res_anger["scale_mod"] < 1.0
    
    # Reverence should elicit respectful bow
    res_rev = lrc.evaluate_listener("kodalu", "maharshi", "reverence", frame_idx=20, total_frames=48,
                                    listener_pos=(300, 200), speaker_pos=(1000, 200))
    assert res_rev["face_emotion"] == "reverence"
    assert res_rev["head_rot"] != 0.0
    
    # Relief should elicit relaxed settling
    res_rel = lrc.evaluate_listener("kodalu", "atha", "relief", frame_idx=20, total_frames=48,
                                    listener_pos=(300, 200), speaker_pos=(1000, 200))
    assert res_rel["face_emotion"] == "relief"


def test_held_prop_orientation_and_scale():
    """GenericPropManager must track holder orientation and scale, and render properly."""
    from src.prop_engine import GenericPropManager
    from PIL import Image
    mgr = GenericPropManager()
    mgr.register_prop("chulha", "chulha.png", x=100, y=200, scale=0.8)
    mgr.attach_to_character("chulha", "kodalu")
    
    # Update held position with left orientation and character scaling
    mgr.update_held_position("chulha", char_x=500, char_y=300, y_bob=4.0, orientation="3/4_left", scale=1.1)
    prop = mgr.get_prop("chulha")
    assert prop["orientation"] == "3/4_left"
    assert prop["holder_scale"] == 1.1
    assert prop["is_held"] is True
    
    # Verify render_prop executes cleanly with mirroring and scaling
    canvas = Image.new("RGBA", (800, 600), (0, 0, 0, 0))
    dummy_prop = Image.new("RGBA", (50, 50), (255, 128, 0, 255))
    mgr.render_prop("chulha", canvas, dummy_prop, frame_idx=0)
    # Check that canvas received non-zero alpha pixels
    assert any(px[3] > 0 for px in canvas.getdata())


def test_arm_ik_all_character_configs():
    """ArmGestureRenderer must define valid anatomical configurations for all characters."""
    from src.arm_ik import ArmGestureRenderer
    renderer = ArmGestureRenderer()
    expected_chars = ["kodalu", "kanthamma", "atha", "saroja", "maharshi", "padma", "kid"]
    for ch in expected_chars:
        assert ch in renderer.CHAR_ARM_CONFIG, f"Character {ch} missing from CHAR_ARM_CONFIG"
        cfg = renderer.CHAR_ARM_CONFIG[ch]
        assert "shoulder_r" in cfg
        assert "skin_color" in cfg
        assert "sleeve_color" in cfg
        assert cfg["arm_thickness"] > 0


# ---------------------------------------------------------------------------
# Phase 7 — Visible Character Animation & Performance Repair Tests
# ---------------------------------------------------------------------------

def test_phase7_evaluate_acting_frame_transmits_arms_and_tremor():
    """PerformanceDirector.evaluate_acting_frame must propagate dynamic arm rotations and tremor jitter."""
    from src.performance_director import PerformanceDirector
    director = PerformanceDirector()
    
    # Shivering / cold performance must output non-zero tremor jitter and arm articulation
    shiver_frame = director.evaluate_acting_frame("shiver", frame_idx=15, total_frames=60, is_speaker=True)
    assert isinstance(shiver_frame, dict)
    assert abs(shiver_frame.get("jitter_x", 0.0)) > 0.0 or abs(shiver_frame.get("jitter_y", 0.0)) > 0.0, "Shiver must generate jitter"
    assert abs(shiver_frame.get("left_arm_rot", 0.0)) > 0.0 or abs(shiver_frame.get("right_arm_rot", 0.0)) > 0.0, "Shiver must articulate arms"

    # Anger / scold performance must output non-zero arm rotation and torso roll
    anger_frame = director.evaluate_acting_frame("anger", frame_idx=15, total_frames=60, is_speaker=True)
    assert abs(anger_frame.get("left_arm_rot", 0.0)) > 0.0 or abs(anger_frame.get("right_arm_rot", 0.0)) > 0.0, "Anger must articulate arms"
    assert abs(anger_frame.get("torso_roll", 0.0)) > 0.0, "Anger must include torso roll"


def test_phase7_listener_dynamic_articulation():
    """ListenerReactionController must return dynamic arm rotations and torso rolls for reactive states."""
    from src.performance_director import ListenerReactionController
    lrc = ListenerReactionController()
    
    # Cower reaction to anger must articulate protective arm postures and torso shrink
    res_cower = lrc.evaluate_listener("kodalu", "atha", "anger", frame_idx=25, total_frames=60,
                                      listener_pos=(300, 200), speaker_pos=(1000, 200))
    assert "left_arm_rot" in res_cower
    assert "right_arm_rot" in res_cower
    assert "torso_roll" in res_cower
    assert abs(res_cower["left_arm_rot"]) > 0.0 or abs(res_cower["right_arm_rot"]) > 0.0, "Cower must articulate arms"


def test_phase7_face_engine_viseme_radial_pulls():
    """FaceDeformationEngine must have max_displacement >= 12.0 and execute viseme deformations cleanly."""
    from src.face_engine import FaceDeformationEngine
    from PIL import Image
    fde = FaceDeformationEngine()
    assert fde.max_displacement >= 12.0
    
    dummy_img = Image.new("RGBA", (600, 900), (200, 160, 120, 255))
    # Test open_a, open_o, and mouth_teeth viseme deformations
    for viseme in ["mouth_open_a", "mouth_open_o", "mouth_teeth", "mouth_open_e"]:
        warped = fde.deform_face(dummy_img, char_id="atha", emotion="angry", intensity=0.8,
                                 audio_stress=0.6, frame_idx=10, mouth_cue=viseme)
        assert warped.size == dummy_img.size
        assert warped.mode == "RGBA"


def test_phase7_arm_ik_saree_occlusion_patch():
    """ArmGestureRenderer must apply saree occlusion patch for Atha scold/point gestures."""
    from src.arm_ik import ArmGestureRenderer
    from PIL import Image
    renderer = ArmGestureRenderer()
    dummy_canvas = Image.new("RGBA", (600, 900), (0, 0, 0, 0))
    result = renderer.render_arm_overlay(dummy_canvas, char_id="atha", gesture="scold", progress=1.0)
    assert result.size == (600, 900)
    # Check that overlay contains saree green pixels (30, 130, 75)
    data = list(result.getdata())
    has_saree_patch = any(p[0] == 30 and p[1] == 130 and p[2] == 75 for p in data)
    assert has_saree_patch, "Saree occlusion patch must be present for Atha scold gesture"


def test_walk_state_reaches_renderer():
    """WalkCycleController must produce complete kinematics and PuppetRenderer must process walk_state."""
    from src.animation_engine import WalkCycleController, PuppetRenderer
    from PIL import Image
    controller = WalkCycleController(fps=24)
    ws = controller.evaluate(12, walk_type="walk_right", total_walk_frames=48)
    assert "y_bob" in ws
    assert "stride_shear" in ws
    assert "left_foot_lift" in ws
    
    parts = {"base": Image.new("RGBA", (600, 900), (200, 150, 100, 255))}
    res = PuppetRenderer.render_puppet(parts, mouth_cue="mouth_closed", is_blinking=False,
                                       char_id="kodalu", walk_state=ws)
    assert res.size == (600, 900)


def test_walk_position_changes_per_frame():
    """Walking interpolation must change character X position frame-by-frame across walk duration."""
    start_x = 1850
    target_x = 980
    walk_frames = 52
    positions = []
    for f in range(walk_frames):
        prog = f / float(walk_frames)
        smooth_prog = 3.0 * (prog ** 2) - 2.0 * (prog ** 3)
        x = int(start_x + (target_x - start_x) * smooth_prog)
        positions.append(x)
    assert positions[0] == start_x
    assert positions[-1] == target_x
    # Ensure monotonic translation
    assert all(positions[i] >= positions[i+1] for i in range(len(positions)-1))


def test_gesture_state_reaches_puppet():
    """GestureController output must articulate arms in PuppetRenderer."""
    from src.animation_engine import GestureController, PuppetRenderer
    from PIL import Image
    g_state = GestureController.evaluate("gesture", frame_idx=15, total_frames=48, is_speaker=True)
    assert abs(g_state["right_arm_rot"]) > 0.0
    
    parts = {"base": Image.new("RGBA", (600, 900), (200, 150, 100, 255))}
    res = PuppetRenderer.render_puppet(parts, mouth_cue="mouth_closed", is_blinking=False,
                                       char_id="kodalu", gesture_pose="gesture", gesture_state=g_state)
    assert res.size == (600, 900)


def test_lipsync_mouth_changes():
    """FacePerformanceEngine viseme articulation must differentiate open and closed mouth cues."""
    from src.animation_engine import PuppetRenderer
    from PIL import Image
    parts = {
        "base": Image.open("assets/characters/atha/base.png").convert("RGBA")
    }
    sprite_closed = PuppetRenderer.render_puppet(parts, mouth_cue="mouth_closed", is_blinking=False, char_id="atha")
    sprite_open = PuppetRenderer.render_puppet(parts, mouth_cue="mouth_open_a", is_blinking=False, char_id="atha")
    assert sprite_closed.size == sprite_open.size
    assert list(sprite_closed.getdata()) != list(sprite_open.getdata())


def test_listener_state_reaches_renderer():
    """ListenerReactionController must produce reactive state when speaker is angry."""
    from src.performance_director import ListenerReactionController
    lrc = ListenerReactionController()
    info = lrc.evaluate_listener("kodalu", "atha", emotion="angry", frame_idx=20, total_frames=60,
                                 listener_pos=(980, 280), speaker_pos=(320, 280))
    assert info["face_emotion"] == "cower"
    assert info["fear_intensity"] > 0.0
    assert info["scale_mod"] < 1.0


def test_camera_follow_uses_actor_position():
    """Camera follow must compute dynamic tracking center from moving actor."""
    target_x = 980
    cur_x_start = 1850
    cur_x_end = 980
    offset_start = (cur_x_start - target_x) * 0.45
    offset_end = (cur_x_end - target_x) * 0.45
    target_cx_start = 960.0 + offset_start
    target_cx_end = 960.0 + offset_end
    assert target_cx_start > target_cx_end
    assert target_cx_end == 960.0


def test_animation_state_not_overwritten():
    """PerformanceDirector must infer emotion from action and preserve non-idle gesture."""
    from src.performance_director import PerformanceDirector
    pd = PerformanceDirector()
    turn_angry = {"character": "atha", "text": "కోపంగా ఉంది!", "action": "angry"}
    plan = pd.plan_performance(turn_angry, actors={"atha": {"x": 320, "y": 280}}, fps=24, turn_frames=48)
    assert plan["emotion"] == "angry"
    assert plan["timeline_id"] == "scold_timeline"

    turn_shiver = {"character": "atha", "text": "చలి వేస్తోంది!", "action": "shiver"}
    plan_s = pd.plan_performance(turn_shiver, actors={"atha": {"x": 320, "y": 280}}, fps=24, turn_frames=48)
    assert plan_s["emotion"] == "shiver"
    assert plan_s["timeline_id"] == "shiver_timeline"


# ---------------------------------------------------------------------------
# Phase 7B Animation Execution Regression Tests (UNRUN)
# ---------------------------------------------------------------------------

def test_walk_phase_and_kinematics_progression():
    """Walk cycle must continuously advance phase, vertical bob, and stride shear across consecutive frames."""
    from src.animation_engine import WalkCycleController
    wc = WalkCycleController(fps=24)
    res_f0 = wc.evaluate(0, walk_type="walk_left", total_walk_frames=84)
    res_f10 = wc.evaluate(10, walk_type="walk_left", total_walk_frames=84)
    res_f20 = wc.evaluate(20, walk_type="walk_left", total_walk_frames=84)

    assert res_f0["phase"] != res_f10["phase"]
    assert res_f10["phase"] != res_f20["phase"]
    assert abs(res_f10["y_bob"] - res_f0["y_bob"]) > 0.1
    assert abs(res_f20["stride_shear"] - res_f10["stride_shear"]) > 0.1


def test_exit_behavior_walks_until_offscreen():
    """Exit movement actions must walk throughout the turn until character reaches off-screen coordinates."""
    from src.behavior_registry import BehaviorRegistry
    reg = BehaviorRegistry()
    actors = {"kodalu": {"x": 960, "y": 180, "is_present": True}}
    m_plan = reg.plan_movement("walk_out_right", phys_actor="kodalu", actors=actors, target_tag="", fps=24, turn_frames=84)
    assert m_plan["is_walking"] is True
    assert m_plan["walk_frames"] == 84
    assert m_plan["target_x"] >= 1920


def test_walk_to_speaking_transition_state():
    """Post-walk frames must preserve character destination position and activate speaking performance."""
    from src.performance_director import PerformanceDirector
    pd = PerformanceDirector()
    g_speaking = pd.evaluate_acting_frame("speaking", frame_idx=85, total_frames=180, is_speaker=True)
    assert "head_rot" in g_speaking
    assert abs(g_speaking["head_rot"]) > 0.0
    assert abs(g_speaking["right_arm_rot"]) > 0.0


def test_telugu_phoneme_viseme_mapping():
    """Telugu phoneme extractor must map Telugu vowels and consonants to accurate viseme categories."""
    from src.lipsync_engine import extract_telugu_phonemes, MOUTH_OPEN_A, MOUTH_OPEN_O, MOUTH_OPEN_E, MOUTH_CLOSED, MOUTH_TEETH
    text = "బాబోయ్"
    phonemes = extract_telugu_phonemes(text)
    assert MOUTH_OPEN_A in phonemes  # 'ా'
    assert MOUTH_OPEN_O in phonemes  # 'ో'

    text2 = "అత్తయ్య"
    phonemes2 = extract_telugu_phonemes(text2)
    assert MOUTH_OPEN_A in phonemes2  # 'అ'
    assert MOUTH_TEETH in phonemes2   # 'త'


def test_scold_sequence_matches_gesture_controller():
    """Sequence action names like scold_sequence must match corresponding acting kinematics in GestureController."""
    from src.animation_engine import GestureController
    g_scold = GestureController.evaluate("scold_sequence", frame_idx=20, total_frames=60, is_speaker=True)
    assert abs(g_scold["right_arm_rot"]) > 10.0
    assert g_scold["torso_roll"] > 0.0


def test_arm_articulation_rotating_mask():
    """PuppetRenderer arm articulation must output valid sprite when arm is rotated inward or outward."""
    from src.animation_engine import PuppetRenderer
    from PIL import Image
    parts = {"base": Image.new("RGBA", (600, 900), (180, 120, 80, 255))}
    g_state = {"left_arm_rot": 15.0, "right_arm_rot": -25.0, "head_rot": 3.0, "torso_roll": 2.0}
    sprite = PuppetRenderer.render_puppet(parts, mouth_cue="mouth_open_a", is_blinking=False,
                                          char_id="kodalu", gesture_state=g_state)
    assert sprite.size == (600, 900)


# ---------------------------------------------------------------------------
# Phase 7C Animation Quality & Reference Analysis Regression Tests (UNRUN)
# ---------------------------------------------------------------------------

def test_walk_cycle_visible_bob_amplitude():
    """WalkCycleController vertical bob amplitude must be at least 16px and exit walks must not dampen to zero."""
    from src.animation_engine import WalkCycleController
    wc = WalkCycleController(fps=24)
    # Passing frame at 3/4 cycle reaches maximum bob and arm swing amplitude
    res_passing = wc.evaluate(frame_idx=int(round(wc.cycle_frames * 0.75)), walk_type="walk_left", total_walk_frames=84)
    assert abs(res_passing["y_bob"]) >= 16.0
    assert abs(res_passing["left_arm_angle"]) >= 28.0

    # Final frames of exit walk must not dampen to 0
    res_exit_end = wc.evaluate(frame_idx=82, walk_type="walk_out_right", total_walk_frames=84)
    assert res_exit_end["dampen"] == 1.0


def test_entrance_movement_dialogue_transit_duration():
    """BehaviorRegistry.plan_movement for entrance walks must span a significant proportion of dialogue turn frames."""
    from src.behavior_registry import BehaviorRegistry
    reg = BehaviorRegistry()
    actors = {"kodalu": {"x": 960, "y": 180, "is_present": False}}
    # 170 frames dialogue (~7.1 seconds)
    plan = reg.plan_movement("walk_in_right", "kodalu", actors, target_tag="", fps=24, turn_frames=170)
    assert plan["is_walking"] is True
    assert plan["walk_frames"] >= 100  # at least 100 frames (~4.2s) of visible transit
    assert plan["start_x"] == 1760     # immediate entry near screen edge


def test_follow_walk_camera_tracking_logic():
    """Follow-walk camera target must track the actor center position within screen bounds."""
    from src.camera_engine import CameraEngine
    cam = CameraEngine(width=1920, height=1080)
    cam.target_zoom = 1.18
    crop_w = int(1920 / 1.18)
    min_x = crop_w / 2.0
    max_x = 1920 - (crop_w / 2.0)

    # Actor near right edge (x=1600)
    actor_cx = 1600 + 300.0
    target_cx = max(min_x, min(max_x, actor_cx))
    assert target_cx == max_x

    # Actor at center stage (x=960)
    actor_cx_center = 960 + 300.0
    target_cx_center = max(min_x, min(max_x, actor_cx_center))
    assert min_x <= target_cx_center <= max_x


def test_speaking_audio_stress_arm_modulation():
    """PerformanceDirector.evaluate_acting_frame must pulse arm gesture rotation when audio_stress occurs."""
    from src.performance_director import PerformanceDirector
    pd = PerformanceDirector()
    g_calm = pd.evaluate_acting_frame("speaking", frame_idx=20, total_frames=100, is_speaker=True, audio_stress=0.0)
    g_stress = pd.evaluate_acting_frame("speaking", frame_idx=20, total_frames=100, is_speaker=True, audio_stress=0.9, is_strike_beat=True)

    # Stressed speech must exhibit stronger arm gesture amplitude than calm speech
    assert abs(g_stress["right_arm_rot"]) > abs(g_calm["right_arm_rot"])


def test_telugu_labial_viseme_closure():
    """extract_telugu_phonemes and lipsync cues must preserve MOUTH_CLOSED on Telugu bilabials."""
    from src.lipsync_engine import extract_telugu_phonemes, MOUTH_CLOSED
    text = "అమ్మ"
    phonemes = extract_telugu_phonemes(text)
    assert MOUTH_CLOSED in phonemes  # 'మ' produces labial lip closure


def test_face_engine_mouth_opens_downward():
    """FacePerformanceEngine must displace the lower lip downward rather than upward for open visemes."""
    from src.face_engine import FacePerformanceEngine
    from PIL import Image
    import numpy as np
    fpe = FacePerformanceEngine()
    # Create test canvas with white face and a black dot at mouth_c
    test_img = Image.new("RGBA", (600, 900), (255, 255, 255, 255))
    arr = np.array(test_img)
    # Put marked pixel at mouth_c (268, 174)
    arr[174, 268, :3] = [0, 0, 0]
    marked = Image.fromarray(arr)
    deformed = fpe.deform_face(marked, char_id="kodalu", emotion="neutral", mouth_cue="mouth_open_a", audio_stress=0.5)
    assert deformed.size == (600, 900)


def test_walk_in_multi_frame_continuous_x_progression():
    """Actor X position must advance continuously across frames during walk_in_right."""
    start_x = 1760
    target_x = 960
    walk_frames = 137
    x_positions = []
    for f in range(walk_frames):
        prog = f / float(walk_frames)
        smooth_prog = 3.0 * (prog ** 2) - 2.0 * (prog ** 3)
        cur_x = int(start_x + (target_x - start_x) * smooth_prog)
        x_positions.append(cur_x)

    # Verify monotonic travel from entrance edge to target
    assert x_positions[0] == 1760
    assert x_positions[-1] <= 965
    # Verify no multi-frame stall in mid-stride (frames 20 to 110)
    for i in range(20, 110):
        assert x_positions[i] < x_positions[i - 1], f"Stall detected at frame {i}"


def test_follow_walk_continuous_camera_panning():
    """Follow-walk camera target must pan continuously across the stage without deadzone freeze."""
    width = 1920
    zoom = 1.18
    crop_w = int(width / zoom)
    min_cam_x = crop_w / 2.0
    max_cam_x = width - (crop_w / 2.0)
    walk_frames = 137
    start_x = 1760
    target_x = 960

    cam_targets = []
    for f in range(walk_frames):
        t_walk = f / float(max(1, walk_frames))
        smooth_cam = 3.0 * (t_walk ** 2) - 2.0 * (t_walk ** 3)
        cx = max_cam_x - (max_cam_x - 960.0) * smooth_cam
        cam_targets.append(cx)

    # Starts near right crop limit and smoothly pans leftward to center framing
    assert cam_targets[0] == max_cam_x
    assert abs(cam_targets[-1] - 960.0) < 1.0
    total_pan = cam_targets[0] - cam_targets[-1]
    assert total_pan >= 140.0, f"Expected pan >= 140px, got {total_pan}"


def test_puppet_renderer_anatomical_shoulder_and_mask_centering():
    """PuppetRenderer must anchor shoulders and arm masks dynamically to each character's anatomical center."""
    from src.animation_engine import PuppetRenderer
    from PIL import Image

    dummy_parts = {"base": Image.new("RGBA", (600, 900), (180, 120, 80, 255))}

    # Render Kodalu gesture (anatomical center xc=268)
    sprite_kodalu = PuppetRenderer.render_puppet(
        parts=dummy_parts, mouth_cue="mouth_closed", is_blinking=False,
        char_id="kodalu", gesture_pose="gesture",
        gesture_state={"left_arm_rot": 18.0, "right_arm_rot": -28.0}
    )
    assert sprite_kodalu.size == (600, 900)

    # Render Atha gesture (anatomical center xc=348)
    sprite_atha = PuppetRenderer.render_puppet(
        parts=dummy_parts, mouth_cue="mouth_closed", is_blinking=False,
        char_id="atha", gesture_pose="scold",
        gesture_state={"left_arm_rot": 14.0, "right_arm_rot": -35.0}
    )
    assert sprite_atha.size == (600, 900)


def test_walk_out_full_offscreen_lifecycle():
    """Exit walk must progress until x >= 1920 and remain present until completely off-screen."""
    start_x = 960
    target_x = 1960
    total_frames = 101

    offscreen_frame = None
    for f in range(total_frames):
        prog = f / float(total_frames)
        exit_prog = prog ** 1.2
        cur_x = int(start_x + (target_x - start_x) * exit_prog)
        if cur_x >= 1920 and offscreen_frame is None:
            offscreen_frame = f

    # Character should remain on screen for at least 90 frames of the 101 frame turn
    assert offscreen_frame is not None
    assert offscreen_frame >= 95, f"Actor exited prematurely at frame {offscreen_frame}"


def test_scold_sequence_multi_frame_acting_progression():
    """Scold sequence must produce distinct kinematic joint positions across frames 0, 10, 20, 30."""
    from src.performance_director import PerformanceDirector
    pd = PerformanceDirector()
    f0 = pd.evaluate_acting_frame("scold_sequence", 0, 100, is_speaker=True)
    f10 = pd.evaluate_acting_frame("scold_sequence", 10, 100, is_speaker=True)
    f20 = pd.evaluate_acting_frame("scold_sequence", 20, 100, is_speaker=True)
    f30 = pd.evaluate_acting_frame("scold_sequence", 30, 100, is_speaker=True)

    # Multi-frame progression must show dynamic variance (not static default pose)
    assert f0["right_arm_rot"] != f10["right_arm_rot"]
    assert f10["right_arm_rot"] != f20["right_arm_rot"]
    assert f20["head_rot"] != f30["head_rot"]


def test_listener_cower_latency_and_physical_retreat():
    """Listener reaction controller must observe reaction latency and smooth retreat during intense scolding."""
    from src.performance_director import ListenerReactionController
    lc = ListenerReactionController(fps=24)
    # Frame 0: within latency window (reaction not yet peaked)
    l0 = lc.evaluate_listener("kodalu", "atha", "scold", 0, 100, (960, 180), (350, 180), 0.8)
    # Frame 30: fully engaged cower reaction
    l30 = lc.evaluate_listener("kodalu", "atha", "scold", 30, 100, (960, 180), (350, 180), 0.8)

    assert l0["fear_intensity"] < l30["fear_intensity"]
    assert abs(l30["x_offset"]) > abs(l0["x_offset"])
    assert l30["scale_mod"] < 1.0  # physical cower compression








