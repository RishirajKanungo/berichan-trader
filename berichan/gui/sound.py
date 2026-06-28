"""
Ready-alert sound playback for the GUI.

Uses QMediaPlayer + QAudioOutput so any .wav or .mp3 works and volume is
adjustable (0.0–1.0). Three soft built-in chimes ship with the app to replace
the original harsh triple beep; users can also point at their own file.

A stored sound preference is one of:
  ""                 -> the default built-in (soft chime)
  "builtin:<file>"   -> a bundled sound under assets/sounds/
  "<absolute path>"  -> a user-supplied file
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from ..paths import resource_path

# Display name -> bundled filename. Order defines the dropdown order.
BUILTIN_SOUNDS: dict[str, str] = {
    "Soft Chime": "soft_chime.wav",
    "Gentle Bell": "gentle_bell.wav",
    "Marimba Pop": "marimba_pop.wav",
}

DEFAULT_BUILTIN = "soft_chime.wav"
_BUILTIN_PREFIX = "builtin:"


def builtin_path(filename: str) -> Path:
    return resource_path("assets", "sounds", filename)


def resolve_sound_path(stored: str) -> Path:
    """Turn a stored preference into a concrete file path."""
    if not stored:
        return builtin_path(DEFAULT_BUILTIN)
    if stored.startswith(_BUILTIN_PREFIX):
        return builtin_path(stored[len(_BUILTIN_PREFIX):])
    return Path(stored)


def builtin_token(filename: str) -> str:
    return f"{_BUILTIN_PREFIX}{filename}"


class SoundManager:
    """Plays the configured ready sound at the configured volume."""

    def __init__(self) -> None:
        self._output = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._output)

    def play(self, stored_path: str, volume: float, enabled: bool = True) -> None:
        if not enabled:
            return
        path = resolve_sound_path(stored_path)
        if not path.exists():
            # Fall back to the default chime rather than failing silently-wrong.
            path = builtin_path(DEFAULT_BUILTIN)
        self._output.setVolume(max(0.0, min(1.0, float(volume))))
        self._player.setSource(QUrl.fromLocalFile(str(path)))
        self._player.play()
