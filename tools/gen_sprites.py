"""
Download the Champions roster sprites and bundle them under assets/sprites/.

Source: the sprite images Serebii shows on the Champions roster page
(https://www.serebii.net/pokemonchampions/pokemon.shtml). Each species row's
first image is the base-form sprite; later images are mega/alt forms which we
skip. Saved as assets/sprites/<slug>.png so the app can load by species id.

Run once (needs internet); images are committed so the app never fetches:
    python tools/gen_sprites.py
"""

from __future__ import annotations

import re
import time
import urllib.request
from pathlib import Path

ROSTER_URL = "https://www.serebii.net/pokemonchampions/pokemon.shtml"
BASE = "https://www.serebii.net"
OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "sprites"
_HEADERS = {"User-Agent": "Mozilla/5.0 (BerichanCrossTransfer sprite fetcher)"}


def _fetch(url: str, binary: bool = False, retries: int = 3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
                return data if binary else data.decode("utf-8", "ignore")
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last}")


def main() -> None:
    html = _fetch(ROSTER_URL)
    pairs = re.findall(
        r'/pokedex-champions/([a-z0-9\-\.\%]+)/"><img src="([^"]+\.png)"', html
    )
    # First sprite per slug = base form.
    sprite_for: dict[str, str] = {}
    for slug, src in pairs:
        sprite_for.setdefault(slug, src)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"{len(sprite_for)} species sprites to fetch")
    ok = 0
    for i, (slug, src) in enumerate(sprite_for.items(), 1):
        dest = OUT_DIR / f"{slug}.png"
        if dest.exists():
            ok += 1
            continue
        try:
            dest.write_bytes(_fetch(BASE + src, binary=True))
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i}] {slug}: ERROR {exc}")
        if i % 25 == 0:
            print(f"  {i}/{len(sprite_for)}…")
        time.sleep(0.15)
    print(f"Done: {ok}/{len(sprite_for)} sprites in {OUT_DIR}")


if __name__ == "__main__":
    main()
