"""Create README artwork from recorded controls and the actual console output."""

import json
import os
import re
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QApplication

P = Path(__file__).resolve().parents[1]
A = P / "assets"
OUT = P.parent / "assets"
INK = "#222b36"
BLUE = "#4f8ef7"
GROUND = "#eeede9"


def load(name):
    image = QImage(str(A / name))
    assert not image.isNull(), name
    return image


def font(size, family="Outfit", weight=QFont.Weight.Medium):
    value = QFont(family)
    value.setPixelSize(size)
    value.setWeight(weight)
    return value


def text(painter, value, x, y, size, color=INK, weight=QFont.Weight.Medium):
    painter.setFont(font(size, weight=weight))
    painter.setPen(QColor(color))
    painter.drawText(x, y, value)


def image(painter, value, x, y, width):
    painter.drawImage(
        QRectF(x, y, width, width * value.height() / value.width()), value
    )


def canvas(width, height, background=GROUND):
    value = QImage(width, height, QImage.Format.Format_RGB32)
    value.fill(QColor(background))
    painter = QPainter(value)
    painter.setRenderHints(
        QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
    )
    return value, painter


def banner():
    value, p = canvas(1800, 960)
    text(p, "Nudge", 100, 185, 140, weight=QFont.Weight.DemiBold)
    text(p, "Computer control for", 105, 305, 60)
    text(p, "limited dexterity", 105, 390, 60)
    image(p, load("browser/bank-page-idle.png"), 800, 55, 920)
    target = QPointF(800 + 107.5 * 920 / 1280, 55 + 258 * 920 / 1280)
    for offset, alpha, width in [(0, 160, 7), (12, 65, 4), (24, 30, 3)]:
        path = QPainterPath(QPointF(1510, 485 + offset))
        path.cubicTo(
            1350,
            590 + offset,
            1010,
            440 + offset,
            target.x(),
            target.y() + offset * 0.1,
        )
        p.setPen(
            QPen(
                QColor(79, 142, 247, alpha),
                width,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        )
        p.drawPath(path)
    p.setPen(QPen(QColor(BLUE), 3))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(target.x() - 34, target.y() - 34, 68, 68))
    image(p, load("pointer.png"), target.x() - 18, target.y() - 18, 142)
    image(p, load("browser/bank-idle.png"), 100, 570, 1600)
    p.end()
    assert value.save(str(OUT / "nudge-banner.png"))


def anatomy():
    value, p = canvas(1600, 940)
    bar = load("browser/bank-done.png")
    x, y, width = 220, 190, 1160
    image(p, bar, x, y, width)
    scale = width / bar.width()
    geometry = json.loads((A / "browser/bank-trace.json").read_text())["geometry"]

    def bottom(name):
        a, b, w, h = geometry[name]
        return QPointF(x + (a + w / 2) * scale, y + (b + h) * scale)

    callouts = [
        ("App", 570, 105, QPointF(x + 355 * scale, y + 45 * scale), QPointF(605, 124)),
        (
            "Debug mode",
            1260,
            160,
            QPointF(x + 1248 * scale, y + 36 * scale),
            QPointF(1370, 165),
        ),
        (
            "Step feed",
            30,
            360,
            QPointF(x + 40 * scale, y + 210 * scale),
            QPointF(182, 365),
        ),
        ("Goal", 630, 865, bottom("input"), QPointF(675, 825)),
        ("Speak", 95, 860, bottom("orb"), QPointF(210, 822)),
        ("Go / Stop", 1370, 830, bottom("go"), QPointF(1380, 790)),
    ]
    for label, lx, ly, point, start in callouts:
        text(p, label, lx, ly, 36, weight=QFont.Weight.DemiBold)
        p.setPen(QPen(QColor(BLUE), 2.5))
        p.drawLine(start, point)
        p.setBrush(QColor(BLUE))
        p.drawEllipse(QRectF(point.x() - 4, point.y() - 4, 8, 8))
    p.end()
    assert value.save(str(OUT / "nudge-interface.png"))


def terminal():
    raw = (A / "browser/bank-console.log").read_text()
    lines = [line for line in raw.splitlines() if not line.startswith("{")]
    value, p = canvas(1600, 130 + len(lines) * 42, "#11151c")
    text(p, "nudge / bank run", 55, 54, 27, "#aeb8c8")
    p.setPen(QPen(QColor("#29313d"), 1))
    p.drawLine(0, 82, 1600, 82)
    families = QFontDatabase.families()
    family = next(
        (
            name
            for name in ("Menlo", "Consolas", "DejaVu Sans Mono")
            if name in families
        ),
        "Monospace",
    )
    colors = {
        "32": "#8cdaa4",
        "35": "#cea3ff",
        "34": "#91b6ff",
        "90": "#8995a6",
        "37": "#dce4ef",
    }
    for index, line in enumerate(lines):
        x = 55
        baseline = 125 + index * 42
        color = "#dce4ef"
        weight = QFont.Weight.Normal
        for part in re.split("(" + re.escape(chr(27) + "[") + "[0-9;]*m)", line):
            if part.startswith("\x1b["):
                code = part[2:-1]
                if code == "0":
                    color = "#dce4ef"
                    weight = QFont.Weight.Normal
                elif code == "1":
                    weight = QFont.Weight.Bold
                elif code in colors:
                    color = colors[code]
                continue
            p.setFont(font(26, family, weight))
            p.setPen(QColor(color))
            p.drawText(x, baseline, part)
            x += p.fontMetrics().horizontalAdvance(part)
    p.end()
    assert value.save(str(OUT / "nudge-terminal.png"))


def main():
    _app = QApplication.instance() or QApplication([])
    assert QFontDatabase.addApplicationFont(str(A / "fonts/Outfit.ttf")) != -1
    OUT.mkdir(exist_ok=True)
    banner()
    anatomy()
    terminal()
    print("Created cursor banner, labelled interface and captured terminal output.")


if __name__ == "__main__":
    main()
