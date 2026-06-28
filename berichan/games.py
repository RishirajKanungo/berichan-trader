"""Berichan Twitch trade commands per Switch game."""

from __future__ import annotations

from dataclasses import dataclass

from colorama import Fore, Style


@dataclass(frozen=True)
class GameOption:
    index: int
    label: str
    command: str


# Order matches the interactive menu (0–3).
GAME_OPTIONS: tuple[GameOption, ...] = (
    GameOption(0, "Scarlet / Violet", "!tradeSV"),
    GameOption(1, "Sword / Shield", "!tradeSWSH"),
    GameOption(2, "Legends Z-A", "!tradePLZ"),
    GameOption(3, "Legends Arceus", "!tradePLA"),
)

# Available via Berichan docs but not in the default menu.
EXTRA_GAME_COMMANDS: dict[str, str] = {
    "bdsp": "!tradeBDSP",
}


def prompt_game() -> GameOption:
    """Ask which Switch game to trade into (options 0–3)."""
    print(f"\n{Fore.CYAN}Which Switch game are you trading into?{Style.RESET_ALL}")
    for opt in GAME_OPTIONS:
        print(f"  {opt.index}. {opt.label}  ({opt.command})")

    while True:
        raw = input(f"\n{Fore.CYAN}Enter 0–3: {Style.RESET_ALL}").strip()
        if raw.isdigit():
            idx = int(raw)
            for opt in GAME_OPTIONS:
                if opt.index == idx:
                    print(
                        f"{Fore.GREEN}Selected: {opt.label} → {opt.command}{Style.RESET_ALL}"
                    )
                    return opt
        print(f"{Fore.RED}Invalid choice — enter a number from 0 to 3.{Style.RESET_ALL}")


def format_trade_message(command: str, showdown_set: str) -> str:
    """Prefix a Showdown set with the Berichan !trade* command."""
    return f"{command} {showdown_set}"
