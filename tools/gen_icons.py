"""
Download the 18 type icons and the 3 move-category icons (Physical / Special /
Status) from Serebii and bundle them under assets/types/ and assets/categories/.
These give each move a recognizable type + category icon in the editor.

Run once (needs internet); outputs are committed:
    python tools/gen_icons.py
"""

from __future__ import annotations

import time
import urllib.request
from pathlib import Path

BASE = "https://www.serebii.net/pokedex-bw/type/"
ROOT = Path(__file__).resolve().parent.parent
TYPE_DIR = ROOT / "assets" / "types"
CAT_DIR = ROOT / "assets" / "categories"
_HEADERS = {"User-Agent": "Mozilla/5.0 (BerichanCrossTransfer icon fetcher)"}

TYPES = [
    "normal", "fire", "water", "electric", "grass", "ice", "fighting", "poison",
    "ground", "flying", "psychic", "bug", "rock", "ghost", "dragon", "dark",
    "steel", "fairy",
]
# Serebii filename -> our category name
CATEGORIES = {"physical": "physical", "special": "special", "other": "status"}


def _fetch(url: str, retries: int = 3) -> bytes:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"failed {url}: {last}")


def main() -> None:
    TYPE_DIR.mkdir(parents=True, exist_ok=True)
    CAT_DIR.mkdir(parents=True, exist_ok=True)
    for t in TYPES:
        (TYPE_DIR / f"{t}.gif").write_bytes(_fetch(f"{BASE}{t}.gif"))
        time.sleep(0.1)
    print(f"types: {len(TYPES)} icons -> {TYPE_DIR}")
    for src, dest in CATEGORIES.items():
        (CAT_DIR / f"{dest}.png").write_bytes(_fetch(f"{BASE}{src}.png"))
        time.sleep(0.1)
    print(f"categories: {len(CATEGORIES)} icons -> {CAT_DIR}")


if __name__ == "__main__":
    main()
