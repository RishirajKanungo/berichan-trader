"""
Reporter interface that decouples the trade flow from any particular UI.

TradeManager talks to a TradeReporter instead of calling print()/input()/
winsound directly. This lets the same async flow drive either the terminal
(ConsoleReporter) or the desktop GUI (a Qt-backed reporter).

Lifecycle hooks are plain methods (fire-and-forget UI updates). The only
blocking interaction is wait_for_trade_done(), which the UI resolves when the
user confirms a trade finished on the Switch.
"""

from __future__ import annotations

import asyncio
import sys

from colorama import Fore, Style, init as _colorama_init

_colorama_init()

_SEP = "=" * 62


class TradeReporter:
    """Default reporter: silent no-ops. Subclass and override what you need."""

    def log(self, message: str, level: str = "info") -> None:
        """Free-form progress text. level in {info, success, warn, error}."""

    def set_status(self, status: str) -> None:
        """High-level state label, e.g. 'Waiting for queue…'."""

    def pokemon_start(self, index: int, total: int, nickname: str, species: str) -> None:
        ...

    def queue_joined(self, queue_id: str, position: str) -> None:
        ...

    def trade_ready(self, pokemon: str, trade_code: str) -> None:
        """Trade is live — play the alert and prompt the user to act."""

    def pokemon_done(self, index: int, total: int) -> None:
        ...

    def cooldown_tick(self, remaining: float, total: float) -> None:
        ...

    def team_complete(self, total: int) -> None:
        ...

    async def wait_for_trade_done(self) -> None:
        """Block until the user confirms the current trade is complete."""
        return None


# ----------------------------------------------------------------------
# Console implementation (preserves the original CLI behavior)
# ----------------------------------------------------------------------

_LEVEL_COLOR = {
    "info": Fore.CYAN,
    "success": Fore.GREEN,
    "warn": Fore.YELLOW,
    "error": Fore.RED,
}


def _alert_sound() -> None:
    """Play 3 short beeps on Windows to signal it's trade time."""
    try:
        import winsound
        for _ in range(3):
            winsound.Beep(1000, 250)
    except Exception:
        pass  # Non-Windows or no audio device — silent fallback


class ConsoleReporter(TradeReporter):
    def log(self, message: str, level: str = "info") -> None:
        color = _LEVEL_COLOR.get(level, Fore.CYAN)
        print(f"{color}{message}{Style.RESET_ALL}")

    def pokemon_start(self, index: int, total: int, nickname: str, species: str) -> None:
        print(
            f"\n{Fore.BLUE}[{index}/{total}] Submitting: "
            f"{nickname} ({species}){Style.RESET_ALL}"
        )

    def queue_joined(self, queue_id: str, position: str) -> None:
        print(
            f"\n{Fore.GREEN}[BOT] Queue joined — "
            f"ID={queue_id}, Position={position}{Style.RESET_ALL}"
        )

    def trade_ready(self, pokemon: str, trade_code: str) -> None:
        _alert_sound()
        print(f"\n{Fore.YELLOW}{_SEP}")
        print(f"  TRADE READY: {pokemon}")
        print(f"  Use code   : {trade_code}  on your Switch")
        print(f"  Search for the trade NOW, then press ENTER when done.")
        print(f"{_SEP}{Style.RESET_ALL}\n")

    def pokemon_done(self, index: int, total: int) -> None:
        print(f"{Fore.GREEN}[DONE] Trade confirmed.{Style.RESET_ALL}")

    def cooldown_tick(self, remaining: float, total: float) -> None:
        # Only announce at the start of the cooldown to avoid console spam.
        if abs(remaining - total) < 0.5:
            print(
                f"\n{Fore.CYAN}[COOLDOWN] Waiting {total:.0f}s "
                f"before next Pokemon…{Style.RESET_ALL}"
            )

    def team_complete(self, total: int) -> None:
        print(f"\n{Fore.GREEN}All {total} Pokemon submitted successfully!{Style.RESET_ALL}")

    async def wait_for_trade_done(self) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sys.stdin.readline)
