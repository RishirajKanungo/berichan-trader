"""
Showdown-style editor for a single Pokémon, Champions-accurate.

When the species is known (picked from the Champions roster, or an existing
team member whose species is in the dex) the editor shows its sprite and
constrains choices to that species: abilities become a dropdown of its legal
abilities and the four move slots autocomplete from its movepool.

Stats use the Champions Stat Point (SP) system via StatSpreadWidget (66 SP
total, 32 per stat, no IVs). On save, SP is converted to the EVs the Switch
game uses (EV = SP*8, capped 252) so the set Berichan injects is correct.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ... import pokedex
from ...team_parser import STAT_ORDER, TWITCH_MAX_CHAT_LENGTH, Pokemon
from .stat_spread import StatSpreadWidget

NATURES = list(pokedex.NATURES.keys())
TYPES = [
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting",
    "Poison", "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon",
    "Dark", "Steel", "Fairy", "Stellar",
]


def _combo(items: list[str], value: str = "") -> QComboBox:
    """An editable combo with case-insensitive 'contains' autocomplete."""
    c = QComboBox()
    c.setEditable(True)
    c.setInsertPolicy(QComboBox.NoInsert)
    c.addItem("")
    c.addItems(items)
    comp = c.completer()
    comp.setCompletionMode(QCompleter.PopupCompletion)
    comp.setFilterMode(Qt.MatchContains)
    comp.setCaseSensitivity(Qt.CaseInsensitive)
    c.setCurrentText(value)
    return c


class PokemonEditor(QDialog):
    def __init__(
        self,
        mon: Pokemon | None = None,
        species: dict | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        mon = mon or Pokemon()
        self._species = species or pokedex.get_species(mon.species)
        if self._species and not mon.species:
            mon.species = self._species["name"]
        self.setWindowTitle(f"Edit {mon.species}" if mon.species else "Add Pokémon")
        self.setMinimumWidth(500)

        self._build_ui()
        self._load(mon)
        self._update_char_count()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        if self._species:
            layout.addLayout(self._build_header())

        ident = QGroupBox("Identity")
        form = QFormLayout(ident)
        self.nickname = QLineEdit()
        self.gender = QComboBox(); self.gender.addItems(["—", "M", "F"])
        self.item = QLineEdit()
        self.level = QSpinBox(); self.level.setRange(0, 100); self.level.setValue(50)
        self.shiny = QCheckBox("Shiny")
        self.tera = _combo(TYPES)
        self.nature = QComboBox(); self.nature.addItems(NATURES)

        if self._species:
            self.species_field: QWidget = QLabel(self._species["name"])
            self.ability: QWidget = _combo(self._species.get("abilities", []))
        else:
            self.species_field = QLineEdit()
            self.ability = QLineEdit()

        form.addRow("Species", self.species_field)
        form.addRow("Nickname", self.nickname)
        form.addRow("Ability", self.ability)
        form.addRow("Item", self.item)
        form.addRow("Gender", self.gender)
        form.addRow("Level", self.level)
        form.addRow("Tera Type", self.tera)
        form.addRow("Nature", self.nature)
        form.addRow("", self.shiny)
        layout.addWidget(ident)

        # Stat spread (SP system, slider + pie views)
        base_stats = self._species["baseStats"] if self._species else {}
        stats_box = QGroupBox("Stats — Stat Points (max 32 each, 66 total)")
        sbl = QVBoxLayout(stats_box)
        self.spread = StatSpreadWidget(base_stats, level=50)
        self.spread.changed.connect(self._update_char_count)
        sbl.addWidget(self.spread)
        layout.addWidget(stats_box)
        self.level.valueChanged.connect(self.spread.set_level)
        self.nature.currentTextChanged.connect(self.spread.set_nature)

        # Moves
        moves_box = QGroupBox("Moves")
        mlayout = QVBoxLayout(moves_box)
        movepool = self._species.get("moves", []) if self._species else []
        self.moves: list[QWidget] = []
        for i in range(4):
            w = _combo(movepool) if self._species else QLineEdit()
            if not self._species:
                w.setPlaceholderText(f"Move {i + 1}")
            self._connect_text(w, self._update_char_count)
            self.moves.append(w)
            mlayout.addWidget(w)
        layout.addWidget(moves_box)

        self.char_label = QLabel("")
        self.char_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.char_label)

        for w in (self.nickname, self.item):
            w.textChanged.connect(self._update_char_count)
        self._connect_text(self.ability, self._update_char_count)
        self._connect_text(self.tera, self._update_char_count)
        if isinstance(self.species_field, QLineEdit):
            self.species_field.textChanged.connect(self._update_char_count)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        sprite = QLabel()
        path = pokedex.sprite_path(self._species["id"])
        if path.exists():
            pix = QPixmap(str(path))
            if not pix.isNull():
                sprite.setPixmap(pix.scaled(96, 96, Qt.KeepAspectRatio,
                                            Qt.SmoothTransformation))
        sprite.setFixedSize(96, 96)
        sprite.setAlignment(Qt.AlignCenter)
        row.addWidget(sprite)

        info = QVBoxLayout()
        name = QLabel(f"<b style='font-size:14pt'>{self._species['name']}</b>")
        types = QLabel("  ".join(self._species.get("types", [])))
        types.setStyleSheet("color: #9a9aa8;")
        bs = self._species["baseStats"]
        bst = sum(bs.values())
        stat_line = QLabel(
            "  ".join(f"{pokedex.STAT_LABELS[k]} {bs[k]}" for k in pokedex.STAT_KEYS)
            + f"   ·   BST {bst}"
        )
        stat_line.setStyleSheet("color: #b9b9c6; font-size: 9pt;")
        info.addWidget(name)
        info.addWidget(types)
        info.addStretch()
        info.addWidget(stat_line)
        row.addLayout(info, stretch=1)
        return row

    @staticmethod
    def _connect_text(widget: QWidget, slot) -> None:
        if isinstance(widget, QComboBox):
            widget.currentTextChanged.connect(lambda _=None: slot())
        else:
            widget.textChanged.connect(lambda _=None: slot())

    @staticmethod
    def _text(widget: QWidget) -> str:
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        return widget.text().strip()

    @staticmethod
    def _set_text(widget: QWidget, value: str) -> None:
        if isinstance(widget, QComboBox):
            widget.setCurrentText(value)
        elif isinstance(widget, QLineEdit):
            widget.setText(value)

    # ------------------------------------------------------------------
    # Load / build
    # ------------------------------------------------------------------

    def _load(self, mon: Pokemon) -> None:
        self._set_text(self.species_field, mon.species)
        self.nickname.setText("" if mon.nickname == mon.species else mon.nickname)
        self.gender.setCurrentText(mon.gender or "—")
        self._set_text(self.ability, mon.ability)
        self.item.setText(mon.item)
        if mon.level:
            self.level.setValue(mon.level)
        self.shiny.setChecked(mon.shiny)
        self._set_text(self.tera, mon.tera_type)
        self.nature.setCurrentText(mon.nature)
        # Existing EVs (from an imported set) convert back to SP for editing.
        self.spread.set_sp({s: pokedex.ev_to_sp(mon.evs.get(s, 0)) for s in STAT_ORDER})
        self.spread.set_level(mon.level or 50)
        self.spread.set_nature(mon.nature)
        for i, w in enumerate(self.moves):
            self._set_text(w, mon.moves[i] if i < len(mon.moves) else "")

    def _build_pokemon(self) -> Pokemon:
        species = self._text(self.species_field)
        nick = self.nickname.text().strip() or species
        sp = self.spread.get_sp()
        mon = Pokemon(
            nickname=nick,
            species=species,
            gender="" if self.gender.currentText() == "—" else self.gender.currentText(),
            item=self.item.text().strip(),
            ability=self._text(self.ability),
            level=self.level.value(),
            shiny=self.shiny.isChecked(),
            tera_type=self._text(self.tera),
            nature=self.nature.currentText().strip(),
            # SP -> EV for the Switch game; IVs stay perfect (31 -> omitted).
            evs={s: pokedex.sp_to_ev(sp[s]) for s in STAT_ORDER},
            moves=[self._text(w) for w in self.moves if self._text(w)],
        )
        mon.sync_lines()
        return mon

    # ------------------------------------------------------------------
    # Live updates
    # ------------------------------------------------------------------

    def _update_char_count(self) -> None:
        length = len(self._build_pokemon().chat_message)
        over = length > (TWITCH_MAX_CHAT_LENGTH - 12)  # room for "!tradeXX "
        self.char_label.setText(f"{length} / {TWITCH_MAX_CHAT_LENGTH} chars")
        self.char_label.setStyleSheet("color: #e74c3c;" if over else "color: gray;")

    def _on_accept(self) -> None:
        if not self._text(self.species_field):
            if isinstance(self.species_field, QLineEdit):
                self.species_field.setFocus()
            return
        self.accept()

    def result_pokemon(self) -> Pokemon:
        return self._build_pokemon()
