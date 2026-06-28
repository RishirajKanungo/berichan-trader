"""
A compact card summarizing one Pokemon in the team list, with reorder / edit /
remove controls. Emits signals; the TeamPage owns the actual list mutations.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ... import items as item_db
from ... import pokedex
from ...team_parser import Pokemon


class PokemonCard(QFrame):
    edit_requested = Signal()
    remove_requested = Signal()
    move_up = Signal()
    move_down = Signal()

    def __init__(self, mon: Pokemon, index: int, total: int, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._build(mon, index, total)

    def _build(self, mon: Pokemon, index: int, total: int) -> None:
        row = QHBoxLayout(self)

        num = QLabel(f"{index + 1}")
        num.setStyleSheet("font-size: 14pt; font-weight: bold; color: #7c4dff;")
        num.setFixedWidth(20)
        row.addWidget(num)

        # Pokémon sprite, with the held-item icon tucked beside it.
        sprite = QLabel()
        sprite.setFixedSize(56, 56)
        sprite.setAlignment(Qt.AlignCenter)
        sp = pokedex.get_species(mon.species)
        if sp:
            path = pokedex.sprite_path(sp["id"])
            if path.exists():
                pix = QPixmap(str(path))
                if not pix.isNull():
                    sprite.setPixmap(pix.scaled(56, 56, Qt.KeepAspectRatio,
                                                Qt.SmoothTransformation))
        row.addWidget(sprite)

        item_icon = QLabel()
        item_icon.setFixedSize(32, 32)
        item_icon.setAlignment(Qt.AlignCenter)
        if mon.item:
            ipath = item_db.icon_path(mon.item)
            if ipath and ipath.exists():
                ipix = QPixmap(str(ipath))
                if not ipix.isNull():
                    item_icon.setPixmap(ipix.scaled(28, 28, Qt.KeepAspectRatio,
                                                    Qt.SmoothTransformation))
                    item_icon.setToolTip(mon.item)
        row.addWidget(item_icon)

        info = QVBoxLayout()
        title = QLabel(mon.display_name or "(unnamed)")
        title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        info.addWidget(title)

        meta_bits = []
        if mon.item:
            meta_bits.append(f"@ {mon.item}")
        if mon.ability:
            meta_bits.append(mon.ability)
        if mon.tera_type:
            meta_bits.append(f"Tera {mon.tera_type}")
        if mon.nature:
            meta_bits.append(mon.nature)
        meta = QLabel("  ·  ".join(meta_bits) if meta_bits else "no details")
        meta.setStyleSheet("color: #9a9aa8;")
        info.addWidget(meta)

        if mon.moves:
            moves_row = QHBoxLayout()
            moves_row.setSpacing(8)
            for move in mon.moves:
                chip = QHBoxLayout()
                chip.setSpacing(3)
                m = pokedex.get_move(move)
                if m and m.get("type"):
                    tpath = pokedex.type_icon_path(m["type"])
                    if tpath.exists():
                        tpix = QPixmap(str(tpath))
                        if not tpix.isNull():
                            ic = QLabel()
                            ic.setPixmap(tpix.scaled(28, 13, Qt.KeepAspectRatio,
                                                     Qt.SmoothTransformation))
                            ic.setToolTip(pokedex.move_tooltip(move))
                            chip.addWidget(ic)
                name = QLabel(move)
                name.setStyleSheet("color: #b9b9c6; font-size: 9pt;")
                name.setToolTip(pokedex.move_tooltip(move))
                chip.addWidget(name)
                moves_row.addLayout(chip)
            moves_row.addStretch()
            info.addLayout(moves_row)

        row.addLayout(info, stretch=1)

        up = QPushButton("↑")
        down = QPushButton("↓")
        edit = QPushButton("Edit")
        remove = QPushButton("✕")
        for b in (up, down, edit, remove):
            b.setFixedHeight(28)
        up.setFixedWidth(30)
        down.setFixedWidth(30)
        remove.setFixedWidth(34)
        up.setEnabled(index > 0)
        down.setEnabled(index < total - 1)
        remove.setToolTip("Remove")

        up.clicked.connect(self.move_up.emit)
        down.clicked.connect(self.move_down.emit)
        edit.clicked.connect(self.edit_requested.emit)
        remove.clicked.connect(self.remove_requested.emit)

        for b in (up, down, edit, remove):
            row.addWidget(b)
