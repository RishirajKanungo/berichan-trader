"""
Searchable picker for the legal Champions roster — the first step of the
Showdown-style "Add Pokémon" flow. Pick a species, then the editor opens
constrained to that species' abilities and movepool.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ... import pokedex


class SpeciesPicker(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Choose a Pokémon")
        self.setMinimumSize(380, 520)
        self._selected: dict | None = None

        layout = QVBoxLayout(self)
        if not pokedex.is_loaded():
            layout.addWidget(QLabel(
                "Pokédex data not found.\n\nRun  python tools/gen_pokedex.py  to "
                "build assets/data/champions.json, then reopen."
            ))
            return

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search the Champions roster…")
        self.search.textChanged.connect(self._refilter)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.setIconSize(QSize(40, 40))
        self.list.itemActivated.connect(lambda _: self._choose())
        self.list.itemDoubleClicked.connect(lambda _: self._choose())
        layout.addWidget(self.list, stretch=1)

        self.hint = QLabel("Double-click or press Enter to select.")
        self.hint.setStyleSheet("color: gray;")
        layout.addWidget(self.hint)

        self._populate(pokedex.all_species())
        self.search.setFocus()

    def _populate(self, species: list[dict]) -> None:
        self.list.clear()
        for sp in species:
            types = "/".join(sp.get("types", []))
            item = QListWidgetItem(f"#{sp.get('num', 0):04d}  {sp['name']}   —   {types}")
            item.setData(Qt.UserRole, sp)
            path = pokedex.sprite_path(sp["id"])
            if path.exists():
                item.setIcon(QIcon(str(path)))
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _refilter(self, text: str) -> None:
        self._populate(pokedex.search(text))

    def _choose(self) -> None:
        item = self.list.currentItem()
        if item:
            self._selected = item.data(Qt.UserRole)
            self.accept()

    def selected_species(self) -> dict | None:
        return self._selected
