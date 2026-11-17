"""Build desktop app examples and control recognition graphics from saved assets."""

import argparse
import os
import sys
from pathlib import Path

from build_artwork import BLUE, OUT, A, canvas, font, image, load, text
from build_recognition_artwork import main as recognition_artwork
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QImage,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

DESKTOP = A / "desktop"
APPS = {
    "Finder": "/System/Library/CoreServices/Finder.app",
    "Safari": "/Applications/Safari.app",
    "Mail": "/System/Applications/Mail.app",
    "Notes": "/System/Applications/Notes.app",
    "Calendar": "/System/Applications/Calendar.app",
}


def refresh_sources():
    """Read local macOS icons and render the real bar."""
    from AppKit import NSBitmapImageRep, NSMakeSize, NSPNGFileType, NSWorkspace
    from PySide6.QtGui import QPixmap

    from nudge.core.models import AppRef
    from nudge.ui.bar import Bar
    from nudge.ui.timeline import Timeline

    workspace = NSWorkspace.sharedWorkspace()
    for name, path in APPS.items():
        assert Path(path).is_dir(), path
        icon = workspace.iconForFile_(str(Path(path).resolve()))
        icon.setSize_(NSMakeSize(256, 256))
        bitmap = NSBitmapImageRep.imageRepWithData_(icon.TIFFRepresentation())
        data = bitmap.representationUsingType_properties_(NSPNGFileType, {})
        png = QImage.fromData(bytes(data), "PNG").scaled(
            256,
            256,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        assert png.save(str(DESKTOP / f"{name.lower()}.png"))

    bar = Bar(Timeline())
    bar.set_target(AppRef("Finder", 999999))
    ratio = bar.devicePixelRatioF()
    icon = QPixmap(str(DESKTOP / "finder.png")).scaled(
        int(16 * ratio),
        int(16 * ratio),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    icon.setDevicePixelRatio(ratio)
    bar.target.icon.setPixmap(icon)
    bar.input.setText("open Notes from the Dock")
    bar.set_status("")
    bar.adjustSize()
    QApplication.processEvents()
    assert bar.grab().save(str(DESKTOP / "dock-bar.png"))
    bar.close()

    print("Saved macOS icons and the offscreen Nudge bar.")


def dock():
    value, p = canvas(1600, 1050)
    text(p, "Open apps from the Dock", 64, 96, 58, weight=QFont.Weight.DemiBold)
    text(p, "Ask Nudge to open Notes.", 64, 153, 34)
    p.setFont(font(28))
    p.setPen(QColor("#525b69"))
    p.drawText(QRectF(1240, 72, 296, 40), Qt.AlignmentFlag.AlignRight, "Mockup")

    desktop = QRectF(48, 204, 1504, 798)
    p.setPen(QPen(QColor("#3a4556"), 2))
    p.setBrush(QColor("#222d3e"))
    p.drawRoundedRect(desktop, 24, 24)
    bar = load("desktop/dock-bar.png")
    image(p, bar, 165, 318, 1270)

    shelf = QRectF(375, 787, 850, 172)
    p.setBrush(QColor("#424d60"))
    p.setPen(QPen(QColor("#697386"), 2))
    p.drawRoundedRect(shelf, 34, 34)
    for index, name in enumerate(APPS):
        image(p, load(f"desktop/{name.lower()}.png"), 411 + index * 160, 811, 130)

    target = QPointF(956, 869)
    path = QPainterPath(QPointF(1315, 318 + 1270 * bar.height() / bar.width() + 10))
    path.cubicTo(1304, 741, 1080, 698, target.x(), target.y())
    for width, alpha in [(13, 25), (5, 130)]:
        pen = QPen(QColor(79, 142, 247, alpha), width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
    p.setPen(QPen(QColor(BLUE), 3))
    p.drawRoundedRect(QRectF(883, 797, 150, 153), 26, 26)
    image(p, load("pointer.png"), target.x() - 12, target.y() - 12, 112)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#f2f4f8"))
    p.drawRoundedRect(QRectF(906, 727, 104, 49), 12, 12)
    p.setPen(QColor("#222b36"))
    p.setFont(font(28))
    p.drawText(QRectF(906, 727, 104, 49), Qt.AlignmentFlag.AlignCenter, "Notes")
    p.end()
    assert value.save(str(OUT / "nudge-dock.png"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-sources",
        action="store_true",
        help="Read macOS app icons and render Nudge's bar offscreen.",
    )
    args = parser.parse_args()
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication([])
    assert QFontDatabase.addApplicationFont(str(A / "fonts/Outfit.ttf")) != -1
    DESKTOP.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    if args.refresh_sources:
        assert sys.platform == "darwin", "Refreshing sources requires macOS"
        refresh_sources()
    dock()
    recognition_artwork()
    app.processEvents()
    print("Created the Dock mockup and control recognition graphics.")


if __name__ == "__main__":
    main()
