"""
Editor for a Pokémon's stat spread in Champions "Stat Point" (SP) units.

Two interchangeable views over the same SP values:
  - "Sliders": a Showdown-style row of per-stat sliders (0–32 SP).
  - "Pie": an interactive radial chart — drag a stat's spoke outward from the
    center to raise it.

Both enforce the Champions limits (32 SP per stat, 66 SP total) and show the
resulting real stat at Level 50. SP converts to EVs at trade time (pokedex).
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ... import pokedex
from ...team_parser import STAT_ORDER

_ACCENT = QColor(124, 77, 255)
_LABEL_FOR_KEY = pokedex.STAT_LABELS  # hp->HP, etc.
_KEY_FOR_LABEL = {v: k for k, v in _LABEL_FOR_KEY.items()}

# Per-stat accent colors (Showdown-ish) for the slider rows.
_STAT_COLOR = {
    "HP": "#ff5959", "Atk": "#f5ac78", "Def": "#fae078",
    "SpA": "#9db7f5", "SpD": "#a7db8d", "Spe": "#fa92b2",
}
_STAT_MAX = 255  # upper bound for the visual bar


def _bar_color(value: int) -> QColor:
    """Red (low) → yellow → green (high), like a stat bar."""
    f = max(0.0, min(1.0, value / 200.0))
    if f < 0.5:
        r, g = 255, int(140 + 200 * (f / 0.5))
    else:
        r, g = int(255 - 200 * ((f - 0.5) / 0.5)), 220
    return QColor(min(r, 255), min(g, 255), 90)


class _StatBar(QWidget):
    """A compact colored bar showing a computed stat value (0–255)."""

    def __init__(self) -> None:
        super().__init__()
        self._value = 0
        self.setMinimumWidth(140)
        self.setFixedHeight(16)

    def set_value(self, value: int) -> None:
        self._value = value
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 28))
        p.drawRoundedRect(0, 0, w, h, 5, 5)
        frac = max(0.0, min(1.0, self._value / _STAT_MAX))
        if frac > 0:
            p.setBrush(_bar_color(self._value))
            p.drawRoundedRect(0, 0, int(w * frac), h, 5, 5)


class StatSpreadWidget(QWidget):
    changed = Signal()

    def __init__(self, base_stats: dict[str, int], level: int = 50,
                 nature: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._base = base_stats  # keyed by STAT_KEYS (hp, atk, …)
        self._level = level
        self._nature = nature
        self._sp = {s: 0 for s in STAT_ORDER}

        root = QVBoxLayout(self)

        # mode toggle
        toggle = QHBoxLayout()
        self.total_label = QLabel()
        toggle.addWidget(self.total_label)
        toggle.addStretch()
        self._group = QButtonGroup(self)
        for i, name in enumerate(("Sliders", "Pie")):
            b = QPushButton(name)
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, idx=i: self._stack.setCurrentIndex(idx))
            self._group.addButton(b, i)
            toggle.addWidget(b)
        self._group.button(0).setChecked(True)
        root.addLayout(toggle)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_sliders())
        self._pie = _PieEditor(self)
        self._stack.addWidget(self._pie)
        root.addWidget(self._stack)

        self._refresh()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_sp(self) -> dict[str, int]:
        return dict(self._sp)

    def set_sp(self, sp: dict[str, int]) -> None:
        for s in STAT_ORDER:
            self._sp[s] = max(0, min(pokedex.SP_MAX_PER_STAT, int(sp.get(s, 0))))
        self._refresh()

    def set_level(self, level: int) -> None:
        self._level = level
        self._refresh()

    def set_nature(self, nature: str) -> None:
        self._nature = nature
        self._refresh()

    def computed(self) -> dict[str, int]:
        return pokedex.calc_all_stats_sp(self._base, self._sp, self._level, self._nature)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_sliders(self) -> QWidget:
        page = QWidget()
        grid = QGridLayout(page)
        grid.setHorizontalSpacing(10)
        for col, head in ((0, ""), (1, "Base"), (2, "SP"), (3, "EV"), (5, "Stat")):
            if head:
                h = QLabel(head)
                h.setStyleSheet("color: #9a9aa8; font-size: 8pt;")
                grid.addWidget(h, 0, col)
        grid.setColumnStretch(4, 1)  # slider column grows
        self._sliders: dict[str, QSlider] = {}
        self._sp_labels: dict[str, QLabel] = {}
        self._ev_labels: dict[str, QLabel] = {}
        self._base_labels: dict[str, QLabel] = {}
        self._total_labels: dict[str, QLabel] = {}
        self._bars: dict[str, _StatBar] = {}
        for row, stat in enumerate(STAT_ORDER, start=1):
            name = QLabel(stat)
            name.setStyleSheet(f"color: {_STAT_COLOR[stat]}; font-weight: bold;")
            name.setFixedWidth(34)
            grid.addWidget(name, row, 0)
            base = QLabel("—"); base.setFixedWidth(28)
            base.setStyleSheet("color: #b9b9c6;"); self._base_labels[stat] = base
            grid.addWidget(base, row, 1)
            sp = QLabel("0"); sp.setFixedWidth(22); self._sp_labels[stat] = sp
            grid.addWidget(sp, row, 2)
            ev = QLabel("0"); ev.setFixedWidth(28)
            ev.setStyleSheet("color: #9a9aa8; font-size: 8pt;"); self._ev_labels[stat] = ev
            grid.addWidget(ev, row, 3)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, pokedex.SP_MAX_PER_STAT)
            slider.valueChanged.connect(lambda v, s=stat: self._set_stat(s, v))
            self._sliders[stat] = slider
            grid.addWidget(slider, row, 4)
            total = QLabel("—"); total.setStyleSheet("font-weight: bold;")
            total.setFixedWidth(30); self._total_labels[stat] = total
            grid.addWidget(total, row, 5)
            bar = _StatBar(); self._bars[stat] = bar
            grid.addWidget(bar, row, 6)
        grid.setColumnStretch(6, 1)  # stat bar grows too
        return page

    def _set_stat(self, stat: str, value: int) -> None:
        value = max(0, min(pokedex.SP_MAX_PER_STAT, value))
        # Enforce the 66-SP total budget.
        others = sum(v for s, v in self._sp.items() if s != stat)
        value = min(value, pokedex.SP_MAX_TOTAL - others)
        if value == self._sp[stat]:
            self._refresh()  # snap any over-budget slider attempt back
            return
        self._sp[stat] = value
        self._refresh()
        self.changed.emit()

    def _refresh(self) -> None:
        totals = self.computed()
        for stat in STAT_ORDER:
            key = _KEY_FOR_LABEL[stat]
            self._base_labels[stat].setText(str(self._base.get(key, "—")))
            sl = self._sliders[stat]
            sl.blockSignals(True)
            sl.setValue(self._sp[stat])
            sl.blockSignals(False)
            self._sp_labels[stat].setText(str(self._sp[stat]))
            self._ev_labels[stat].setText(str(pokedex.sp_to_ev(self._sp[stat])))
            self._total_labels[stat].setText(str(totals[key]))
            self._bars[stat].set_value(totals[key])
        used = sum(self._sp.values())
        over = used > pokedex.SP_MAX_TOTAL
        self.total_label.setText(f"SP used: {used} / {pokedex.SP_MAX_TOTAL}")
        self.total_label.setStyleSheet("color: #e74c3c;" if over else "color: gray;")
        self._pie.update()


class _PieEditor(QWidget):
    """Radial SP editor: drag a stat's spoke outward to set its value."""

    def __init__(self, owner: StatSpreadWidget) -> None:
        super().__init__(owner)
        self._owner = owner
        self.setMinimumSize(280, 280)
        # Stat axes evenly around the circle, HP at top, clockwise.
        self._angles = {
            stat: math.radians(-90 + 60 * i) for i, stat in enumerate(STAT_ORDER)
        }

    # --- geometry helpers ---
    def _center_radius(self):
        m = 54  # margin for labels
        r = (min(self.width(), self.height()) - 2 * m) / 2
        return QPointF(self.width() / 2, self.height() / 2), max(20.0, r)

    def _point(self, center: QPointF, radius: float, stat: str, frac: float) -> QPointF:
        a = self._angles[stat]
        return QPointF(center.x() + radius * frac * math.cos(a),
                       center.y() + radius * frac * math.sin(a))

    # --- painting ---
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        center, R = self._center_radius()
        sp = self._owner._sp
        totals = self._owner.computed()

        # rings
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        for frac in (0.25, 0.5, 0.75, 1.0):
            poly = QPolygonF([self._point(center, R, s, frac) for s in STAT_ORDER])
            p.drawPolygon(poly)
        # axes
        for s in STAT_ORDER:
            p.drawLine(center, self._point(center, R, s, 1.0))

        # filled SP polygon
        poly = QPolygonF([
            self._point(center, R, s, sp[s] / pokedex.SP_MAX_PER_STAT) for s in STAT_ORDER
        ])
        fill = QColor(_ACCENT); fill.setAlpha(90)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(_ACCENT, 2))
        p.drawPolygon(poly)

        # handles + labels
        p.setBrush(QBrush(_ACCENT))
        font = QFont("Segoe UI", 8)
        p.setFont(font)
        for s in STAT_ORDER:
            frac = sp[s] / pokedex.SP_MAX_PER_STAT
            h = self._point(center, R, s, frac)
            p.setPen(Qt.NoPen)
            p.drawEllipse(h, 4, 4)
            label = self._point(center, R + 22, s, 1.0)
            p.setPen(QColor(232, 232, 236))
            key = _KEY_FOR_LABEL[s]
            p.drawText(QPointF(label.x() - 18, label.y()), f"{s} {totals[key]}")
            p.setPen(QColor(160, 160, 175))
            p.drawText(QPointF(label.x() - 10, label.y() + 13), f"{sp[s]} SP")

    # --- interaction ---
    def mousePressEvent(self, event) -> None:
        self._apply(event.position())

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.LeftButton:
            self._apply(event.position())

    def _apply(self, pos: QPointF) -> None:
        center, R = self._center_radius()
        dx, dy = pos.x() - center.x(), pos.y() - center.y()
        if dx == 0 and dy == 0:
            return
        cursor = math.atan2(dy, dx)
        # nearest stat axis by angle
        best, best_d = None, 9.9
        for s, a in self._angles.items():
            d = abs(math.atan2(math.sin(cursor - a), math.cos(cursor - a)))
            if d < best_d:
                best, best_d = s, d
        dist = math.hypot(dx, dy)
        sp = round(dist / R * pokedex.SP_MAX_PER_STAT)
        self._owner._set_stat(best, sp)
