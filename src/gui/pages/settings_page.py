"""
Settings page: Twitch account (with re-auth + connection check), channel/trade,
timing, the customizable ready sound, and appearance (theme).

Edits the live Config and persists on Save. Theme changes apply live.
"""

from __future__ import annotations

import asyncio
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...config import Config
from ...twitch_auth import SCOPES, missing_scopes, obtain_token, validate_token
from ..sound import BUILTIN_SOUNDS, builtin_token
from ..theme import THEMES

_CUSTOM_LABEL = "Custom file…"


class SettingsPage(QWidget):
    def __init__(
        self,
        cfg: Config,
        sound,
        apply_theme_cb: Callable[[str], None],
        run_wizard_cb: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        self._cfg = cfg
        self._sound = sound
        self._apply_theme_cb = apply_theme_cb
        self._run_wizard_cb = run_wizard_cb

        outer = QVBoxLayout(self)
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        outer.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        self.v = QVBoxLayout(body)
        self.v.addWidget(self._build_account_group())
        self.v.addWidget(self._build_appearance_group())
        self.v.addWidget(self._build_trade_group())
        self.v.addWidget(self._build_timing_group())
        self.v.addWidget(self._build_sound_group())
        self.v.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll, stretch=1)

        save_row = QHBoxLayout()
        save_row.addStretch()
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("Primary")
        self.save_btn.clicked.connect(self._on_save)
        save_row.addWidget(self.save_btn)
        outer.addLayout(save_row)

        self._load_from_config()

    # ------------------------------------------------------------------
    # Groups
    # ------------------------------------------------------------------

    def _build_account_group(self) -> QGroupBox:
        box = QGroupBox("Twitch Account")
        form = QFormLayout(box)
        self.username_edit = QLineEdit()
        self.client_id_edit = QLineEdit()
        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.Password)

        token_row = QHBoxLayout()
        token_row.addWidget(self.token_edit)
        self.reauth_btn = QPushButton("Re-authenticate…")
        self.reauth_btn.clicked.connect(self._on_reauth)
        token_row.addWidget(self.reauth_btn)
        token_widget = QWidget(); token_widget.setLayout(token_row)

        check_row = QHBoxLayout()
        self.check_btn = QPushButton("Check connection")
        self.check_btn.clicked.connect(self._on_check)
        self.wizard_btn = QPushButton("Run setup wizard")
        self.wizard_btn.clicked.connect(lambda: self._run_wizard_cb())
        check_row.addWidget(self.check_btn)
        check_row.addWidget(self.wizard_btn)
        check_row.addStretch()
        check_widget = QWidget(); check_widget.setLayout(check_row)

        self.auth_status = QLabel("")
        self.auth_status.setStyleSheet("color: gray;")

        form.addRow("Username", self.username_edit)
        form.addRow("Client ID", self.client_id_edit)
        form.addRow("OAuth token", token_widget)
        form.addRow("", check_widget)
        form.addRow("", self.auth_status)
        return box

    def _build_appearance_group(self) -> QGroupBox:
        box = QGroupBox("Appearance")
        form = QFormLayout(box)
        self.theme_combo = QComboBox()
        for key, label in THEMES.items():
            self.theme_combo.addItem(label, key)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        form.addRow("Theme", self.theme_combo)
        hint = QLabel("Windows is the native default. Material and Glass are dark themes.")
        hint.setStyleSheet("color: gray;")
        form.addRow("", hint)
        return box

    def _build_trade_group(self) -> QGroupBox:
        box = QGroupBox("Channel & Trade")
        form = QFormLayout(box)
        self.channel_edit = QLineEdit()
        self.bot_edit = QLineEdit()
        self.code_edit = QLineEdit()
        form.addRow("Channel", self.channel_edit)
        form.addRow("Bot username", self.bot_edit)
        form.addRow("Trade code", self.code_edit)
        return box

    def _build_timing_group(self) -> QGroupBox:
        box = QGroupBox("Timing (seconds)")
        form = QFormLayout(box)
        self.line_delay = self._spin(0.0, 10.0, 0.1)
        self.whisper_delay = self._spin(0.0, 30.0, 0.1)
        self.inter_delay = self._spin(0.0, 600.0, 1.0)
        self.timeout = self._spin(10.0, 3600.0, 5.0)
        form.addRow("Line send delay", self.line_delay)
        form.addRow("Post-whisper delay", self.whisper_delay)
        form.addRow("Cooldown between trades", self.inter_delay)
        form.addRow("Trade start timeout", self.timeout)
        return box

    def _build_sound_group(self) -> QGroupBox:
        box = QGroupBox("Ready Sound")
        outer = QVBoxLayout(box)
        self.sound_enabled = QCheckBox("Play a sound when a trade is ready")
        outer.addWidget(self.sound_enabled)

        form = QFormLayout()
        self.sound_combo = QComboBox()
        for name in BUILTIN_SOUNDS:
            self.sound_combo.addItem(name)
        self.sound_combo.addItem(_CUSTOM_LABEL)
        self.sound_combo.currentTextChanged.connect(self._on_sound_choice_changed)
        form.addRow("Sound", self.sound_combo)

        custom_row = QHBoxLayout()
        self.custom_path = QLineEdit()
        self.custom_path.setPlaceholderText("Path to a .wav or .mp3 file")
        self.browse_btn = QPushButton("Browse…")
        self.browse_btn.clicked.connect(self._on_browse)
        custom_row.addWidget(self.custom_path)
        custom_row.addWidget(self.browse_btn)
        self.custom_widget = QWidget(); self.custom_widget.setLayout(custom_row)
        form.addRow("File", self.custom_widget)

        vol_row = QHBoxLayout()
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_label = QLabel("50%")
        self.volume_slider.valueChanged.connect(lambda v: self.volume_label.setText(f"{v}%"))
        self.test_btn = QPushButton("Test ▶")
        self.test_btn.clicked.connect(self._on_test_sound)
        vol_row.addWidget(self.volume_slider)
        vol_row.addWidget(self.volume_label)
        vol_row.addWidget(self.test_btn)
        vol_widget = QWidget(); vol_widget.setLayout(vol_row)
        form.addRow("Volume", vol_widget)
        outer.addLayout(form)
        return box

    @staticmethod
    def _spin(lo: float, hi: float, step: float) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setSingleStep(step)
        s.setDecimals(1)
        return s

    # ------------------------------------------------------------------
    # Load / save
    # ------------------------------------------------------------------

    def _load_from_config(self) -> None:
        c = self._cfg
        self.username_edit.setText(c.username)
        self.client_id_edit.setText(c.client_id)
        self.token_edit.setText(c.oauth_token)
        self.channel_edit.setText(c.channel)
        self.bot_edit.setText(c.bot_username)
        self.code_edit.setText(c.trade_code)
        self.line_delay.setValue(c.line_send_delay)
        self.whisper_delay.setValue(c.post_whisper_delay)
        self.inter_delay.setValue(c.inter_trade_delay)
        self.timeout.setValue(c.trade_timeout)
        self.sound_enabled.setChecked(c.sound_enabled)
        self.volume_slider.setValue(int(round(c.sound_volume * 100)))
        self._select_sound(c.sound_path)
        idx = self.theme_combo.findData(c.theme)
        self.theme_combo.setCurrentIndex(idx if idx >= 0 else 0)

    def reload(self) -> None:
        """Re-pull values from the Config (e.g. after the wizard ran)."""
        self._load_from_config()

    def _select_sound(self, stored: str) -> None:
        builtin_name = None
        if not stored:
            builtin_name = next(iter(BUILTIN_SOUNDS))
        elif stored.startswith("builtin:"):
            filename = stored[len("builtin:"):]
            for name, fn in BUILTIN_SOUNDS.items():
                if fn == filename:
                    builtin_name = name
                    break
        if builtin_name:
            self.sound_combo.setCurrentText(builtin_name)
        else:
            self.sound_combo.setCurrentText(_CUSTOM_LABEL)
            self.custom_path.setText(stored)
        self._on_sound_choice_changed(self.sound_combo.currentText())

    def _current_sound_pref(self) -> str:
        choice = self.sound_combo.currentText()
        if choice == _CUSTOM_LABEL:
            return self.custom_path.text().strip()
        return builtin_token(BUILTIN_SOUNDS[choice])

    def _on_save(self) -> None:
        c = self._cfg
        c.username = self.username_edit.text().strip().lower()
        c.client_id = self.client_id_edit.text().strip()
        c.set_token(self.token_edit.text().strip())
        c.channel = self.channel_edit.text().strip().lower()
        c.bot_username = self.bot_edit.text().strip()
        c.trade_code = self.code_edit.text().strip()
        c.line_send_delay = self.line_delay.value()
        c.post_whisper_delay = self.whisper_delay.value()
        c.inter_trade_delay = self.inter_delay.value()
        c.trade_timeout = self.timeout.value()
        c.sound_enabled = self.sound_enabled.isChecked()
        c.sound_volume = self.volume_slider.value() / 100.0
        c.sound_path = self._current_sound_pref()
        c.theme = self.theme_combo.currentData()
        c.save()
        self.auth_status.setText("✓ Settings saved.")
        self.auth_status.setStyleSheet("color: #27ae60;")

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_theme_changed(self) -> None:
        key = self.theme_combo.currentData()
        if key:
            self._cfg.theme = key
            self._apply_theme_cb(key)

    def _on_sound_choice_changed(self, text: str) -> None:
        self.custom_widget.setEnabled(text == _CUSTOM_LABEL)

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a sound", "", "Audio files (*.wav *.mp3 *.ogg)"
        )
        if path:
            self.custom_path.setText(path)

    def _on_test_sound(self) -> None:
        self._sound.play(self._current_sound_pref(), self.volume_slider.value() / 100.0, True)

    def _on_reauth(self) -> None:
        client_id = self.client_id_edit.text().strip()
        if not client_id:
            self._status("Enter a Client ID first.", error=True)
            return
        asyncio.ensure_future(self._reauthenticate(client_id))

    async def _reauthenticate(self, client_id: str) -> None:
        self.reauth_btn.setEnabled(False)
        self._status("Waiting for browser authorization…")
        loop = asyncio.get_event_loop()
        try:
            token = await loop.run_in_executor(None, obtain_token, client_id)
        except Exception as exc:  # noqa: BLE001
            self._status(f"Auth error: {exc}", error=True)
            self.reauth_btn.setEnabled(True)
            return
        if token:
            self.token_edit.setText(f"oauth:{token}")
            self._status("✓ Token captured. Click Save to keep it.", ok=True)
        else:
            self._status("No token received (timed out).", error=True)
        self.reauth_btn.setEnabled(True)

    def _on_check(self) -> None:
        asyncio.ensure_future(self._check_connection())

    async def _check_connection(self) -> None:
        self.check_btn.setEnabled(False)
        self._status("Checking…")
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, validate_token, self.token_edit.text().strip())
        if not info:
            self._status("Token invalid or expired — re-authenticate.", error=True)
        else:
            missing = missing_scopes(info["scopes"])
            days = info["expires_in"] // 86400
            if missing:
                self._status(
                    f"Connected as {info['login']}, but missing scopes: {', '.join(missing)}. "
                    f"Re-authenticate.",
                    error=True,
                )
            else:
                self._status(
                    f"✓ Connected as {info['login']} · expires in ~{days}d · all scopes present.",
                    ok=True,
                )
        self.check_btn.setEnabled(True)

    def _status(self, text: str, ok: bool = False, error: bool = False) -> None:
        self.auth_status.setText(text)
        color = "#27ae60" if ok else "#c0392b" if error else "gray"
        self.auth_status.setStyleSheet(f"color: {color};")
