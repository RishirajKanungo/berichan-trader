"""
Filesystem locations for the app, working both in a normal checkout and
inside a PyInstaller one-file bundle.

  - app_data_dir(): per-user writable dir for settings.json (%APPDATA%/Berichan…)
  - resource_path(): read-only bundled assets (sounds, icons), relocated by
    PyInstaller to sys._MEIPASS at runtime.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "BerichanCrossTransfer"


def app_data_dir() -> Path:
    """Per-user writable directory for settings. Created if missing."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = Path(base) / APP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_file() -> Path:
    return app_data_dir() / "settings.json"


def project_root() -> Path:
    """Repository root (parent of the berichan/ package)."""
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    """
    Resolve a bundled, read-only asset path.

    Under PyInstaller, data files live under sys._MEIPASS. In a normal
    checkout they live next to the project root.
    """
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base else project_root()
    return root.joinpath(*parts)
