"""
Application configuration.

Config is the single source of truth for credentials, trade settings, timing
and the ready-sound preferences. It can be:

  - loaded from / saved to a JSON settings file (used by the GUI), and
  - migrated from a legacy .env file the first time the GUI runs.

The CLI still works via from_env(); the GUI uses load()/save().
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from dotenv import load_dotenv

from .paths import settings_file
from .secrets_store import protect, unprotect

load_dotenv()


@dataclass
class Config:
    # Twitch credentials
    oauth_token: str = ""       # "oauth:xxxxx" format for IRC
    access_token: str = ""      # raw token (no "oauth:" prefix) for Helix API
    client_id: str = ""
    username: str = ""          # Your Twitch username, lowercase

    # Target channel and bot
    channel: str = "berichandev"
    bot_username: str = "BerichanBot"

    # Trade settings
    trade_code: str = "24932000"
    trade_command: str = "!tradeSV"  # Berichan !trade* prefix for target game

    # Timing (seconds)
    line_send_delay: float = 0.6
    post_whisper_delay: float = 2.0
    inter_trade_delay: float = 120.0
    trade_timeout: float = 600.0

    # Ready-sound preferences (GUI). sound_path == "" means use the bundled
    # default chime; volume is 0.0–1.0.
    sound_enabled: bool = True
    sound_path: str = ""
    sound_volume: float = 0.5

    # Appearance: "windows" (native, default), "material", or "glass".
    theme: str = "windows"

    # Fields that live only in .env / runtime, never persisted to settings.json.
    _DERIVED = {"oauth_token", "access_token"}

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------

    def set_token(self, raw: str) -> None:
        """Accept a token with or without the 'oauth:' prefix and set both forms."""
        raw = raw.strip()
        self.oauth_token = raw if raw.startswith("oauth:") else f"oauth:{raw}"
        self.access_token = raw[len("oauth:"):] if raw.startswith("oauth:") else raw

    # ------------------------------------------------------------------
    # Legacy .env loading (CLI + first-run migration)
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "Config":
        cfg = cls(
            client_id=os.getenv("TWITCH_CLIENT_ID", ""),
            username=os.getenv("TWITCH_USERNAME", "").lower(),
            channel=os.getenv("TWITCH_CHANNEL", "berichandev").lower(),
            bot_username=os.getenv("BOT_USERNAME", "BerichanBot"),
            trade_code=os.getenv("TRADE_CODE", "24932000"),
            line_send_delay=float(os.getenv("LINE_SEND_DELAY", "0.6")),
            post_whisper_delay=float(os.getenv("POST_WHISPER_DELAY", "2.0")),
            inter_trade_delay=float(os.getenv("INTER_TRADE_DELAY", "120.0")),
            trade_timeout=float(os.getenv("TRADE_TIMEOUT", "600.0")),
        )
        cfg.set_token(os.getenv("TWITCH_OAUTH_TOKEN", ""))
        return cfg

    # ------------------------------------------------------------------
    # JSON settings (GUI)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serializable settings. The token is encrypted at rest (DPAPI)."""
        data = {k: v for k, v in asdict(self).items() if k not in self._DERIVED}
        data["token_enc"] = protect(self.oauth_token)  # never plaintext on disk
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        cfg = cls()
        known = {f.name for f in fields(cls)}
        for key, value in data.items():
            if key in known and key not in cls._DERIVED:
                setattr(cfg, key, value)
        cfg.username = (cfg.username or "").lower()
        cfg.channel = (cfg.channel or "").lower()
        # Prefer the encrypted form; fall back to a legacy plaintext "token" key
        # written by older builds (it gets re-encrypted on the next save()).
        if "token_enc" in data:
            cfg.set_token(unprotect(data["token_enc"]))
        else:
            cfg.set_token(data.get("token", ""))
        return cfg

    @classmethod
    def load(cls) -> "Config":
        """
        Load settings from the JSON file. On first run (no file yet) migrate
        from the legacy .env and write the JSON so the GUI owns it from then on.
        """
        path = settings_file()
        if path.exists():
            try:
                return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass  # corrupt/unreadable — fall through to env defaults
        cfg = cls.from_env()
        cfg.save()
        return cfg

    def save(self) -> None:
        path = settings_file()
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> list[str]:
        """Return a list of missing/invalid field names."""
        errors = []
        if not self.access_token:
            errors.append("TWITCH_OAUTH_TOKEN")
        if not self.client_id:
            errors.append("TWITCH_CLIENT_ID")
        if not self.username:
            errors.append("TWITCH_USERNAME")
        return errors
