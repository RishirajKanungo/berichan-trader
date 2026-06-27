"""
Main application window — an app shell with a left sidebar nav and a stacked
set of pages (Team · Trade · Settings), a title, and a bottom connection-status
chip. The async trade flow runs on the qasync loop so the UI stays responsive.
"""

from __future__ import annotations

import asyncio

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..config import Config
from ..twitch_auth import missing_scopes, validate_token
from .onboarding import OnboardingWizard
from .pages.settings_page import SettingsPage
from .pages.team_page import TeamPage
from .pages.trade_page import TradePage
from .sound import SoundManager
from .theme import apply_theme


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._cfg = Config.load()
        self._sound = SoundManager()

        self.setObjectName("Shell")
        self.setWindowTitle("Berichan Auto Cross-Transfer")
        self.resize(960, 700)

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        # Pages
        self.team_page = TeamPage()
        self.trade_page = TradePage(self._cfg, self._sound, self.team_page.get_team)
        self.settings_page = SettingsPage(
            self._cfg, self._sound, self._apply_theme, self._run_wizard
        )
        self.team_page.team_changed.connect(self.trade_page.refresh_team)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.team_page)
        self.stack.addWidget(self.trade_page)
        self.stack.addWidget(self.settings_page)
        root.addWidget(self.stack, stretch=1)

    def _build_sidebar(self) -> QWidget:
        side = QWidget()
        side.setObjectName("Sidebar")
        side.setFixedWidth(190)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(12, 18, 12, 12)

        title = QLabel("Berichan\nCross-Transfer")
        title.setStyleSheet("font-size: 13pt; font-weight: bold;")
        layout.addWidget(title)
        layout.addSpacing(16)

        self._nav_group = QButtonGroup(self)
        for i, name in enumerate(("Team", "Trade", "Settings")):
            btn = QPushButton(name)
            btn.setObjectName("Nav")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, idx=i: self.stack.setCurrentIndex(idx))
            self._nav_group.addButton(btn, i)
            layout.addWidget(btn)
        self._nav_group.button(0).setChecked(True)

        layout.addStretch()
        self.status_chip = QLabel("Not connected")
        self.status_chip.setObjectName("StatusChip")
        self.status_chip.setWordWrap(True)
        layout.addWidget(self.status_chip)
        return side

    # ------------------------------------------------------------------
    # Startup hooks (called after show, so winId()/acrylic work)
    # ------------------------------------------------------------------

    def on_shown(self) -> None:
        self._apply_theme(self._cfg.theme)
        if self._cfg.validate():
            QTimer.singleShot(0, self._run_wizard)
        else:
            asyncio.ensure_future(self._refresh_status())

    def _apply_theme(self, theme: str) -> None:
        apply_theme(QApplication.instance(), self, theme)

    def _run_wizard(self) -> None:
        wizard = OnboardingWizard(self._cfg, self)
        if wizard.exec():
            self.settings_page.reload()
            asyncio.ensure_future(self._refresh_status())

    async def _refresh_status(self) -> None:
        self.status_chip.setText("Checking…")
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, validate_token, self._cfg.oauth_token)
        if not info:
            self._set_chip("⚠ Not connected", "#c0392b")
        elif missing_scopes(info["scopes"]):
            self._set_chip(f"⚠ {info['login']}: missing scopes", "#e67e22")
        else:
            days = info["expires_in"] // 86400
            self._set_chip(f"● {info['login']} · {days}d left", "#27ae60")

    def _set_chip(self, text: str, color: str) -> None:
        self.status_chip.setText(text)
        self.status_chip.setStyleSheet(
            f"QLabel#StatusChip {{ color: {color}; border-radius: 9px;"
            f" padding: 4px 10px; }}"
        )
