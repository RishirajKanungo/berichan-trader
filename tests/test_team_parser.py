"""Showdown parse / serialize round-trip tests."""

from berichan.team_parser import parse_pokemon, parse_team

# Self-contained sample team (a small, generic Showdown export) so the tests
# don't depend on any external file.
SAMPLE_TEAM = """\
KRATOS (Incineroar) (M) @ Sitrus Berry
Ability: Intimidate
Level: 50
Tera Type: Grass
EVs: 252 HP / 4 Atk / 252 SpD
Careful Nature
- Fake Out
- Knock Off
- Parting Shot
- Flare Blitz

Garchomp @ Life Orb
Ability: Rough Skin
Level: 50
Shiny: Yes
Tera Type: Steel
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Earthquake
- Dragon Claw
- Rock Slide
- Protect
"""


def _team():
    return parse_team(SAMPLE_TEAM)


def test_parses_team():
    team = _team()
    assert len(team) == 2
    assert team[0].species == "Incineroar"
    assert team[0].nickname == "KRATOS"
    assert team[1].species == "Garchomp"


def test_roundtrip_preserves_fields():
    """parse -> to_showdown -> parse must reproduce identical structured fields."""
    for mon in _team():
        again = parse_pokemon(mon.to_showdown())
        assert again is not None
        for field in ("nickname", "species", "item", "ability", "tera_type",
                      "nature", "gender", "level", "shiny", "evs", "ivs", "moves"):
            assert getattr(again, field) == getattr(mon, field), field


def test_imported_chat_message_is_stable():
    """Imported sets keep their original lines, so the trade payload is unchanged."""
    for mon in _team():
        assert mon.chat_message == " ".join(mon.lines)
