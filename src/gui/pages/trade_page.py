"""
Trade page — runs the trade flow for the team built on the Team page.

Pick the game, review the team, Start / Stop. Status, progress and a log update
live; the big "Trade Done" button lights up (and the configurable sound plays)
when each trade is ready. The flow runs as an asyncio task on the qasync loop.
"""

from __future__ import annotations

import asyncio
import html
from typing import Callable

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...config import Config
from ...games import GAME_OPTIONS
from ...trade_manager import TradeManager
from ...twitch_client import TwitchClient
from ..qt_reporter import QtReporter
from ..sound import SoundManager

_LOG_COLORS = {
    "info": "#dddddd",
    "success": "#2ecc71",
    "warn": "#f1c40f",
    "error": "#e74c3c",
}


class TradePage(QWidget):
    def __init__(
        self,
        cfg: Config,
        sound: SoundManager,
        get_team: Callable[[], list],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        self._cfg = cfg
        self._sound = sound
        self._get_team = get_team
        self._reporter = QtReporter(self)
        self._trade_task: asyncio.Task | None = None

        self._build_ui()
        self._connect_reporter()
        self._set_running(False)
        self.refresh_team()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        title = QLabel("Trade")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        root.addWidget(title)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Game:"))
        self.game_combo = QComboBox()
        for opt in GAME_OPTIONS:
            self.game_combo.addItem(f"{opt.label}  ({opt.command})", opt.command)
        controls.addWidget(self.game_combo)
        controls.addStretch()
        self.start_btn = QPushButton("▶ Start Trading")
        self.start_btn.setObjectName("Primary")
        self.start_btn.clicked.connect(self._on_start)
        controls.addWidget(self.start_btn)
        self.stop_btn = QPushButton("■ Stop")
        self.stop_btn.clicked.connect(self._on_stop)
        controls.addWidget(self.stop_btn)
        root.addLayout(controls)

        self.team_summary = QListWidget()
        self.team_summary.setMaximumHeight(130)
        root.addWidget(QLabel("Team to trade:"))
        root.addWidget(self.team_summary)

        self.status_label = QLabel("Idle")
        self.status_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        root.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setFormat("%v / %m Pokémon")
        root.addWidget(self.progress)

        self.done_btn = QPushButton("✓ Trade Done — next Pokémon")
        self.done_btn.setMinimumHeight(48)
        self.done_btn.setStyleSheet(
            "QPushButton:enabled { background-color: #27ae60; color: white;"
            " font-size: 15px; font-weight: bold; border-radius: 6px; }"
        )
        self.done_btn.clicked.connect(self._on_trade_done)
        root.addWidget(self.done_btn)

        root.addWidget(QLabel("Log:"))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 9))
        root.addWidget(self.log_view, stretch=1)

    def _connect_reporter(self) -> None:
        r = self._reporter
        r.log_message.connect(self._append_log)
        r.status_changed.connect(self.status_label.setText)
        r.pokemon_started.connect(self._on_pokemon_started)
        r.queue_joined_sig.connect(
            lambda qid, pos: self._append_log(
                f"[BOT] Queue joined — ID={qid}, Position={pos}", "success"
            )
        )
        r.trade_ready_sig.connect(self._on_trade_ready)
        r.pokemon_finished.connect(self._on_pokemon_finished)
        r.cooldown_sig.connect(self._on_cooldown)
        r.team_finished.connect(self._on_team_finished)

    # ------------------------------------------------------------------
    # Helpers / public
    # ------------------------------------------------------------------

    def refresh_team(self) -> None:
        self.team_summary.clear()
        for i, mon in enumerate(self._get_team(), 1):
            self.team_summary.addItem(f"{i}. {mon.display_name}")

    def _append_log(self, message: str, level: str = "info") -> None:
        color = _LOG_COLORS.get(level, _LOG_COLORS["info"])
        self.log_view.append(f'<span style="color:{color};">{html.escape(message)}</span>')

    def _set_running(self, running: bool) -> None:
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.game_combo.setEnabled(not running)
        if not running:
            self.done_btn.setEnabled(False)

    # ------------------------------------------------------------------
    # Reporter slots
    # ------------------------------------------------------------------

    def _on_pokemon_started(self, index: int, total: int, nick: str, species: str) -> None:
        self.progress.setMaximum(total)
        self.progress.setValue(index - 1)
        label = nick if nick == species else f"{nick} ({species})"
        self._append_log(f"[{index}/{total}] Submitting: {label}", "info")

    def _on_trade_ready(self, pokemon: str, trade_code: str) -> None:
        self._append_log(
            f"TRADE READY: {pokemon} — use code {trade_code} on your Switch, "
            f"then click “Trade Done”.",
            "warn",
        )
        self.done_btn.setEnabled(True)
        self._sound.play(self._cfg.sound_path, self._cfg.sound_volume, self._cfg.sound_enabled)

    def _on_pokemon_finished(self, index: int, total: int) -> None:
        self.progress.setValue(index)
        self.done_btn.setEnabled(False)
        self._append_log("[DONE] Trade confirmed.", "success")

    def _on_cooldown(self, remaining: float, total: float) -> None:
        if remaining > 0:
            self.status_label.setText(f"Cooldown: {remaining:.0f}s until next Pokémon…")
        else:
            self.status_label.setText("Cooldown complete.")

    def _on_team_finished(self, total: int) -> None:
        self._append_log(f"All {total} Pokémon submitted successfully!", "success")
        self.status_label.setText("Done 🎉")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_trade_done(self) -> None:
        self.done_btn.setEnabled(False)
        self._reporter.confirm_done()

    def _on_start(self) -> None:
        errors = self._cfg.validate()
        if errors:
            QMessageBox.warning(
                self,
                "Missing settings",
                "Please finish setup first (Settings):\n  - " + "\n  - ".join(errors),
            )
            return

        team = self._get_team()
        if not team:
            QMessageBox.warning(
                self, "No team", "Build or import a team on the Team page first."
            )
            return

        self._cfg.trade_command = self.game_combo.currentData()
        self._set_running(True)
        self.log_view.clear()
        self._append_log(
            f"Starting: {len(team)} Pokémon → #{self._cfg.channel} "
            f"(game {self._cfg.trade_command})",
            "info",
        )
        self._trade_task = asyncio.ensure_future(self._run_trades(team))

    def _on_stop(self) -> None:
        if self._trade_task and not self._trade_task.done():
            self._append_log("Stopping…", "warn")
            self._trade_task.cancel()

    async def _run_trades(self, team) -> None:
        client = TwitchClient(self._cfg)
        manager = TradeManager(self._cfg, client, self._reporter)
        manager.register()
        listen_task: asyncio.Task | None = None
        try:
            self.status_label.setText("Connecting to Twitch…")
            await client.connect()
            listen_task = asyncio.ensure_future(client.listen())
            await manager.run_team(team)
        except asyncio.CancelledError:
            self.status_label.setText("Stopped.")
            self._append_log("Trading stopped.", "warn")
        except Exception as exc:  # noqa: BLE001 - surface any runtime failure
            self.status_label.setText("Error.")
            self._append_log(f"[ERROR] {exc}", "error")
            QMessageBox.critical(self, "Trade error", str(exc))
        finally:
            if listen_task:
                listen_task.cancel()
                await asyncio.gather(listen_task, return_exceptions=True)
            await client.disconnect()
            self._set_running(False)
            self._trade_task = None
