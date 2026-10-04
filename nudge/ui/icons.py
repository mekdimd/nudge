from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QFileInfo, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPixmap, QRadialGradient
from PySide6.QtSvg import QSvgRenderer

from ..core.models import AppRef
from . import theme

ASSETS = Path(__file__).parent / "assets"
SVGS = {"jev": "typesafe", "gemini": "gemini", "vision": "eye"}
LETTERS = {"you": ("You", QColor("#2A2F3A"))}
APP_ICON_PX = 64
_cache: dict[tuple, QPixmap] = {}


def _ratio() -> float:
    screen = QGuiApplication.primaryScreen()
    return screen.devicePixelRatio() if screen is not None else 2.0


def _canvas(size: int) -> QPixmap:
    ratio = _ratio()
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap


def svg_pixmap(name: str, size: int) -> QPixmap:
    key = ("svg", name, size)
    if key not in _cache:
        pixmap = _canvas(size)
        renderer = QSvgRenderer(str(ASSETS / f"{name}.svg"))
        renderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        _cache[key] = pixmap
    return _cache[key]


def _letter(text: str, color: QColor, size: int) -> QPixmap:
    pixmap = _canvas(size)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawRoundedRect(QRectF(0, 0, size, size), size * 0.28, size * 0.28)
    painter.setPen(theme.TEXT)
    painter.setFont(theme.font(max(7, int(size * (0.42 if len(text) > 1 else 0.55))), QFont.Weight.Bold))
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, text)
    painter.end()
    return pixmap


def _dot(size: int) -> QPixmap:
    pixmap = _canvas(size)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QRadialGradient(size * 0.35, size * 0.3, size * 0.7)
    gradient.setColorAt(0.0, QColor("#D4E4FF"))
    gradient.setColorAt(0.45, QColor("#6AA0FF"))
    gradient.setColorAt(1.0, QColor("#2F3F8F"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    painter.drawEllipse(QRectF(1, 1, size - 2, size - 2))
    painter.end()
    return pixmap


def _mac_app_icon(pid: int) -> QPixmap | None:
    from AppKit import NSBitmapImageRep, NSDeviceRGBColorSpace, NSGraphicsContext, NSMakeRect, NSRunningApplication

    running = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    image = running.icon() if running is not None else None
    if image is None:
        return None
    # Draw into a small bitmap; encoding the full 1024 px icon takes a quarter second on the UI thread.
    rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, APP_ICON_PX, APP_ICON_PX, 8, 4, True, False, NSDeviceRGBColorSpace, 0, 0
    )
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep))
    image.drawInRect_(NSMakeRect(0, 0, APP_ICON_PX, APP_ICON_PX))
    NSGraphicsContext.restoreGraphicsState()
    png = rep.representationUsingType_properties_(4, {})  # NSBitmapImageFileTypePNG
    pixmap = QPixmap()
    return pixmap if png is not None and pixmap.loadFromData(bytes(png)) else None


def _windows_exe(pid: int) -> str | None:
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.windll.kernel32
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        buffer = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        return buffer.value if kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)) else None
    finally:
        kernel.CloseHandle(handle)


def _windows_app_icon(pid: int, size: int) -> QPixmap | None:
    from PySide6.QtWidgets import QFileIconProvider

    path = _windows_exe(pid)
    if not path:
        return None
    pixmap = QFileIconProvider().icon(QFileInfo(path)).pixmap(size)
    return None if pixmap.isNull() else pixmap


def _raw_app_icon(pid: int) -> QPixmap | None:
    key = ("raw", pid)
    if key not in _cache:
        try:
            if sys.platform == "darwin":
                raw = _mac_app_icon(pid)
            elif sys.platform == "win32":
                raw = _windows_app_icon(pid, APP_ICON_PX)
            else:
                raw = None
        except Exception:
            raw = None
        _cache[key] = raw if raw is not None and not raw.isNull() else QPixmap()
    return _cache[key] if not _cache[key].isNull() else None


def _app_icon(app: AppRef, size: int) -> QPixmap | None:
    raw = _raw_app_icon(app.pid)
    if raw is None:
        return None
    ratio = _ratio()
    scaled = raw.scaled(int(size * ratio), int(size * ratio), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    scaled.setDevicePixelRatio(ratio)
    return scaled


def actor_icon(actor: str, app: AppRef | None = None, size: int = 18) -> QPixmap:
    """The small avatar shown next to a timeline entry. Never null: unknown things get a letter."""
    key = (actor, app.pid if actor == "app" and app else None, size)
    if key in _cache:
        return _cache[key]
    if actor in SVGS:
        pixmap = svg_pixmap(SVGS[actor], size)
    elif actor == "nudge":
        pixmap = _dot(size)
    elif actor == "app":
        pixmap = (_app_icon(app, size) if app else None) or _letter((app.name[:1] if app else "?").upper(), QColor("#34405A"), size)
    else:
        text, color = LETTERS.get(actor, (actor[:1].upper(), QColor("#2A2F3A")))
        pixmap = _letter(text, color, size)
    _cache[key] = pixmap
    return pixmap
