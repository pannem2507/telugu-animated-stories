"""
Command Line Interface for 2D Animated Stories Engine (Phase 5).
Provides unified subcommands for rendering productions, scaffolding new projects,
validating project workspaces, and managing characters/props.

Usage:
    python -m src.cli render --project projects/my_story/ --output output/my_story.mp4
    python -m src.cli create-project --target projects/my_story/ --name "My Story"
    python -m src.cli validate --project projects/my_story/
    python -m src.cli list-templates
    python -m src.cli add-character --project projects/my_story/ --id hero --name "Hero"
    python -m src.cli add-prop --project projects/my_story/ --id lamp --name "Oil Lamp"
"""

import sys
import argparse
from pathlib import Path

# Fix Windows console UTF-8 printing
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.cli",
        description="2D Animated Stories Production CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # render
    render_parser = subparsers.add_parser("render", help="Render an animated production to MP4")
    render_parser.add_argument("--project", "-p", type=str, default=None, help="Path to project workspace directory")
    render_parser.add_argument("--script", "-s", "--screenplay", type=str, default=None, help="Path to screenplay JSON script")
    render_parser.add_argument("--output", "-o", type=str, default=None, help="Output MP4 file path")
    render_parser.add_argument("--fps", type=int, default=24, help="Render frame rate (default: 24)")

    # create-project
    create_parser = subparsers.add_parser("create-project", help="Initialize a new animation project workspace")
    create_parser.add_argument("--target", "-t", type=str, required=True, help="Destination directory path")
    create_parser.add_argument("--name", "-n", type=str, default="New Animation Project", help="Title of the project")
    create_parser.add_argument("--template", type=str, default=None, help="Starter template directory")

    # validate
    validate_parser = subparsers.add_parser("validate", help="Validate an animation project workspace")
    validate_parser.add_argument("--project", "-p", type=str, required=True, help="Path to project workspace directory")

    # list-templates
    subparsers.add_parser("list-templates", help="List available project starter templates")

    # add-character
    char_parser = subparsers.add_parser("add-character", help="Scaffold a new character in a project workspace")
    char_parser.add_argument("--project", "-p", type=str, required=True, help="Path to project workspace directory")
    char_parser.add_argument("--id", type=str, required=True, help="Unique identifier for the character")
    char_parser.add_argument("--name", type=str, default=None, help="Display name of the character")
    char_parser.add_argument("--orientation", type=str, default="3/4_right", choices=["3/4_left", "3/4_right", "front"], help="Base facing orientation")
    char_parser.add_argument("--scale", type=float, default=1.0, help="Render scale")

    # add-prop
    prop_parser = subparsers.add_parser("add-prop", help="Scaffold a new prop in a project workspace")
    prop_parser.add_argument("--project", "-p", type=str, required=True, help="Path to project workspace directory")
    prop_parser.add_argument("--id", type=str, required=True, help="Unique identifier for the prop")
    prop_parser.add_argument("--name", type=str, default=None, help="Display name of the prop")
    prop_parser.add_argument("--scale", type=float, default=1.0, help="Render scale")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "create-project":
        from .project_scaffolder import create_project
        out_path = create_project(args.target, project_name=args.name, template_dir=args.template)
        print(f"✅ Successfully initialized project at: {out_path}")
        return 0

    elif args.command == "validate":
        from .project_scaffolder import validate_project
        report = validate_project(args.project)
        print(f"Validation Report for: {args.project}")
        print(f"  Status: {'VALID ✅' if report['valid'] else 'INVALID ❌'}")
        print(f"  Project Name: {report['project_name']}")
        print(f"  Characters Found: {len(report['characters_found'])} ({', '.join(report['characters_found']) or 'none'})")
        print(f"  Scenes Found: {report['scenes_found']}")
        if report["errors"]:
            print(f"  Errors:")
            for err in report["errors"]:
                print(f"    - {err}")
        if report["warnings"]:
            print(f"  Warnings:")
            for w in report["warnings"]:
                print(f"    - {w}")
        return 0 if report["valid"] else 1

    elif args.command == "list-templates":
        from .project_scaffolder import list_templates
        templates = list_templates()
        print(f"Available Starter Templates ({len(templates)}):")
        for t in templates:
            print(f"  - {t['id']}: {t['name']} (Path: {t['path']})")
        return 0

    elif args.command == "add-character":
        from .project_scaffolder import add_character
        char_path = add_character(args.project, args.id, char_name=args.name,
                                  orientation=args.orientation, scale=args.scale)
        print(f"✅ Created character '{args.id}' at: {char_path}")
        return 0

    elif args.command == "add-prop":
        from .project_scaffolder import add_prop
        prop_path = add_prop(args.project, args.id, prop_name=args.name, scale=args.scale)
        print(f"✅ Created prop '{args.id}' at: {prop_path}")
        return 0

    elif args.command == "render":
        from .project_config import load_project_config
        from .script_parser import load_script
        from .compositor import render_story_video

        proj_path = args.project
        cfg = load_project_config(proj_path)
        script_file = args.script
        if not script_file:
            # Fallback to scenes/screenplay.json in project
            candidate = Path(cfg.root) / cfg.paths.get("scenes", "scenes") / "screenplay.json"
            if candidate.is_file():
                script_file = str(candidate)
            else:
                candidate2 = Path(cfg.root) / "screenplay.json"
                if candidate2.is_file():
                    script_file = str(candidate2)

        if not script_file or not Path(script_file).is_file():
            print(f"Error: Screenplay script not found. Specify with --script <path>")
            return 1

        output_mp4 = args.output or f"output/{Path(script_file).stem}.mp4"
        script_data = load_script(script_file)
        render_story_video(script_data, output_mp4=output_mp4, fps=args.fps)
        print(f"✅ Render complete: {output_mp4}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
