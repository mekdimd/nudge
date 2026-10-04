from __future__ import annotations

from typing import Callable

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .bar import HOTKEY
from .icons import actor_icon


class Tray(QSystemTrayIcon):
    """The menu bar (or notification area) icon that keeps a hidden Nudge reachable."""

    def __init__(self, show: Callable[[], None], quit: Callable[[], None]):
        super().__init__(QIcon(actor_icon("nudge", size=18)))
        self.setToolTip(f"Nudge · {HOTKEY} to open")
        menu = QMenu()
        opened = QAction(f"Show Nudge ({HOTKEY})", menu)
        opened.triggered.connect(show)
        menu.addAction(opened)
        menu.addSeparator()
        leave = QAction("Quit Nudge", menu)
        leave.triggered.connect(quit)
        menu.addAction(leave)
        self._menu = menu
        self.setContextMenu(menu)
        self.activated.connect(lambda reason: show() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.show()

    @staticmethod
    def available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()
