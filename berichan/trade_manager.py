"""
Orchestrates the full trade flow for each Pokemon in the team:

  1. Send the full Showdown set as one chat message (space-joined, one PRIVMSG).
  2. Wait briefly, then whisper the trade code to BerichanBot.
  3. Wait for chat confirmation: "Added to the LinkTrade queue, unique ID: …"
  4. Wait for trade start: "Initializing trade (POKEMON) with you."
  5. Alert the user to begin trading on the Switch (via the reporter).
  6. Wait for the user to confirm the trade is done (reporter.wait_for_trade_done).
  7. Observe the configured cooldown before submitting the next Pokemon.

All user-facing output and interaction goes through a TradeReporter, so the
same flow drives either the terminal or the GUI.

Bot message patterns (from berichandev Twitch chat, based on observed behavior):
  Queue join  → contains username + "Added to the LinkTrade queue"
  Trade start → contains username + "Initializing trade"
"""

from __future__ import annotations

import asyncio
import re

from .games import format_trade_message
from .reporter import TradeReporter
from .team_parser import Pokemon, TWITCH_MAX_CHAT_LENGTH
from .twitch_client import TwitchClient
from .config import Config


class TradeManager:
    def __init__(
        self,
        cfg: "Config",
        client: "TwitchClient",
        reporter: TradeReporter | None = None,
    ) -> None:
        self._cfg = cfg
        self._client = client
        self._reporter = reporter or TradeReporter()
        self._queue_event = asyncio.Event()
        self._trade_event = asyncio.Event()
        self._queue_id: str = "?"
        self._queue_position: str = "?"
        self._trade_pokemon: str = "?"

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def register(self) -> None:
        """Register the IRC message handler. Call once after connect."""
        self._client.add_message_handler(self._on_message)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_team(self, pokemon_list: list["Pokemon"]) -> None:
        """Trade every Pokemon in the list sequentially."""
        total = len(pokemon_list)
        for idx, mon in enumerate(pokemon_list, start=1):
            self._reporter.pokemon_start(idx, total, mon.nickname, mon.species)
            await self._trade_one(mon)
            self._reporter.pokemon_done(idx, total)

            if idx < total:
                await self._cooldown(self._cfg.inter_trade_delay)

        self._reporter.team_complete(total)

    # ------------------------------------------------------------------
    # Per-Pokemon trade flow
    # ------------------------------------------------------------------

    async def _trade_one(self, mon: "Pokemon") -> None:
        self._queue_event.clear()
        self._trade_event.clear()

        # Step 1 — post entire Showdown set as one chat message with !trade* prefix
        message = format_trade_message(self._cfg.trade_command, mon.chat_message)
        if len(message) > TWITCH_MAX_CHAT_LENGTH:
            self._reporter.log(
                f"[ERROR] Set for {mon.nickname} is {len(message)} chars "
                f"(Twitch limit {TWITCH_MAX_CHAT_LENGTH}). Shorten nicknames/moves "
                f"or remove optional fields.",
                level="error",
            )
            return

        self._reporter.set_status(f"Posting {mon.nickname} to chat…")
        self._reporter.log("Posting to chat…")
        await self._client.send_chat(message)
        await asyncio.sleep(self._cfg.line_send_delay)

        # Step 2 — whisper trade code
        await asyncio.sleep(self._cfg.post_whisper_delay)
        await self._client.send_whisper(self._cfg.trade_code)

        # Step 3 — wait for queue join confirmation
        self._reporter.set_status("Waiting for queue confirmation…")
        self._reporter.log("Waiting for queue confirmation…")
        try:
            await asyncio.wait_for(self._queue_event.wait(), timeout=30.0)
            self._reporter.log(f"[QUEUE] Joined! ID={self._queue_id}", level="success")
        except asyncio.TimeoutError:
            self._reporter.log(
                "[TIMEOUT] No queue confirmation in 30s. Is the bot active? "
                "Continuing to wait for trade start anyway…",
                level="warn",
            )

        # Step 4 — wait for "Initializing trade"
        self._reporter.set_status("Waiting for trade to start…")
        self._reporter.log("Waiting for trade to be initialized (may take a while)…")
        try:
            await asyncio.wait_for(
                self._trade_event.wait(), timeout=self._cfg.trade_timeout
            )
        except asyncio.TimeoutError:
            self._reporter.log(
                f"[TIMEOUT] Trade never started after "
                f"{self._cfg.trade_timeout:.0f}s. Skipping this Pokemon.",
                level="error",
            )
            return

        # Step 5 — alert user
        self._reporter.set_status(f"TRADE READY: {self._trade_pokemon}")
        self._reporter.trade_ready(self._trade_pokemon, self._cfg.trade_code)

        # Step 6 — wait for the user to complete the trade on the Switch
        await self._reporter.wait_for_trade_done()
        self._reporter.set_status("Trade confirmed.")

    async def _cooldown(self, total: float) -> None:
        """Sleep for `total` seconds, ticking the reporter once per second."""
        self._reporter.set_status("Cooldown before next Pokemon…")
        remaining = total
        while remaining > 0:
            self._reporter.cooldown_tick(remaining, total)
            step = min(1.0, remaining)
            await asyncio.sleep(step)
            remaining -= step
        self._reporter.cooldown_tick(0.0, total)

    # ------------------------------------------------------------------
    # IRC message handler
    # ------------------------------------------------------------------

    async def _on_message(self, sender: str, channel: str, text: str) -> None:
        username = self._cfg.username.lower()
        lower = text.lower()

        # Queue join: "@kaastre: Added to the LinkTrade queue, unique ID: 1245. Current Position: 3"
        if username in lower and "added to the linktrade queue" in lower:
            m = re.search(r"unique id[:\s]+(\d+)", text, re.IGNORECASE)
            self._queue_id = m.group(1) if m else "?"
            pos_m = re.search(r"current position[:\s]+(\d+)", text, re.IGNORECASE)
            self._queue_position = pos_m.group(1) if pos_m else "?"
            self._reporter.queue_joined(self._queue_id, self._queue_position)
            self._queue_event.set()

        # Trade start: "@kaastre (ID: 1245): Initializing trade (PENATRATOR) with you."
        if username in lower and "initializing trade" in lower:
            m = re.search(r"initializing trade\s*\(([^)]+)\)", text, re.IGNORECASE)
            self._trade_pokemon = m.group(1) if m else "?"
            self._trade_event.set()
