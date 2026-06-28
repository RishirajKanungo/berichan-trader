"""
GUI entry point. Sets up a single asyncio event loop that is driven by Qt
(via qasync) so the async Twitch/trade code and the widgets share one loop.

    python -m berichan.gui
"""

from __future__ import annotations

import asyncio
import sys

import qasync
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Berichan Auto Cross-Transfer")

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()
    window.on_shown()  # apply theme / first-run wizard after the native window exists

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
