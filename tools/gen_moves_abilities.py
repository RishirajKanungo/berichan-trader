"""
Generate assets/data/moves.json and assets/data/abilities.json — descriptions
and metadata for every move/ability used by the Champions roster.

Move mechanics (type, category, power, accuracy, PP, **priority**) and effect
text are universal across games, so this pulls them from Pokémon Showdown's
canonical data files (complete, current, and including priority), trimmed to
exactly the moves/abilities that appear in assets/data/champions.json.

Run once (needs internet); outputs are committed:
    python tools/gen_moves_abilities.py
"""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAMPIONS = ROOT / "assets" / "data" / "champions.json"
MOVES_URL = "https://play.pokemonshowdown.com/data/moves.json"
# Ability effect text lives in Showdown's JS data file (no JSON equivalent).
ABILITIES_JS_URL = "https://play.pokemonshowdown.com/data/abilities.js"
_HEADERS = {"User-Agent": "Mozilla/5.0 (BerichanCrossTransfer data gen)"}


def _to_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _get_text(url: str) -> str:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def _ability_descs() -> dict[str, str]:
    """Parse name -> shortDesc from Showdown's abilities.js (keyed by toID)."""
    js = _get_text(ABILITIES_JS_URL)
    pairs = re.findall(
        r'name:"([^"]+)",.*?shortDesc:"((?:[^"\\]|\\.)*)"', js, re.DOTALL
    )
    return {_to_id(name): desc.replace('\\"', '"') for name, desc in pairs}


def main() -> None:
    champ = json.loads(CHAMPIONS.read_text(encoding="utf-8"))
    move_names, ability_names = set(), set()
    for sp in champ["species"]:
        move_names.update(sp.get("moves", []))
        ability_names.update(sp.get("abilities", []))

    sd_moves = _get(MOVES_URL)
    abil_desc = _ability_descs()

    # Human-friendly move flags worth surfacing in the UI (e.g. "Sound" moves
    # bypass Substitute; "Contact" triggers Rough Skin; etc.).
    flag_labels = {
        "contact": "Contact", "sound": "Sound", "punch": "Punch", "bite": "Bite",
        "bullet": "Bullet", "pulse": "Pulse", "powder": "Powder", "dance": "Dance",
        "slicing": "Slicing", "wind": "Wind", "heal": "Heal", "bypasssub": "Bypasses Sub",
        "recharge": "Recharge", "charge": "Charge",
    }

    moves = []
    for name in sorted(move_names):
        m = sd_moves.get(_to_id(name))
        if not m:
            moves.append({"name": name, "type": "", "category": "",
                          "power": 0, "accuracy": "—", "pp": 0,
                          "priority": 0, "desc": "", "longDesc": "", "flags": []})
            continue
        acc = m.get("accuracy", True)
        mflags = m.get("flags", {}) or {}
        flags = [label for key, label in flag_labels.items() if mflags.get(key)]
        moves.append({
            "name": m.get("name", name),
            "type": m.get("type", ""),
            "category": m.get("category", ""),
            "power": m.get("basePower", 0),
            "accuracy": "—" if acc is True else acc,
            "pp": m.get("pp", 0),
            "priority": m.get("priority", 0),
            "desc": m.get("shortDesc") or m.get("desc", ""),
            "longDesc": m.get("desc", ""),
            "flags": flags,
        })

    abilities = []
    for name in sorted(ability_names):
        abilities.append({"name": name, "desc": abil_desc.get(_to_id(name), "")})

    _write("moves.json", "pokemonshowdown moves (priority/effects)", moves, "moves")
    _write("abilities.json", "pokemonshowdown abilities (effects)", abilities, "abilities")
    missing_m = [m["name"] for m in moves if not m["desc"]]
    missing_a = [a["name"] for a in abilities if not a["desc"]]
    print(f"moves: {len(moves)} ({len(missing_m)} without desc: {missing_m[:8]})")
    print(f"abilities: {len(abilities)} ({len(missing_a)} without desc: {missing_a[:8]})")


def _write(filename: str, source: str, rows: list, key: str) -> None:
    path = ROOT / "assets" / "data" / filename
    path.write_text(
        json.dumps({"source": source, "generated": date.today().isoformat(),
                    "count": len(rows), key: rows}, indent=1, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {path} ({len(rows)} {key})")


if __name__ == "__main__":
    main()
