"""
Team page — the teambuilder foundation.

Owns the current team (list[Pokemon]) and presents it as editable cards. A team
can be built from scratch, imported from a Showdown export, edited per-Pokemon,
reordered, and saved/loaded by name. The Trade page reads the current team from
here via get_team().
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ... import team_store
from ...team_parser import Pokemon, parse_team, team_to_showdown
from ..widgets.pokemon_card import PokemonCard
from ..widgets.pokemon_editor import PokemonEditor
from ..widgets.species_picker import SpeciesPicker


class TeamPage(QWidget):
    team_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        self._team: list[Pokemon] = []
        self._build_ui()
        self._rebuild_cards()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_team(self) -> list[Pokemon]:
        return self._team

    def set_team(self, team: list[Pokemon]) -> None:
        self._team = team
        self._rebuild_cards()
        self.team_changed.emit()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("Team Builder")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #9a9aa8;")
        header.addWidget(self.count_label)
        root.addLayout(header)

        # toolbar
        bar = QHBoxLayout()
        self.add_btn = QPushButton("+ Add Pokémon")
        self.add_btn.setObjectName("Primary")
        self.add_btn.clicked.connect(self._on_add)
        self.import_btn = QPushButton("Import from Showdown")
        self.import_btn.setCheckable(True)
        self.import_btn.toggled.connect(self._toggle_import)
        self.save_btn = QPushButton("Save team")
        self.save_btn.clicked.connect(self._on_save)
        self.load_btn = QPushButton("Load team")
        self.load_btn.clicked.connect(self._on_load)
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self._on_export)
        for b in (self.add_btn, self.import_btn, self.save_btn, self.load_btn, self.export_btn):
            bar.addWidget(b)
        bar.addStretch()
        root.addLayout(bar)

        # collapsible import panel
        self.import_panel = QFrame()
        self.import_panel.setObjectName("Card")
        ip = QVBoxLayout(self.import_panel)
        ip.addWidget(QLabel("Paste a Showdown export, then Import (replaces the current team):"))
        self.import_text = QPlainTextEdit()
        self.import_text.setPlaceholderText("Paste exported Showdown team here…")
        self.import_text.setFixedHeight(150)
        ip.addWidget(self.import_text)
        ip_row = QHBoxLayout()
        ip_row.addStretch()
        do_import = QPushButton("Import")
        do_import.setObjectName("Primary")
        do_import.clicked.connect(self._do_import)
        ip_row.addWidget(do_import)
        ip.addLayout(ip_row)
        self.import_panel.setVisible(False)
        root.addWidget(self.import_panel)

        # scrollable card list
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.card_host = QWidget()
        self.card_layout = QVBoxLayout(self.card_host)
        self.card_layout.addStretch()
        self.scroll.setWidget(self.card_host)
        root.addWidget(self.scroll, stretch=1)

        self.empty_label = QLabel(
            "No Pokémon yet. Click “+ Add Pokémon” or import a Showdown team."
        )
        self.empty_label.setStyleSheet("color: #9a9aa8; padding: 20px;")
        root.addWidget(self.empty_label)

    def _rebuild_cards(self) -> None:
        # clear existing cards (keep trailing stretch)
        while self.card_layout.count() > 1:
            item = self.card_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        total = len(self._team)
        for i, mon in enumerate(self._team):
            card = PokemonCard(mon, i, total)
            card.edit_requested.connect(lambda idx=i: self._on_edit(idx))
            card.remove_requested.connect(lambda idx=i: self._on_remove(idx))
            card.move_up.connect(lambda idx=i: self._move(idx, -1))
            card.move_down.connect(lambda idx=i: self._move(idx, 1))
            self.card_layout.insertWidget(i, card)

        self.empty_label.setVisible(total == 0)
        self.count_label.setText(f"{total} Pokémon")

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _toggle_import(self, on: bool) -> None:
        self.import_panel.setVisible(on)

    def _do_import(self) -> None:
        team = parse_team(self.import_text.toPlainText())
        if not team:
            QMessageBox.warning(self, "Nothing imported", "No Pokémon were parsed.")
            return
        self._team = team
        self.import_text.clear()
        self.import_btn.setChecked(False)
        self._rebuild_cards()
        self.team_changed.emit()

    def _on_add(self) -> None:
        picker = SpeciesPicker(self)
        if not picker.exec():
            return
        species = picker.selected_species()
        dlg = PokemonEditor(species=species, parent=self)
        if dlg.exec():
            self._team.append(dlg.result_pokemon())
            self._rebuild_cards()
            self.team_changed.emit()

    def _on_edit(self, index: int) -> None:
        if not (0 <= index < len(self._team)):
            return
        dlg = PokemonEditor(self._team[index], parent=self)
        if dlg.exec():
            self._team[index] = dlg.result_pokemon()
            self._rebuild_cards()
            self.team_changed.emit()

    def _on_remove(self, index: int) -> None:
        if 0 <= index < len(self._team):
            del self._team[index]
            self._rebuild_cards()
            self.team_changed.emit()

    def _move(self, index: int, delta: int) -> None:
        j = index + delta
        if 0 <= index < len(self._team) and 0 <= j < len(self._team):
            self._team[index], self._team[j] = self._team[j], self._team[index]
            self._rebuild_cards()
            self.team_changed.emit()

    def _on_save(self) -> None:
        if not self._team:
            QMessageBox.information(self, "Empty team", "Add some Pokémon first.")
            return
        name, ok = QInputDialog.getText(self, "Save team", "Team name:")
        if ok and name.strip():
            team_store.save_team(name.strip(), self._team)
            QMessageBox.information(self, "Saved", f"Saved team “{name.strip()}”.")

    def _on_load(self) -> None:
        names = team_store.list_teams()
        if not names:
            QMessageBox.information(self, "No saved teams", "You haven't saved any teams yet.")
            return
        name, ok = QInputDialog.getItem(self, "Load team", "Choose a team:", names, 0, False)
        if ok and name:
            self.set_team(team_store.load_team(name))

    def _on_export(self) -> None:
        if not self._team:
            return
        text = team_to_showdown(self._team)
        QApplication.clipboard().setText(text)
        QMessageBox.information(
            self, "Exported", "Showdown team copied to clipboard."
        )
