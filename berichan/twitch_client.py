"""
Async Twitch client combining:
  - IRC (chat read/write, PING/PONG keepalive)
  - Helix REST API (whispers, user-ID lookup)

Each Pokemon is sent as one PRIVMSG (space-joined Showdown set).
Whispers go through the Helix
API because Twitch deprecated IRC-based whispers for non-verified bots.
"""

from __future__ import annotations

import asyncio
import re
import ssl
from typing import Awaitable, Callable

import aiohttp
from colorama import Fore, Style, init as _colorama_init
_colorama_init()

MessageHandler = Callable[[str, str, str], Awaitable[None]]

_IRC_HOST = "irc.chat.twitch.tv"
_IRC_PORT = 6697  # SSL
_HELIX_BASE = "https://api.twitch.tv/helix"


class TwitchClient:
    def __init__(self, config) -> None:
        self._cfg = config
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._send_lock = asyncio.Lock()
        self._handlers: list[MessageHandler] = []
        self._user_id: str | None = None
        self._bot_user_id: str | None = None
        self._http: aiohttp.ClientSession | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_message_handler(self, handler: MessageHandler) -> None:
        self._handlers.append(handler)

    async def connect(self) -> None:
        """Open IRC connection, authenticate, join channel, fetch user IDs."""
        ssl_ctx = ssl.create_default_context()
        self._reader, self._writer = await asyncio.open_connection(
            _IRC_HOST, _IRC_PORT, ssl=ssl_ctx
        )
        self._http = aiohttp.ClientSession()

        await self._send_raw(f"PASS {self._cfg.oauth_token}")
        await self._send_raw(f"NICK {self._cfg.username}")
        # Request tags + commands so we get proper message parsing
        await self._send_raw("CAP REQ :twitch.tv/tags twitch.tv/commands")
        await self._send_raw(f"JOIN #{self._cfg.channel}")

        print(f"{Fore.GREEN}[IRC] Connected to #{self._cfg.channel}{Style.RESET_ALL}")

        await self._resolve_user_ids()

    async def disconnect(self) -> None:
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        if self._http:
            await self._http.close()

    async def send_chat(self, message: str) -> None:
        """Send one line to the channel."""
        async with self._send_lock:
            await self._send_raw(f"PRIVMSG #{self._cfg.channel} :{message}")
        print(f"{Fore.CYAN}  → chat: {message}{Style.RESET_ALL}")

    async def send_whisper(self, message: str) -> bool:
        """
        Send a whisper to the bot via Helix API.
        Returns True on success.
        Requires: TWITCH_CLIENT_ID and TWITCH_OAUTH_TOKEN with user:manage:whispers.
        """
        if not (self._user_id and self._bot_user_id):
            print(
                f"{Fore.RED}[WHISPER] Cannot whisper — missing user IDs. "
                f"Check TWITCH_CLIENT_ID and token scopes.{Style.RESET_ALL}"
            )
            return False

        url = (
            f"{_HELIX_BASE}/whispers"
            f"?from_user_id={self._user_id}&to_user_id={self._bot_user_id}"
        )
        headers = self._helix_headers()
        try:
            async with self._http.post(
                url, headers=headers, json={"message": message}, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 204:
                    print(
                        f"{Fore.GREEN}[WHISPER] Sent trade code '{message}' "
                        f"→ @{self._cfg.bot_username}{Style.RESET_ALL}"
                    )
                    return True
                body = await resp.text()
                print(f"{Fore.RED}[WHISPER] {resp.status}: {body}{Style.RESET_ALL}")
                return False
        except Exception as exc:
            print(f"{Fore.RED}[WHISPER] Error: {exc}{Style.RESET_ALL}")
            return False

    async def listen(self) -> None:
        """Run forever reading IRC lines. Call this as a background task."""
        buf = ""
        while True:
            try:
                data = await self._reader.read(4096)
                if not data:
                    print(f"{Fore.RED}[IRC] Connection closed by server.{Style.RESET_ALL}")
                    break
                buf += data.decode("utf-8", errors="ignore")
                while "\r\n" in buf:
                    line, buf = buf.split("\r\n", 1)
                    await self._dispatch(line)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                print(f"{Fore.RED}[IRC] Read error: {exc}{Style.RESET_ALL}")
                break

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _send_raw(self, line: str) -> None:
        self._writer.write(f"{line}\r\n".encode())
        await self._writer.drain()

    async def _dispatch(self, line: str) -> None:
        if line.startswith("PING"):
            pong = line.replace("PING", "PONG", 1)
            await self._send_raw(pong)
            return

        # Strip IRCv3 tags (@key=val;...) from the front
        stripped = re.sub(r"^@\S+\s+", "", line)

        # :sender!user@host.tmi.twitch.tv PRIVMSG #channel :text
        m = re.match(
            r":(\w+)!\w+@[\w.]+\.tmi\.twitch\.tv PRIVMSG #(\w+) :(.+)", stripped
        )
        if m:
            sender, channel, text = m.group(1), m.group(2), m.group(3)
            for handler in self._handlers:
                await handler(sender, channel, text)

    def _helix_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._cfg.access_token}",
            "Client-Id": self._cfg.client_id,
            "Content-Type": "application/json",
        }

    async def _resolve_user_ids(self) -> None:
        """Fetch Twitch user IDs for self and the bot via Helix /users."""
        if not (self._cfg.client_id and self._cfg.access_token):
            print(f"{Fore.YELLOW}[WARN] No client_id/token — whispers disabled.{Style.RESET_ALL}")
            return

        url = (
            f"{_HELIX_BASE}/users"
            f"?login={self._cfg.username}&login={self._cfg.bot_username.lower()}"
        )
        try:
            async with self._http.get(
                url,
                headers=self._helix_headers(),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = (await resp.json()).get("data", [])
        except Exception as exc:
            print(f"{Fore.YELLOW}[WARN] Could not fetch user IDs: {exc}{Style.RESET_ALL}")
            return

        for user in data:
            login = user["login"].lower()
            if login == self._cfg.username:
                self._user_id = user["id"]
            elif login == self._cfg.bot_username.lower():
                self._bot_user_id = user["id"]

        if self._user_id and self._bot_user_id:
            print(
                f"{Fore.GREEN}[HELIX] user_id={self._user_id}, "
                f"bot_id={self._bot_user_id}{Style.RESET_ALL}"
            )
        else:
            missing = []
            if not self._user_id:
                missing.append(self._cfg.username)
            if not self._bot_user_id:
                missing.append(self._cfg.bot_username)
            print(
                f"{Fore.YELLOW}[WARN] Could not resolve IDs for: {', '.join(missing)}. "
                f"Whispers may fail.{Style.RESET_ALL}"
            )
