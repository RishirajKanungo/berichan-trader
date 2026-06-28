"""
Persistent library of named teams, stored as Showdown text in teams.json under
the per-user app data dir. Keeping the on-disk form as Showdown text makes it
human-readable and round-trips through the same parser the rest of the app uses.
"""

from __future__ import annotations

import json
from pathlib import Path

from .paths import app_data_dir
from .team_parser import Pokemon, parse_team, team_to_showdown


def _teams_file() -> Path:
    return app_data_dir() / "teams.json"


def _load_raw() -> dict:
    path = _teams_file()
    if not path.exists():
        return {"teams": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("teams"), list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"teams": []}


def _write_raw(data: dict) -> None:
    _teams_file().write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_teams() -> list[str]:
    return [t["name"] for t in _load_raw()["teams"] if "name" in t]


def save_team(name: str, team: list[Pokemon]) -> None:
    """Create or overwrite a named team."""
    name = name.strip()
    if not name:
        raise ValueError("Team name cannot be empty.")
    data = _load_raw()
    entry = {"name": name, "showdown": team_to_showdown(team)}
    for i, t in enumerate(data["teams"]):
        if t.get("name") == name:
            data["teams"][i] = entry
            break
    else:
        data["teams"].append(entry)
    _write_raw(data)


def load_team(name: str) -> list[Pokemon]:
    for t in _load_raw()["teams"]:
        if t.get("name") == name:
            return parse_team(t.get("showdown", ""))
    return []


def delete_team(name: str) -> None:
    data = _load_raw()
    data["teams"] = [t for t in data["teams"] if t.get("name") != name]
    _write_raw(data)
