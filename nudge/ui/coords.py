from __future__ import annotations

from PySide6.QtCore import QPoint
from PySide6.QtGui import QGuiApplication


def physical_to_logical(x: float, y: float, w: float, h: float) -> tuple[float, float, float, float]:
    """Windows UIA reports physical pixels; Qt draws in logical pixels."""
    screen = QGuiApplication.primaryScreen()
    for candidate in QGuiApplication.screens():
        g = candidate.geometry()
        ratio = candidate.devicePixelRatio()
        px, py = g.x() * ratio, g.y() * ratio
        if px <= x < px + g.width() * ratio and py <= y < py + g.height() * ratio:
            screen = candidate
            break
    g = screen.geometry()
    ratio = screen.devicePixelRatio() or 1.0
    ox, oy = g.x() * ratio, g.y() * ratio
    return (g.x() + (x - ox) / ratio, g.y() + (y - oy) / ratio, w / ratio, h / ratio)


def logical_to_physical(x: float, y: float, w: float, h: float) -> tuple[float, float, float, float]:
    """For screenshots on Windows, where capture APIs take physical pixels."""
    screen = QGuiApplication.screenAt(QPoint(int(x + w / 2), int(y + h / 2))) or QGuiApplication.primaryScreen()
    g = screen.geometry()
    ratio = screen.devicePixelRatio() or 1.0
    return (g.x() * ratio + (x - g.x()) * ratio, g.y() * ratio + (y - g.y()) * ratio, w * ratio, h * ratio)
