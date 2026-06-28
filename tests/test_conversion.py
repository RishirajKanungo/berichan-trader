"""
Champions Stat-Point ↔ mainline EV conversion tests.

These guard the legalization rule: a built set must stay within the mainline
510-total / 252-per-stat EV limits, or Berichan refuses to legalize it.
"""

from berichan import pokedex
from berichan.team_parser import STAT_ORDER


def test_sp_to_ev_endpoints():
    assert pokedex.sp_to_ev(0) == 0
    assert pokedex.sp_to_ev(2) == 16
    assert pokedex.sp_to_ev(31) == 248
    assert pokedex.sp_to_ev(32) == 252  # maxed stat == classic 252 EVs


def test_full_spread_is_mainline_legal():
    """A full 66-SP spread must clamp to <=510 total and <=252 per stat."""
    sp = {"HP": 2, "Atk": 32, "Def": 0, "SpA": 0, "SpD": 0, "Spe": 32}  # 66 SP
    ev = pokedex.sp_spread_to_evs(sp)
    assert sum(ev.values()) <= 510
    assert all(v <= 252 for v in ev.values())
    # Maxed stats stay exact; only the dump stat is trimmed.
    assert ev["Atk"] == 252 and ev["Spe"] == 252


def test_small_spread_unchanged():
    sp = {s: 0 for s in STAT_ORDER}
    sp["HP"], sp["Def"] = 10, 10
    ev = pokedex.sp_spread_to_evs(sp)
    assert ev["HP"] == 80 and ev["Def"] == 80
    assert sum(ev.values()) == 160


def test_champions_formula_matches_mainline_with_converted_evs():
    """calc_stat_sp(SP) must equal the standard formula at IV 31, EV = 8*SP."""
    base = pokedex.get_species("Garchomp")["baseStats"]
    sp = {"HP": 0, "Atk": 32, "Def": 0, "SpA": 0, "SpD": 0, "Spe": 32}
    champ = pokedex.calc_all_stats_sp(base, sp, 50, "Jolly")
    evs = {lab: pokedex.sp_to_ev(sp[lab]) for lab in STAT_ORDER}
    ivs = {lab: 31 for lab in STAT_ORDER}
    standard = pokedex.calc_all_stats(base, ivs, evs, 50, "Jolly")
    assert champ == standard
