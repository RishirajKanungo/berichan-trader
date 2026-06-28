"""
Generate assets/data/legality.json — for every species, the set of moves it can
legally learn (across games), from Pokémon Showdown's learnset data.

This powers the web teambuilder's legality check: Berichan injects sets into the
mainline games (Scarlet/Violet etc.), so a move the species genuinely can't learn
(e.g. Sneasler + Fake Out) makes PKHeX reject the trade ("Unable to legalize").
Champions movepools are broader than the mainline games', so we validate against
what the species can actually learn.

We use "learnable in any game" (not strictly gen-9) because most learnset moves
transfer into SV via HOME, so this catches the real errors with few false
positives.

Run once (needs internet); output is committed:
    python tools/gen_legality.py
"""

from __future__ import annotations

import json
import urllib.request
from datetime import date
from pathlib import Path

LEARNSETS_URL = "https://play.pokemonshowdown.com/data/learnsets.json"
OUT = Path(__file__).resolve().parent.parent / "assets" / "data" / "legality.json"
_HEADERS = {"User-Agent": "Mozilla/5.0 (BerichanCrossTransfer legality gen)"}


def main() -> None:
    req = urllib.request.Request(LEARNSETS_URL, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        learnsets = json.loads(r.read())

    species: dict[str, list[str]] = {}
    for sid, info in learnsets.items():
        lset = info.get("learnset")
        if lset:
            species[sid] = sorted(lset.keys())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {"source": "pokemonshowdown learnsets", "generated": date.today().isoformat(),
             "note": "per-species move ids the Pokémon can learn (any game)", "species": species},
            separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    kb = OUT.stat().st_size / 1024
    print(f"Wrote {OUT} ({len(species)} species, {kb:.0f} KB)")


if __name__ == "__main__":
    main()
