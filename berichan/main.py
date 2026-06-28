"""
Entry point for the Berichan Auto Cross-Transfer tool.

This is the optional command-line interface; most users run the desktop app
(`python -m berichan.gui`, or the packaged BerichanCrossTransfer.exe).

Usage:
    python -m berichan.main                     # paste team interactively
    python -m berichan.main myteam.txt          # load from a file
    python -m berichan.main --code 12345678     # override trade code for this run

Credentials come from environment variables (or a local .env). The desktop app's
setup wizard is the easiest way to configure them.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from colorama import Fore, Style, init as colorama_init

from .config import Config
from .games import prompt_game
from .reporter import ConsoleReporter
from .team_parser import parse_team
from .twitch_client import TwitchClient
from .trade_manager import TradeManager

colorama_init()

BANNER = f"""
{Fore.MAGENTA}╔══════════════════════════════════════════════════════════════╗
║         Berichan Auto Cross-Transfer  v1.0                  ║
║   Pokemon Showdown  →  Twitch Chat  →  Switch Trade         ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""


def _read_team_interactive() -> str:
    print(
        f"{Fore.CYAN}Paste your Pokemon Showdown team export below.\n"
        f"Press ENTER on a blank line twice when finished:\n{Style.RESET_ALL}"
    )
    lines: list[str] = []
    blank_streak = 0
    while True:
        try:
            line = input()
        except EOFError:
            break
        lines.append(line)
        if line.strip() == "":
            blank_streak += 1
            if blank_streak >= 2:
                break
        else:
            blank_streak = 0
    return "\n".join(lines)


def _print_team_summary(
    pokemon_list, trade_code: str, channel: str, bot: str, trade_command: str
) -> None:
    print(f"\n{Fore.GREEN}Parsed {len(pokemon_list)} Pokemon:{Style.RESET_ALL}")
    for i, mon in enumerate(pokemon_list, 1):
        label = mon.nickname if mon.nickname != mon.species else mon.species
        if mon.nickname != mon.species:
            label = f"{mon.nickname} ({mon.species})"
        print(f"  {i}. {label}")

    print(f"\n{Fore.YELLOW}Settings:{Style.RESET_ALL}")
    print(f"  Channel   : #{channel}")
    print(f"  Bot       : @{bot}")
    print(f"  Command   : {trade_command}")
    print(f"  Trade code: {trade_code}")


async def _run(cfg: Config, team_text: str) -> None:
    pokemon_list = parse_team(team_text)
    if not pokemon_list:
        print(f"{Fore.RED}No Pokemon found in the provided text. Exiting.{Style.RESET_ALL}")
        sys.exit(1)

    _print_team_summary(
        pokemon_list, cfg.trade_code, cfg.channel, cfg.bot_username, cfg.trade_command
    )

    answer = input(f"\n{Fore.CYAN}Start trading? (y/n): {Style.RESET_ALL}").strip().lower()
    if answer != "y":
        print("Aborted.")
        return

    client = TwitchClient(cfg)
    manager = TradeManager(cfg, client, ConsoleReporter())
    manager.register()

    await client.connect()

    # Run the IRC listener and the trade flow concurrently
    listen_task = asyncio.create_task(client.listen())
    try:
        await manager.run_team(pokemon_list)
    finally:
        listen_task.cancel()
        await asyncio.gather(listen_task, return_exceptions=True)
        await client.disconnect()


def main() -> None:
    print(BANNER)

    cfg = Config.from_env()
    errors = cfg.validate()
    if errors:
        print(
            f"{Fore.RED}Missing required config: {', '.join(errors)}\n"
            f"Set them as environment variables / in a .env file, or run the "
            f"desktop app (python -m berichan.gui) and use its setup wizard.{Style.RESET_ALL}"
        )
        sys.exit(1)

    # Accept optional CLI args
    trade_code_override: str | None = None
    team_file: str | None = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--code" and i + 1 < len(args):
            trade_code_override = args[i + 1]
            i += 2
        else:
            team_file = args[i]
            i += 1

    if trade_code_override:
        cfg.trade_code = trade_code_override

    game = prompt_game()
    cfg.trade_command = game.command

    if team_file:
        path = Path(team_file)
        if not path.exists():
            print(f"{Fore.RED}File not found: {team_file}{Style.RESET_ALL}")
            sys.exit(1)
        team_text = path.read_text(encoding="utf-8")
    else:
        team_text = _read_team_interactive()

    asyncio.run(_run(cfg, team_text))


if __name__ == "__main__":
    main()
