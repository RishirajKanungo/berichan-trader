"""
First-run setup wizard.

Walks a new user through the parts that trip people up: creating a Twitch
Developer App (to get a Client ID) and authorizing the app. The redirect URL is
shown with a copy button and there's inline help explaining what a Client ID is.
Runs automatically when the config is incomplete, and is re-runnable from
Settings. On finish it writes and saves the Config.
"""

from __future__ import annotations

import asyncio
import webbrowser

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from ..config import Config
from ..twitch_auth import REDIRECT_URI, SCOPES, missing_scopes, obtain_token, validate_token


def _wrap(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    return lbl


class WelcomePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Welcome")
        layout = QVBoxLayout(self)
        layout.addWidget(_wrap(
            "This app posts your Pokémon team to Berichan's Twitch chat and "
            "whispers your trade code automatically, so you just do the trades "
            "on your Switch.\n\nLet's connect your Twitch account. It takes about "
            "two minutes and you only do it once."
        ))


class UsernamePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Your Twitch username")
        layout = QVBoxLayout(self)
        layout.addWidget(_wrap("Enter your Twitch username (the account that will post)."))
        edit = QLineEdit()
        edit.setPlaceholderText("e.g. kaastre")
        layout.addWidget(edit)
        self.registerField("username*", edit)


class CreateAppPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Create your Twitch app")
        layout = QVBoxLayout(self)
        layout.addWidget(_wrap(
            "Twitch requires each user to register a small (free) developer app "
            "to get a <b>Client ID</b>. Follow these steps:"
        ))
        layout.addWidget(_wrap(
            "1. Open the Twitch Developer Console and click <b>Register Your "
            "Application</b>.<br>"
            "2. Name: anything (e.g. “My Trade Helper”).<br>"
            "3. <b>OAuth Redirect URL</b>: paste the URL below exactly.<br>"
            "4. Category: Application Integration. Click <b>Create</b>.<br>"
            "5. Open the app and copy its <b>Client ID</b> into the box below."
        ))

        open_btn = QPushButton("Open dev.twitch.tv/console")
        open_btn.clicked.connect(lambda: webbrowser.open("https://dev.twitch.tv/console"))
        layout.addWidget(open_btn)

        redirect_row = QHBoxLayout()
        redirect_field = QLineEdit(REDIRECT_URI)
        redirect_field.setReadOnly(True)
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(REDIRECT_URI))
        redirect_row.addWidget(QLabel("Redirect URL:"))
        redirect_row.addWidget(redirect_field)
        redirect_row.addWidget(copy_btn)
        layout.addLayout(redirect_row)

        cid = QLineEdit()
        cid.setPlaceholderText("Paste your Client ID here")
        cid.setToolTip(
            "The Client ID is a public identifier for your Twitch app (not a "
            "password). It's safe to paste here and is stored on your PC only."
        )
        layout.addWidget(QLabel("Client ID:"))
        layout.addWidget(cid)
        self.registerField("client_id*", cid)


class ConnectPage(QWizardPage):
    token_captured = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Connect your account")
        self._token = ""
        layout = QVBoxLayout(self)
        layout.addWidget(_wrap(
            "Click Connect to open Twitch in your browser and authorize the app. "
            f"It requests only these permissions: <b>{SCOPES}</b>."
        ))
        self.connect_btn = QPushButton("Connect Twitch")
        self.connect_btn.clicked.connect(self._on_connect)
        layout.addWidget(self.connect_btn)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        # Hidden field used to gate page completion.
        self._token_field = QLineEdit()
        self._token_field.setVisible(False)
        layout.addWidget(self._token_field)
        self.registerField("token*", self._token_field)

    def _on_connect(self) -> None:
        client_id = self.wizard().field("client_id")
        if not client_id:
            self._set_status("Enter your Client ID on the previous page first.", error=True)
            return
        self.connect_btn.setEnabled(False)
        self._set_status("Waiting for browser authorization…")
        asyncio.ensure_future(self._do_connect(client_id))

    async def _do_connect(self, client_id: str) -> None:
        loop = asyncio.get_event_loop()
        token = await loop.run_in_executor(None, obtain_token, client_id)
        if not token:
            self._set_status("No token received. Try Connect again.", error=True)
            self.connect_btn.setEnabled(True)
            return
        info = await loop.run_in_executor(None, validate_token, token)
        if info and not missing_scopes(info["scopes"]):
            self._token = f"oauth:{token}"
            self._token_field.setText(self._token)
            self._set_status(f"✓ Connected as {info['login']}. You're all set.", ok=True)
            self.completeChanged.emit()
        else:
            missing = missing_scopes(info["scopes"]) if info else SCOPES.split()
            self._set_status(
                f"Authorized, but missing permissions: {', '.join(missing)}. "
                f"Re-run Connect and accept all.",
                error=True,
            )
            self.connect_btn.setEnabled(True)

    def _set_status(self, text: str, ok: bool = False, error: bool = False) -> None:
        self.status.setText(text)
        color = "#27ae60" if ok else "#c0392b" if error else "gray"
        self.status.setStyleSheet(f"color: {color};")

    def isComplete(self) -> bool:  # noqa: N802 (Qt override)
        return bool(self._token)


class DefaultsPage(QWizardPage):
    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.setTitle("Trade defaults")
        layout = QVBoxLayout(self)
        layout.addWidget(_wrap("These have sensible defaults — change only if you know you need to."))

        self.channel = QLineEdit(cfg.channel)
        self.bot = QLineEdit(cfg.bot_username)
        self.code = QLineEdit(cfg.trade_code)
        for label, w in (("Channel", self.channel), ("Bot username", self.bot),
                         ("Trade code", self.code)):
            layout.addWidget(QLabel(label))
            layout.addWidget(w)


class OnboardingWizard(QWizard):
    def __init__(self, cfg: Config, parent=None) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self.setWindowTitle("Setup")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumWidth(520)

        self.addPage(WelcomePage())
        self.addPage(UsernamePage())
        self.addPage(CreateAppPage())
        self.addPage(ConnectPage())
        self._defaults = DefaultsPage(cfg)
        self.addPage(self._defaults)

    def accept(self) -> None:  # noqa: D401 (Qt override)
        c = self._cfg
        c.username = self.field("username").strip().lower()
        c.client_id = self.field("client_id").strip()
        c.set_token(self.field("token").strip())
        c.channel = self._defaults.channel.text().strip().lower()
        c.bot_username = self._defaults.bot.text().strip()
        c.trade_code = self._defaults.code.text().strip()
        c.save()
        super().accept()
