from __future__ import annotations

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
