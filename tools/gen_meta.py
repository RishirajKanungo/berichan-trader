"""
Generate assets/data/meta.json — competitive usage data ("what people actually
run") for the Champions roster, from the free championsbattledata.com API.

Per Pokémon and per format (Doubles & Singles) it captures the most-used moves,
held items, abilities, stat alignments (natures), and Stat-Point spreads, each
with a usage %. The SP spreads map straight onto the editor's stat spread.

Bundled & committed; the app can also live-refresh via src/meta.py.

    python tools/gen_meta.py
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import quote

API = "https://championsbattledata.com"
ROOT = Path(__file__).resolve().parent.parent
CHAMPIONS = ROOT / "assets" / "data" / "champions.json"
OUT = ROOT / "assets" / "data" / "meta.json"
FORMATS = ["Doubles", "Singles"]
SEASON = "Current"
_HEADERS = {"User-Agent": "Mozilla/5.0 (BerichanCrossTransfer meta gen)"}

_SP_FIELDS = [("HP", "hp_points"), ("Atk", "attack_points"), ("Def", "defense_points"),
              ("SpA", "sp_atk_points"), ("SpD", "sp_def_points"), ("Spe", "speed_points")]


def _to_id(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _get(url: str, retries: int = 6):
    """GET with polite backoff; honors Retry-After and backs off hard on 503."""
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code in (429, 503):
                retry_after = exc.headers.get("Retry-After")
                wait = int(retry_after) if (retry_after and retry_after.isdigit()) \
                    else min(60, 5 * (attempt + 1) ** 2)
                time.sleep(wait)
            else:
                time.sleep(2 * (attempt + 1))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed {url}: {last}")


def parse_rows(rows: list[dict]) -> dict:
    out = {"moves": [], "items": [], "abilities": [], "natures": [], "spreads": []}
    for r in rows:
        cat, pct = r.get("category"), r.get("percentage_value", 0)
        if cat == "move":
            out["moves"].append([r["name"], pct])
        elif cat == "held_item":
            out["items"].append([r["name"], pct])
        elif cat == "ability":
            out["abilities"].append([r["name"], pct])
        elif cat == "stat_alignment":
            out["natures"].append([r["name"], pct, r.get("stat_up", ""), r.get("stat_down", "")])
        elif cat == "stat_points":
            sp = {label: int(r.get(field) or 0) for label, field in _SP_FIELDS}
            out["spreads"].append([sp, pct])
    return out


def _save(data: dict) -> None:
    OUT.write_text(json.dumps({
        "source": "championsbattledata.com",
        "season": SEASON,
        "generated": date.today().isoformat(),
        "formats": data,
    }, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    champ = json.loads(CHAMPIONS.read_text(encoding="utf-8"))
    roster = [(sp["id"], sp["name"]) for sp in champ["species"]]

    index = _get(f"{API}/api/index")
    # Map our species -> API slug by normalized name/battleName/slug.
    slug_for: dict[str, str] = {}
    for p in index.get("pokemon", []):
        for key in (p.get("name"), p.get("battleName"), p.get("slug")):
            if key:
                slug_for.setdefault(_to_id(key), p.get("slug") or _to_id(p["name"]))

    # Resume: keep any species already fetched in a prior (interrupted) run.
    data = {fmt: {} for fmt in FORMATS}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8")).get("formats", {})
            for fmt in FORMATS:
                data[fmt].update(prev.get(fmt, {}))
            done = len(data[FORMATS[0]])
            if done:
                print(f"Resuming — {done} species already have data.")
        except (OSError, json.JSONDecodeError):
            pass

    missing = []
    for i, (our_id, name) in enumerate(roster, 1):
        if all(our_id in data[fmt] for fmt in FORMATS):
            continue  # already fetched in a previous run
        slug = slug_for.get(_to_id(name)) or slug_for.get(_to_id(our_id)) or _to_id(name)
        for fmt in FORMATS:
            if our_id in data[fmt]:
                continue
            try:
                d = _get(f"{API}/api/battle/{fmt}/{quote(slug)}?season={quote(SEASON)}")
                parsed = parse_rows(d.get("rows", []))
                if any(parsed.values()):
                    data[fmt][our_id] = parsed
            except Exception as exc:  # noqa: BLE001
                missing.append(f"{name}/{fmt}: {exc}")
            time.sleep(0.4)
        if i % 10 == 0:
            _save(data)  # checkpoint so progress survives interruption
            print(f"  {i}/{len(roster)}…")

    _save(data)
    for fmt in FORMATS:
        print(f"{fmt}: {len(data[fmt])} species with data")
    if missing:
        print(f"{len(missing)} fetch issues (first few): {missing[:5]}")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
