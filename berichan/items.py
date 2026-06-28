"""
Loader for the bundled Champions item list (assets/data/items.json) and item
icons (assets/items/<id>.png). Powers the item picker, effect tooltips, and the
held-item image shown next to each Pokémon on the team cards.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from .paths import resource_path


def _to_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


@lru_cache(maxsize=1)
def _data() -> dict:
    path = resource_path("assets", "data", "items.json")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"items": []}


@lru_cache(maxsize=1)
def _by_name() -> dict[str, dict]:
    index: dict[str, dict] = {}
    for it in _data().get("items", []):
        index[it["name"].lower()] = it
        index[it["id"].lower()] = it
        index[_to_id(it["name"])] = it
    return index


def is_loaded() -> bool:
    return bool(_data().get("items"))


def all_items() -> list[dict]:
    return sorted(_data().get("items", []), key=lambda it: it["name"])


def all_names() -> list[str]:
    return [it["name"] for it in all_items()]


def get_item(name: str) -> dict | None:
    if not name:
        return None
    return _by_name().get(name.strip().lower()) or _by_name().get(_to_id(name))


def describe(name: str) -> str:
    it = get_item(name)
    return it["desc"] if it else ""


def icon_path(name: str) -> Path | None:
    it = get_item(name)
    if not it:
        return None
    return resource_path("assets", "items", f"{it['id']}.png")
