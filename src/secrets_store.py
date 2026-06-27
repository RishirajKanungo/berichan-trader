"""
At-rest encryption for the Twitch OAuth token using the Windows Data
Protection API (DPAPI), reached through stdlib ctypes — no third-party
dependency.

DPAPI ties the ciphertext to the current Windows user account, so a copied or
leaked settings.json cannot be decrypted on another machine / by another user.

  protect(plaintext)  -> base64 ciphertext (or "plain:<text>" fallback)
  unprotect(stored)   -> plaintext

On non-Windows or if DPAPI fails, we fall back to a clearly-marked, un-encrypted
form so the app still works; is_encrypted() lets the UI warn in that case.
"""

from __future__ import annotations

import base64
import ctypes
import sys
from ctypes import wintypes

_PLAIN_PREFIX = "plain:"
_ENC_PREFIX = "dpapi:"

_IS_WINDOWS = sys.platform == "win32"

# Entropy mixed into the DPAPI blob — a fixed app salt (not a secret; just
# ties blobs to this app so unrelated DPAPI data can't be cross-read).
_ENTROPY = b"BerichanCrossTransfer/v1"


if _IS_WINDOWS:

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def _blob(data: bytes) -> _DATA_BLOB:
        buf = ctypes.create_string_buffer(data, len(data))
        return _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))

    def _blob_bytes(blob: _DATA_BLOB) -> bytes:
        return ctypes.string_at(blob.pbData, blob.cbData)

    _crypt32 = ctypes.windll.crypt32
    _kernel32 = ctypes.windll.kernel32

    def _dpapi(func, data: bytes) -> bytes:
        in_blob = _blob(data)
        ent_blob = _blob(_ENTROPY)
        out_blob = _DATA_BLOB()
        ok = func(
            ctypes.byref(in_blob),
            None,
            ctypes.byref(ent_blob),
            None,
            None,
            0,  # CRYPTPROTECT flags: 0 = per-user
            ctypes.byref(out_blob),
        )
        if not ok:
            raise OSError("DPAPI call failed")
        try:
            return _blob_bytes(out_blob)
        finally:
            _kernel32.LocalFree(out_blob.pbData)


def protect(plaintext: str) -> str:
    """Encrypt a token for storage. Returns a tagged, JSON-safe string."""
    if not plaintext:
        return ""
    if _IS_WINDOWS:
        try:
            enc = _dpapi(_crypt32.CryptProtectData, plaintext.encode("utf-8"))
            return _ENC_PREFIX + base64.b64encode(enc).decode("ascii")
        except OSError:
            pass
    return _PLAIN_PREFIX + plaintext


def unprotect(stored: str) -> str:
    """Decrypt a value produced by protect() (or an older raw/plaintext value)."""
    if not stored:
        return ""
    if stored.startswith(_ENC_PREFIX):
        if not _IS_WINDOWS:
            return ""  # can't decrypt a DPAPI blob off Windows
        raw = base64.b64decode(stored[len(_ENC_PREFIX):])
        try:
            return _dpapi(_crypt32.CryptUnprotectData, raw).decode("utf-8")
        except OSError:
            return ""
    if stored.startswith(_PLAIN_PREFIX):
        return stored[len(_PLAIN_PREFIX):]
    # Legacy: a bare token written before encryption existed.
    return stored


def is_encrypted(stored: str) -> bool:
    return stored.startswith(_ENC_PREFIX)
