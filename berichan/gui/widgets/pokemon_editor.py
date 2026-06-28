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

import asyncio

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
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ... import items as item_db
from ... import meta as meta_db
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
        self.setMinimumWidth(520)
        self.resize(560, 760)

        self._build_ui()
        self._load(mon)
        self._update_char_count()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        body = QWidget()
        layout = QVBoxLayout(body)

        if self._species:
            layout.addLayout(self._build_header())
            meta_panel = self._build_meta_panel()
            if meta_panel:
                layout.addWidget(meta_panel)

        ident = QGroupBox("Identity")
        form = QFormLayout(ident)
        self.nickname = QLineEdit()
        self.gender = QComboBox(); self.gender.addItems(["—", "M", "F"])
        self.item: QWidget = _combo(item_db.all_names()) if item_db.is_loaded() else QLineEdit()
        self.item_desc = QLabel()
        self.item_desc.setWordWrap(True)
        self.item_desc.setStyleSheet("color: #9a9aa8; font-size: 9pt;")
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
        self.ability_desc = QLabel()
        self.ability_desc.setWordWrap(True)
        self.ability_desc.setStyleSheet("color: #9a9aa8; font-size: 9pt;")

        form.addRow("Species", self.species_field)
        form.addRow("Nickname", self.nickname)
        form.addRow("Ability", self.ability)
        form.addRow("", self.ability_desc)
        form.addRow("Item", self.item)
        form.addRow("", self.item_desc)
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

        # Moves — each slot shows type + category icons and a live summary.
        moves_box = QGroupBox("Moves")
        mlayout = QVBoxLayout(moves_box)
        movepool = self._species.get("moves", []) if self._species else []
        self.moves: list[QWidget] = []
        self.move_info: list[QLabel] = []
        self.move_type_icon: list[QLabel] = []
        self.move_cat_icon: list[QLabel] = []
        for i in range(4):
            w = _combo(movepool) if self._species else QLineEdit()
            if not self._species:
                w.setPlaceholderText(f"Move {i + 1}")
            mlayout.addWidget(w)

            detail = QHBoxLayout()
            type_icon = QLabel(); type_icon.setFixedSize(36, 16)
            cat_icon = QLabel(); cat_icon.setFixedSize(22, 16)
            info = QLabel(); info.setStyleSheet("color: #9a9aa8; font-size: 8pt;")
            detail.addWidget(type_icon)
            detail.addWidget(cat_icon)
            detail.addWidget(info, stretch=1)
            mlayout.addLayout(detail)

            self._connect_text(w, self._update_char_count)
            self._connect_text(w, lambda idx=i: self._update_move_info(idx))
            self.moves.append(w)
            self.move_info.append(info)
            self.move_type_icon.append(type_icon)
            self.move_cat_icon.append(cat_icon)
        layout.addWidget(moves_box)

        self.char_label = QLabel("")
        self.char_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.char_label)

        self.nickname.textChanged.connect(self._update_char_count)
        self._connect_text(self.item, self._update_char_count)
        self._connect_text(self.item, self._update_item_desc)
        self._connect_text(self.ability, self._update_char_count)
        self._connect_text(self.ability, self._update_ability_desc)
        self._connect_text(self.tera, self._update_char_count)
        if isinstance(self.species_field, QLineEdit):
            self.species_field.textChanged.connect(self._update_char_count)

        scroll.setWidget(body)
        outer.addWidget(scroll, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def _build_meta_panel(self) -> QWidget | None:
        if not (self._species and meta_db.is_loaded()):
            return None
        box = QGroupBox(f"Recommended (meta · {meta_db.season()})")
        v = QVBoxLayout(box)

        top = QHBoxLayout()
        self.meta_format = QComboBox()
        self.meta_format.addItems(meta_db.FORMATS)
        self.meta_format.currentTextChanged.connect(self._refresh_meta_display)
        apply_btn = QPushButton("Apply set")
        apply_btn.setObjectName("Primary")
        apply_btn.clicked.connect(self._apply_recommended)
        self.meta_refresh_btn = QPushButton("Refresh")
        self.meta_refresh_btn.setToolTip("Re-pull the latest usage data from the API")
        self.meta_refresh_btn.clicked.connect(self._on_refresh_meta)
        top.addWidget(self.meta_format)
        top.addStretch()
        top.addWidget(apply_btn)
        top.addWidget(self.meta_refresh_btn)
        v.addLayout(top)

        self.meta_summary = QLabel()
        self.meta_summary.setWordWrap(True)
        self.meta_summary.setTextFormat(Qt.RichText)
        self.meta_summary.setStyleSheet("font-size: 9pt;")
        v.addWidget(self.meta_summary)
        self._refresh_meta_display()
        return box

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

        type_row = QHBoxLayout()
        for t in self._species.get("types", []):
            icon = QLabel()
            tpath = pokedex.type_icon_path(t)
            if tpath.exists():
                pix = QPixmap(str(tpath))
                if not pix.isNull():
                    icon.setPixmap(pix.scaled(46, 20, Qt.KeepAspectRatio,
                                              Qt.SmoothTransformation))
            icon.setToolTip(t)
            type_row.addWidget(icon)
        type_row.addStretch()

        bs = self._species["baseStats"]
        bst = sum(bs.values())
        stat_line = QLabel(
            "  ".join(f"{pokedex.STAT_LABELS[k]} {bs[k]}" for k in pokedex.STAT_KEYS)
            + f"   ·   BST {bst}"
        )
        stat_line.setStyleSheet("color: #b9b9c6; font-size: 9pt;")
        info.addWidget(name)
        info.addLayout(type_row)
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
        self._update_ability_desc()
        self._set_text(self.item, mon.item)
        self._update_item_desc()
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
            self._update_move_info(i)

    def _build_pokemon(self) -> Pokemon:
        species = self._text(self.species_field)
        nick = self.nickname.text().strip() or species
        sp = self.spread.get_sp()
        mon = Pokemon(
            nickname=nick,
            species=species,
            gender="" if self.gender.currentText() == "—" else self.gender.currentText(),
            item=self._text(self.item),
            ability=self._text(self.ability),
            level=self.level.value(),
            shiny=self.shiny.isChecked(),
            tera_type=self._text(self.tera),
            nature=self.nature.currentText().strip(),
            # SP -> legal mainline EVs (<=252/stat, <=510 total); IVs perfect.
            evs=pokedex.sp_spread_to_evs(sp),
            moves=[self._text(w) for w in self.moves if self._text(w)],
        )
        mon.sync_lines()
        return mon

    # ------------------------------------------------------------------
    # Live updates
    # ------------------------------------------------------------------

    def _update_item_desc(self) -> None:
        self.item_desc.setText(item_db.describe(self._text(self.item)))

    def _update_ability_desc(self) -> None:
        self.ability_desc.setText(pokedex.ability_desc(self._text(self.ability)))

    def _update_move_info(self, index: int) -> None:
        name = self._text(self.moves[index])
        self.move_info[index].setText(pokedex.move_summary(name))
        self.moves[index].setToolTip(pokedex.move_tooltip(name))
        m = pokedex.get_move(name)
        self._set_icon(self.move_type_icon[index],
                       pokedex.type_icon_path(m["type"]) if m and m.get("type") else None, 32, 14)
        self._set_icon(self.move_cat_icon[index],
                       pokedex.category_icon_path(m["category"]) if m and m.get("category") else None, 20, 14)

    @staticmethod
    def _set_icon(label: QLabel, path, w: int, h: int) -> None:
        if path and path.exists():
            pix = QPixmap(str(path))
            if not pix.isNull():
                label.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
        label.clear()

    # ------------------------------------------------------------------
    # Recommended (meta) panel
    # ------------------------------------------------------------------

    @staticmethod
    def _spread_str(sp: dict) -> str:
        return "/".join(str(sp.get(s, 0)) for s in STAT_ORDER) + " SP"

    def _refresh_meta_display(self) -> None:
        fmt = self.meta_format.currentText()
        d = meta_db.get(self._species["id"], fmt)
        if not d:
            self.meta_summary.setText(
                "<i>No usage data for this Pokémon in this format. "
                "Try Refresh or the other format.</i>"
            )
            return
        def line(label, pairs):
            inner = " · ".join(f"{n} {p:.0f}%" for n, p in pairs)
            return f"<b>{label}:</b> {inner}" if inner else ""
        parts = [
            line("Moves", [(m[0], m[1]) for m in d.get("moves", [])[:4]]),
            line("Item", [(i[0], i[1]) for i in d.get("items", [])[:2]]),
            line("Ability", [(a[0], a[1]) for a in d.get("abilities", [])[:2]]),
            line("Nature", [(n[0], n[1]) for n in d.get("natures", [])[:2]]),
        ]
        spreads = d.get("spreads", [])
        if spreads:
            sp, pct = spreads[0]
            parts.append(f"<b>Spread:</b> {self._spread_str(sp)} {pct:.0f}%")
        self.meta_summary.setText("<br>".join(p for p in parts if p))

    def _apply_recommended(self) -> None:
        rec = meta_db.recommended(self._species["id"], self.meta_format.currentText())
        if not rec:
            return
        if rec.get("ability"):
            self._set_text(self.ability, rec["ability"]); self._update_ability_desc()
        if rec.get("item"):
            self._set_text(self.item, rec["item"]); self._update_item_desc()
        if rec.get("nature"):
            self.nature.setCurrentText(rec["nature"])
        if rec.get("spread"):
            self.spread.set_sp(rec["spread"])
        for i in range(4):
            self._set_text(self.moves[i], rec["moves"][i] if i < len(rec["moves"]) else "")
            self._update_move_info(i)
        self._update_char_count()

    def _on_refresh_meta(self) -> None:
        asyncio.ensure_future(self._refresh_meta_async())

    async def _refresh_meta_async(self) -> None:
        self.meta_refresh_btn.setEnabled(False)
        self.meta_refresh_btn.setText("Refreshing…")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, meta_db.refresh_species, self._species["id"], self._species["name"]
        )
        self.meta_refresh_btn.setEnabled(True)
        self.meta_refresh_btn.setText("Refresh")
        self._refresh_meta_display()

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
