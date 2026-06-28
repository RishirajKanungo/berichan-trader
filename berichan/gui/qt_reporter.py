"""
Qt-backed TradeReporter.

Bridges the async trade flow to the GUI. Because qasync runs the asyncio loop
on the Qt thread, reporter methods (called from the trade coroutine) and the
GUI slots run on the same thread, so emitting signals here is safe and direct.

The one blocking interaction — wait_for_trade_done() — is resolved by the user
clicking the "Trade Done" button, which calls confirm_done().
"""

from __future__ import annotations

import asyncio

from PySide6.QtCore import QObject, Signal

from ..reporter import TradeReporter


class QtReporter(QObject, TradeReporter):
    log_message = Signal(str, str)          # (message, level)
    status_changed = Signal(str)            # high-level status label
    pokemon_started = Signal(int, int, str, str)  # (index, total, nickname, species)
    queue_joined_sig = Signal(str, str)     # (queue_id, position)
    trade_ready_sig = Signal(str, str)      # (pokemon, trade_code)
    pokemon_finished = Signal(int, int)     # (index, total)
    cooldown_sig = Signal(float, float)     # (remaining, total)
    team_finished = Signal(int)             # (total)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._done_event = asyncio.Event()

    # --- TradeReporter API (called from the async trade task) ---------

    def log(self, message: str, level: str = "info") -> None:
        self.log_message.emit(message, level)

    def set_status(self, status: str) -> None:
        self.status_changed.emit(status)

    def pokemon_start(self, index: int, total: int, nickname: str, species: str) -> None:
        self.pokemon_started.emit(index, total, nickname, species)

    def queue_joined(self, queue_id: str, position: str) -> None:
        self.queue_joined_sig.emit(queue_id, position)

    def trade_ready(self, pokemon: str, trade_code: str) -> None:
        self._done_event.clear()
        self.trade_ready_sig.emit(pokemon, trade_code)

    def pokemon_done(self, index: int, total: int) -> None:
        self.pokemon_finished.emit(index, total)

    def cooldown_tick(self, remaining: float, total: float) -> None:
        self.cooldown_sig.emit(remaining, total)

    def team_complete(self, total: int) -> None:
        self.team_finished.emit(total)

    async def wait_for_trade_done(self) -> None:
        await self._done_event.wait()

    # --- Called from the GUI thread -----------------------------------

    def confirm_done(self) -> None:
        """Resolve the current wait_for_trade_done()."""
        self._done_event.set()
