import os
import json
from pathlib import Path

class ProjectConfig:
    """Lightweight loader for the project configuration.
    
    The configuration file ``project.json`` lives at the repository root.
    This class validates required top‑level sections and provides convenient
    properties for the engine modules.
    """
    REQUIRED_TOP_LEVEL = {"project", "paths"}
    REQUIRED_PATHS = {"assets", "characters", "props", "environments", "scenes"}

    def __init__(self, project_root: str = None):
        # Resolve the repository root. If ``project_root`` is None we assume the
        # caller resides somewhere inside the repository (e.g., ``src``) and
        # walk up until ``project.json`` is found.
        if project_root:
            self.root = Path(project_root).resolve()
        else:
            # Start from this file's directory and ascend until we find project.json
            cur = Path(__file__).resolve()
            while cur != cur.parent:
                if (cur / "project.json").exists():
                    self.root = cur
                    break
                cur = cur.parent
            else:
                raise FileNotFoundError("project.json not found in any parent directory.")

        self._data = self._load_json(self.root / "project.json")
        self._validate()
        # Lazily loaded sub‑configs
        self._subtitles = None
        self._environments = None
        self._magic_stove = None
        self._shots = None
        self._behaviors = None

    def _load_json(self, path: Path) -> dict:
        if not path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _validate(self):
        missing = self.REQUIRED_TOP_LEVEL - self._data.keys()
        if missing:
            raise ValueError(f"Missing required top‑level sections in project.json: {missing}")
        # Validate required path keys exist
        paths = self._data.get("paths", {})
        missing_paths = self.REQUIRED_PATHS - paths.keys()
        if missing_paths:
            raise ValueError(f"Missing required path entries in project.json: {missing_paths}")

    # ---------------------------------------------------------------------
    # Helper properties
    # ---------------------------------------------------------------------
    @property
    def project(self) -> dict:
        return self._data.get("project", {})

    @property
    def paths(self) -> dict:
        return self._data.get("paths", {})

    @property
    def character_aliases(self) -> dict:
        return self._data.get("character_aliases", {})

    @property
    def subtitles(self) -> dict:
        if self._subtitles is None:
            sub_path = self.root / self.paths.get("subtitles", "config/subtitles.json")
            if sub_path.is_file():
                raw = self._load_json(sub_path)
                data = raw.get("subtitles", raw)
                self._subtitles = {k: tuple(v) for k, v in data.items()}
            else:
                self._subtitles = {}
        return self._subtitles

    @property
    def environments(self) -> dict:
        if self._environments is None:
            env_path = self.root / self.paths.get("environment_config", "config/environments.json")
            if env_path.is_file():
                raw = self._load_json(env_path)
                self._environments = raw.get("environments", raw)
            else:
                self._environments = {}
        return self._environments

    @property
    def magic_stove(self) -> dict:
        if self._magic_stove is None:
            ms_path = self.root / self.paths.get("magic_stove", "config/magic_stove.json")
            if ms_path.is_file():
                self._magic_stove = self._load_json(ms_path)
            else:
                self._magic_stove = {}
        return self._magic_stove

    @property
    def shots(self) -> dict:
        if self._shots is None:
            shot_path = self.root / self.paths.get("shots", "config/shot_defs.json")
            if shot_path.is_file():
                raw = self._load_json(shot_path)
                self._shots = raw.get("shots", raw)
            else:
                self._shots = {}
        return self._shots

    @property
    def behaviors(self) -> dict:
        if self._behaviors is None:
            b_path = self.root / self.paths.get("behaviors", "config/behaviors.json")
            if b_path.is_file():
                raw = self._load_json(b_path)
                self._behaviors = raw.get("behaviors", raw)
            else:
                self._behaviors = {}
        return self._behaviors

    # ---------------------------------------------------------------------
    # Convenience helpers
    # ---------------------------------------------------------------------
    def resolve_path(self, key: str) -> Path:
        """Return an absolute path for a entry in ``paths`` relative to the repo root."""
        rel = self.paths.get(key)
        if not rel:
            raise KeyError(f"Path key '{key}' not defined in project.json")
        return (self.root / rel).resolve()

def load_project_config(project_dir: str = None) -> ProjectConfig:
    """Factory function used by the engine entry points.
    
    ``project_dir`` may be omitted – the function will locate the repository root
    automatically.
    """
    return ProjectConfig(project_dir)
