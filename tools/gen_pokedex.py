"""
Generate assets/data/champions.json — the bundled Pokédex the teambuilder uses.

Source: Serebii's Pokémon Champions Pokédex (the authoritative, current source
for this game), parsed directly:
  - roster:  https://www.serebii.net/pokemonchampions/pokemon.shtml
  - per-mon: https://www.serebii.net/pokedex-champions/<slug>/

For each legal species we capture: name, dex number, types, base stats, the
legal abilities, and the full Champions movepool (the "Standard Moves" table).

Run once (needs internet); the JSON is committed so users never fetch anything:
    python tools/gen_pokedex.py

Be polite: this fetches ~200 pages with a small delay between requests.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from datetime import date
from pathlib import Path

ROSTER_URL = "https://www.serebii.net/pokemonchampions/pokemon.shtml"
SPECIES_URL = "https://www.serebii.net/pokedex-champions/{slug}/"
OUT_PATH = Path(__file__).resolve().parent.parent / "assets" / "data" / "champions.json"

_HEADERS = {"User-Agent": "Mozilla/5.0 (BerichanCrossTransfer dataset generator)"}
_STAT_KEYS = ["hp", "atk", "def", "spa", "spd", "spe"]


def _fetch(url: str, retries: int = 3) -> str:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last}")


def parse_roster(html: str) -> list[dict]:
    """Return [{slug, name, num}] in listed order, deduped."""
    # Each row pairs a dex number with the species link in the same row:
    #   #NNNN ... <a href="/pokedex-champions/<slug>/"><img alt="<Name> Image"
    pattern = re.compile(
        r'#(\d{4}).*?/pokedex-champions/([a-z0-9\-\.\%]+)/"><img[^>]*alt="([^"]+?) Image"',
        re.IGNORECASE | re.DOTALL,
    )
    out: list[dict] = []
    seen: set[str] = set()
    for num, slug, name in pattern.findall(html):
        if slug in seen:
            continue
        seen.add(slug)
        out.append({"slug": slug, "name": name.strip(), "num": int(num)})
    return out


def parse_species(html: str) -> dict:
    head = html[: html.find("Abilities")] if "Abilities" in html else html

    # Types: /pokedex-champions/<type>.shtml links (typeimg), before Abilities.
    types = []
    for t in re.findall(r'/pokedex-champions/([a-z]+)\.shtml"', head):
        cap = t.capitalize()
        if cap not in types:
            types.append(cap)
    types = types[:2]

    # Abilities: from the "Abilities:" header row, the abilitydex links.
    abilities: list[str] = []
    am = re.search(r"<b>Abilities</b>:(.*?)</tr>", html, re.DOTALL)
    if am:
        for a in re.findall(r'/abilitydex/[^"]+"><b>([^<]+)</b>', am.group(1)):
            if a not in abilities:
                abilities.append(a)

    # Base stats: 6 fooinfo cells right after "Base Stats - Total:".
    base: dict[str, int] = {}
    bm = re.search(r"Base Stats - Total:\s*\d+(.*?)</tr>", html, re.DOTALL)
    if bm:
        cells = re.findall(r'class="fooinfo">(\d+)</td>', bm.group(1))
        if len(cells) >= 6:
            base = {k: int(cells[i]) for i, k in enumerate(_STAT_KEYS)}

    # Moves: the Champions movepool (attackdex-champions anchors), deduped.
    moves: list[str] = []
    for mv in re.findall(r'/attackdex-champions/[a-z0-9\-]+\.shtml">([^<]+)</a>', html):
        mv = mv.strip()
        if mv and mv not in moves:
            moves.append(mv)
    moves.sort()

    return {"types": types, "abilities": abilities, "baseStats": base, "moves": moves}


def main() -> None:
    print("Fetching roster…")
    roster = parse_roster(_fetch(ROSTER_URL))
    print(f"  {len(roster)} species")

    species: list[dict] = []
    for i, entry in enumerate(roster, 1):
        slug = entry["slug"]
        try:
            data = parse_species(_fetch(SPECIES_URL.format(slug=slug)))
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i}/{len(roster)}] {slug}: ERROR {exc}")
            continue
        species.append({
            "id": slug,
            "name": entry["name"],
            "num": entry["num"],
            **data,
        })
        ok = bool(data["baseStats"] and data["abilities"] and data["moves"])
        flag = "" if ok else "  <-- incomplete"
        print(f"  [{i}/{len(roster)}] {entry['name']}: "
              f"{len(data['moves'])} moves, {len(data['abilities'])} abilities{flag}")
        time.sleep(0.2)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "serebii.net pokedex-champions",
        "generated": date.today().isoformat(),
        "count": len(species),
        "species": species,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {OUT_PATH} ({len(species)} species)")


if __name__ == "__main__":
    main()
