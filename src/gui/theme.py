"""
Theme system: three selectable looks, applied app-wide and switchable live.

  - "windows"  : native Windows look (no stylesheet) — the default.
  - "material" : flat dark Material surfaces, accent color, rounded corners.
  - "glass"    : a frosted dark look — layered translucent panels over a dark
                 gradient base (simulated glass, not desktop see-through).

Implementation note: switching is done with *pure stylesheet swaps only*. We
deliberately do NOT toggle WA_TranslucentBackground or native DWM acrylic at
runtime — doing that on a live window leaves a transparent backing buffer and
half-applied blur, which corrupted the UI when swapping themes and forced a
restart. Stylesheet swaps are fully reversible, so live switching is reliable.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

WINDOWS = "windows"
MATERIAL = "material"
GLASS = "glass"

THEMES: dict[str, str] = {
    WINDOWS: "Windows (native)",
    MATERIAL: "Material",
    GLASS: "Glass (frosted)",
}

ACCENT = "#7c4dff"
ACCENT_HOVER = "#9670ff"

# Shared dark widget styling. {base}/{surface}/{panel}/{border} are filled per
# theme. `base` may be a solid color or a qlineargradient(...) expression.
_DARK_QSS = """
* {{ color: #e8e8ec; font-family: "Segoe UI"; font-size: 10pt; }}
QWidget#Shell {{ background: {base}; }}
QWidget#Page {{ background: transparent; }}
QFrame#Card, QGroupBox {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 10px;
}}
QGroupBox {{ margin-top: 14px; padding: 10px; }}
QGroupBox::title {{
    subcontrol-origin: margin; left: 12px; padding: 0 4px; color: #b9b9c6;
}}
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QDoubleSpinBox, QSpinBox,
QListWidget, QAbstractItemView {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: {accent};
    color: #e8e8ec;
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus,
QDoubleSpinBox:focus, QSpinBox:focus {{ border: 1px solid {accent}; }}
QComboBox QAbstractItemView {{ background: {menu}; }}
QPushButton {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 7px 14px;
}}
QPushButton:hover {{ border: 1px solid {accent}; }}
QPushButton:disabled {{ color: #6b6b78; }}
QPushButton#Primary {{
    background: {accent}; border: none; color: white; font-weight: bold;
}}
QPushButton#Primary:hover {{ background: {accent_hover}; }}
QPushButton#Nav {{
    text-align: left; border: none; border-radius: 8px; padding: 10px 14px;
    background: transparent;
}}
QPushButton#Nav:hover {{ background: {panel}; }}
QPushButton#Nav:checked {{ background: {accent}; color: white; font-weight: bold; }}
QWidget#Sidebar {{ background: {surface}; border-right: 1px solid {border}; }}
QProgressBar {{
    background: {panel}; border: 1px solid {border}; border-radius: 6px;
    text-align: center; height: 18px; color: #e8e8ec;
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 5px; }}
QScrollArea {{ background: transparent; border: none; }}
QLabel#StatusChip {{ border-radius: 9px; padding: 4px 10px; background: {panel}; }}
"""

_MATERIAL_VARS = dict(
    base="#121218", surface="#1c1c26", panel="#262633", menu="#262633",
    border="#33333f", accent=ACCENT, accent_hover=ACCENT_HOVER,
)
# Frosted glass: dark gradient base, light translucent panels layered on top.
_GLASS_VARS = dict(
    base="qlineargradient(x1:0, y1:0, x2:1, y2:1, "
         "stop:0 #15151f, stop:0.5 #1b1b2c, stop:1 #21162e)",
    surface="rgba(255, 255, 255, 0.055)",
    panel="rgba(255, 255, 255, 0.10)",
    menu="#23202e",  # opaque so dropdown popups stay readable
    border="rgba(255, 255, 255, 0.14)",
    accent=ACCENT, accent_hover=ACCENT_HOVER,
)


def apply_theme(app: QApplication, window: QWidget, theme: str) -> None:
    """Apply a theme app-wide. Safe to call repeatedly / live."""
    theme = theme if theme in THEMES else WINDOWS

    # Guard against any translucency left over from older builds in a session.
    window.setAttribute(Qt.WA_TranslucentBackground, False)

    if theme == WINDOWS:
        app.setStyleSheet("")
    elif theme == MATERIAL:
        app.setStyleSheet(_DARK_QSS.format(**_MATERIAL_VARS))
    else:  # GLASS
        app.setStyleSheet(_DARK_QSS.format(**_GLASS_VARS))

    # Force a clean repaint so the swap is immediate and artifact-free.
    window.style().unpolish(window)
    window.style().polish(window)
    window.update()
