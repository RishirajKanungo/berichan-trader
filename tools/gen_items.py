"""
Generate assets/data/items.json and assets/items/<id>.png from Serebii's
Pokémon Champions item list (https://www.serebii.net/pokemonchampions/items.shtml).

Captures each held item's name, effect description, and icon, so the teambuilder
can offer a searchable item picker with effects and show the item image next to
the Pokémon on the team cards.

Run once (needs internet); outputs are committed:
    python tools/gen_items.py
"""

from __future__ import annotations

import html as _html
import json
import re
import time
import urllib.request
from datetime import date
from pathlib import Path

ITEMS_URL = "https://www.serebii.net/pokemonchampions/items.shtml"
BASE = "https://www.serebii.net"
ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "assets" / "data" / "items.json"
ICON_DIR = ROOT / "assets" / "items"
_HEADERS = {"User-Agent": "Mozilla/5.0 (BerichanCrossTransfer item fetcher)"}

_ROW = re.compile(
    r'/itemdex/([a-z0-9]+)\.shtml"><img src="(/itemdex/sprites/[^"]+\.png)"[^>]*>'
    r'</a></td>\s*<td class="fooinfo"><a href="/itemdex/[a-z0-9]+\.shtml">([^<]+)</a>'
    r'</td>\s*<td class="fooinfo">(.*?)</td>',
    re.DOTALL,
)


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


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return _html.unescape(text).strip()


def main() -> None:
    html = _fetch(ITEMS_URL)
    seen: set[str] = set()
    items: list[dict] = []
    ICON_DIR.mkdir(parents=True, exist_ok=True)

    for item_id, icon_url, name, desc in _ROW.findall(html):
        if item_id in seen:
            continue
        seen.add(item_id)
        items.append({"id": item_id, "name": _clean(name), "desc": _clean(desc)})

    print(f"{len(items)} items parsed; downloading icons…")
    pairs = {m[0]: m[1] for m in _ROW.findall(html)}  # id -> icon url
    ok = 0
    for i, it in enumerate(items, 1):
        dest = ICON_DIR / f"{it['id']}.png"
        if not dest.exists():
            try:
                dest.write_bytes(_fetch(BASE + pairs[it["id"]], binary=True))
            except Exception as exc:  # noqa: BLE001
                print(f"  {it['id']}: icon ERROR {exc}")
        ok += 1
        if i % 40 == 0:
            print(f"  {i}/{len(items)}…")
        time.sleep(0.1)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(
            {"source": "serebii.net pokemonchampions/items",
             "generated": date.today().isoformat(),
             "count": len(items), "items": items},
            indent=1, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {OUT_JSON} ({len(items)} items) and icons in {ICON_DIR}")


if __name__ == "__main__":
    main()
