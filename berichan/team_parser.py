"""
Parse Pokemon Showdown team export format into structured Pokemon objects,
and serialize them back out (so the GUI can edit teams, not just paste them).

Showdown export format (one Pokemon):

    PENATRATOR (Excadrill) (M) @ No Item
    Ability: Sand Rush
    Level: 50
    Shiny: Yes
    Tera Type: Ground
    EVs: 4 HP / 252 Atk / 252 Spe
    Adamant Nature
    IVs: 0 Atk
    - Rock Slide
    - Protect
    - High Horsepower
    - Iron Head

Multiple Pokemon are separated by one or more blank lines.

Design note: for *imported* Pokemon we keep the original `lines` verbatim, so
`chat_message` (what the trade flow sends) is byte-identical to before. For
Pokemon *built or edited* in the GUI, `sync_lines()` regenerates `lines` from
`to_showdown()`, so edits are reflected in what gets traded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# Twitch chat limit for most accounts (single PRIVMSG must stay under this).
TWITCH_MAX_CHAT_LENGTH = 500

# Canonical stat order used by Showdown for EV/IV lines.
STAT_ORDER = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"]
DEFAULT_IV = 31


def _empty_evs() -> dict[str, int]:
    return {s: 0 for s in STAT_ORDER}


def _default_ivs() -> dict[str, int]:
    return {s: DEFAULT_IV for s in STAT_ORDER}


@dataclass
class Pokemon:
    nickname: str = ""          # Custom nickname if set, otherwise species name
    species: str = ""           # Species name (from parentheses, or same as nickname)
    lines: list[str] = field(default_factory=list)   # Non-empty lines of the block
    raw_block: str = ""         # Original text of the block

    # Structured fields (parsed from the block; editable in the GUI).
    gender: str = ""            # "M", "F", or "" (genderless / unspecified)
    item: str = ""
    ability: str = ""
    level: int = 0              # 0 = unspecified
    shiny: bool = False
    tera_type: str = ""
    nature: str = ""
    evs: dict[str, int] = field(default_factory=_empty_evs)
    ivs: dict[str, int] = field(default_factory=_default_ivs)
    moves: list[str] = field(default_factory=list)

    @property
    def chat_message(self) -> str:
        """Single-line Showdown set for one Twitch chat message (Berichan format)."""
        return " ".join(self.lines)

    @property
    def display_name(self) -> str:
        if self.nickname and self.nickname != self.species:
            return f"{self.nickname} ({self.species})"
        return self.species or self.nickname

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_showdown(self) -> str:
        """Render this Pokemon back to a Showdown set block."""
        out: list[str] = [self._header_line()]
        if self.ability:
            out.append(f"Ability: {self.ability}")
        if self.level:
            out.append(f"Level: {self.level}")
        if self.shiny:
            out.append("Shiny: Yes")
        if self.tera_type:
            out.append(f"Tera Type: {self.tera_type}")
        ev_line = self._stat_line(self.evs, 0)
        if ev_line:
            out.append(f"EVs: {ev_line}")
        if self.nature:
            out.append(f"{self.nature} Nature")
        iv_line = self._stat_line(self.ivs, DEFAULT_IV)
        if iv_line:
            out.append(f"IVs: {iv_line}")
        for move in self.moves:
            if move:
                out.append(f"- {move}")
        return "\n".join(out)

    def sync_lines(self) -> None:
        """Regenerate `lines`/`raw_block` from the structured fields (after edits)."""
        self.raw_block = self.to_showdown()
        self.lines = [ln for ln in self.raw_block.splitlines() if ln.strip()]

    def _header_line(self) -> str:
        name = self.species or self.nickname
        if self.nickname and self.nickname != self.species:
            name = f"{self.nickname} ({self.species})"
        if self.gender in ("M", "F"):
            name = f"{name} ({self.gender})"
        if self.item:
            name = f"{name} @ {self.item}"
        return name

    @staticmethod
    def _stat_line(stats: dict[str, int], default: int) -> str:
        parts = [
            f"{stats[s]} {s}" for s in STAT_ORDER if stats.get(s, default) != default
        ]
        return " / ".join(parts)


# ----------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------

def _parse_header(first_line: str) -> tuple[str, str, str, str]:
    """
    Return (nickname, species, gender, item) from a Showdown header line.

    Examples:
      "Excadrill @ Item"                 -> ("Excadrill", "Excadrill", "", "Item")
      "PENATRATOR (Excadrill) (M) @ X"   -> ("PENATRATOR", "Excadrill", "M", "X")
      "Grimmsnarl (M) @ Item"            -> ("Grimmsnarl", "Grimmsnarl", "M", "Item")
    """
    item = ""
    if "@" in first_line:
        base, item = re.split(r"\s*@\s*", first_line, maxsplit=1)
        base, item = base.strip(), item.strip()
    else:
        base = first_line.strip()

    gender = ""
    gm = re.search(r"\(([MF])\)", base)
    if gm:
        gender = gm.group(1)
        base = re.sub(r"\s*\([MF]\)\s*", " ", base).strip()

    paren = re.findall(r"\(([^)]+)\)", base)
    if paren:
        species = paren[0]
        nickname = base.split("(")[0].strip() or species
    else:
        species = base
        nickname = base

    return nickname, species, gender, item


def _parse_stats(text: str, default: int) -> dict[str, int]:
    stats = {s: default for s in STAT_ORDER}
    for chunk in text.split("/"):
        m = re.match(r"\s*(\d+)\s+(\w+)", chunk.strip())
        if m:
            value, label = int(m.group(1)), m.group(2)
            for s in STAT_ORDER:
                if s.lower() == label.lower():
                    stats[s] = value
    return stats


def parse_pokemon(block: str) -> Pokemon | None:
    """Parse a single Showdown block into a Pokemon, or None if empty."""
    block = block.strip()
    if not block:
        return None
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    if not lines:
        return None

    nickname, species, gender, item = _parse_header(lines[0])
    mon = Pokemon(
        nickname=nickname,
        species=species,
        lines=lines,
        raw_block=block,
        gender=gender,
        item=item,
    )

    for line in lines[1:]:
        low = line.lower()
        if low.startswith("ability:"):
            mon.ability = line.split(":", 1)[1].strip()
        elif low.startswith("level:"):
            try:
                mon.level = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif low.startswith("shiny:"):
            mon.shiny = line.split(":", 1)[1].strip().lower().startswith("y")
        elif low.startswith("tera type:"):
            mon.tera_type = line.split(":", 1)[1].strip()
        elif low.startswith("evs:"):
            mon.evs = _parse_stats(line.split(":", 1)[1], 0)
        elif low.startswith("ivs:"):
            mon.ivs = _parse_stats(line.split(":", 1)[1], DEFAULT_IV)
        elif low.endswith("nature"):
            mon.nature = line.rsplit(" ", 1)[0].strip()
        elif line.startswith("-"):
            mon.moves.append(line.lstrip("-").strip())

    return mon


def parse_team(text: str) -> list[Pokemon]:
    """
    Parse a full Pokemon Showdown team export into a list of Pokemon.
    Returns an empty list if no valid blocks are found.
    """
    blocks = re.split(r"\n(?:\s*\n)+", text.strip())
    team: list[Pokemon] = []
    for block in blocks:
        mon = parse_pokemon(block)
        if mon:
            team.append(mon)
    return team


def team_to_showdown(team: list[Pokemon]) -> str:
    """Serialize a whole team back to Showdown export text."""
    return "\n\n".join(mon.to_showdown() for mon in team)
