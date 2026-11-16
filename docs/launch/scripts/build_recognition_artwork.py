"""Build accessibility, local vision and Jev explanations from saved inputs."""

import json

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication

from build_artwork import A, OUT, canvas, font, image, load, text

DESKTOP = A / "desktop"
BG = "#181b20"
INK = "#f3f4f6"
MUTED = "#d3d9e2"
BLUE = "#609eff"
ORANGE = "#ffaf40"
MINT = "#8ce0b7"


def panel(painter, rect, fill="#20262e", stroke="#444d5b", width=1.5):
    painter.setPen(QPen(QColor(stroke), width))
    painter.setBrush(QColor(fill))
    painter.drawRoundedRect(rect, 14, 14)


def photo(painter, screen, rect):
    panel(painter, rect, "#1e1e1e", "#505866", 2)
    painter.save()
    clip = QPainterPath()
    clip.addRoundedRect(rect, 12, 12)
    painter.setClipPath(clip)
    painter.drawImage(rect, screen)
    painter.restore()


def recognition(title, subtitle, command, screen, filename, color, legends, note):
    value, p = canvas(1600, 1290, BG)
    text(p, title, 60, 120, 86, INK, QFont.Weight.DemiBold)
    assert p.fontMetrics().horizontalAdvance(title) <= 1480
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawRoundedRect(QRectF(62, 164, 38, 38), 7, 7)
    text(p, subtitle, 121, 200, 47, MUTED, QFont.Weight.Normal)
    assert p.fontMetrics().horizontalAdvance(subtitle) <= 1419
    families = QFontDatabase.families()
    mono = next(
        (name for name in ("Menlo", "Consolas", "DejaVu Sans Mono") if name in families),
        QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family(),
    )
    p.setFont(font(35, mono))
    command_box = QRectF(60, 236, p.fontMetrics().horizontalAdvance(command) + 48, 67)
    panel(p, command_box, "#242a32", "#414853")
    p.setPen(QColor(INK))
    p.drawText(command_box, Qt.AlignmentFlag.AlignCenter, command)
    x = command_box.right() + 38
    for swatch, label in legends:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(swatch))
        p.drawRoundedRect(QRectF(x, 257, 20, 20), 4, 4)
        text(p, label, x + 38, 280, 31, MUTED)
        x += 38 + p.fontMetrics().horizontalAdvance(label) + 32
    assert x - 32 <= 1540, "Legend exceeds the image width"
    photo(p, screen, QRectF(52, 344, 1496, 842))
    text(p, note, 60, 1246, 27, "#aeb7c5")
    p.end()
    assert value.save(str(OUT / filename))


def accessibility():
    recognition(
        "Nudge reads sites and apps.",
        "Blue boxes mark UI elements found through accessibility APIs.",
        "uv run nudge",
        load("desktop/vscode-accessibility.png"),
        "nudge-accessibility.png",
        BLUE,
        [(BLUE, "Accessibility")],
        "VS Code issue tracker. Every recorded control is outlined.",
    )


def figma():
    reference = load("desktop/figma-controls-reference.png").scaled(
        1440, 810, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
    )
    toolbar = reference.copy(775, 54, 665, 72).scaled(
        447, 48, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
    )
    sidebar = reference.copy(775, 126, 360, 684).scaled(
        241, 458, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
    )
    screens = load("desktop/figma-canvas.png").copy(205, 78, 869, 616)
    screen = QImage(1280, 720, QImage.Format.Format_RGB32)
    screen.fill(QColor("#1e1e1e"))
    p = QPainter(screen)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
    p.fillRect(QRectF(0, 0, 1280, 48), QColor("#2c2c2c"))
    p.fillRect(QRectF(0, 48, 241, 672), QColor("#2c2c2c"))
    p.drawImage(0, 0, toolbar)
    p.drawImage(0, 48, sidebar)
    p.drawImage(326, 76, screens)
    # These outlines illustrate the captured toolbar and layer controls.
    chrome = [
        (5, 7, 42, 34), (50, 6, 47, 35), (101, 6, 46, 35), (151, 6, 44, 35),
        (198, 6, 48, 35), (249, 6, 43, 35), (294, 6, 43, 35), (341, 6, 40, 35),
        (8, 52, 58, 28), (69, 52, 59, 28), (152, 52, 78, 28),
        (12, 100, 61, 28), (205, 100, 24, 28),
        (10, 132, 219, 27), (10, 164, 219, 27), (10, 196, 219, 27),
        (10, 228, 219, 27), (10, 277, 219, 27), (10, 309, 219, 27),
        (10, 341, 219, 27), (10, 373, 219, 27), (10, 405, 219, 27),
        (10, 437, 219, 27), (10, 469, 219, 27),
    ]
    for x, y, w, h in chrome:
        p.setPen(QPen(QColor(BLUE), 1.8))
        fill = QColor(BLUE)
        fill.setAlpha(14)
        p.setBrush(fill)
        p.drawRect(QRectF(x, y, w, h))
    data = json.loads((DESKTOP / "figma-detections.json").read_text())
    assert data["image_size"] == [1280, 720]
    regions = data["labelled"] + [{"box": box} for box in data["unnamed"]]
    count = 0
    for region in regions:
        x1, y1, x2, y2 = region["box"]
        if y2 < 52 or x2 - x1 < 5 or y2 - y1 < 5:
            continue
        x1, x2 = x1 + 121, x2 + 121
        y1, y2 = y1 - 2, y2 - 2
        assert 241 <= x1 < x2 <= 1280 and 48 <= y1 < y2 <= 720
        p.setPen(QPen(QColor(ORANGE), 2.2))
        fill = QColor(ORANGE)
        fill.setAlpha(22)
        p.setBrush(fill)
        p.drawRect(QRectF(x1 - 2, y1 - 2, x2 - x1 + 4, y2 - y1 + 4))
        count += 1
    assert count == 38, "Missing saved text or icon detections"
    text(p, "Figma / Travel app UI design", 496, 29, 18, MUTED)
    p.end()
    return screen


def vision():
    recognition(
        "Local OCR and icon detection",
        "Orange boxes mark UI elements found by local vision as a fallback.",
        "uv run --extra vision nudge",
        figma(),
        "nudge-vision.png",
        ORANGE,
        [(BLUE, "Accessibility"), (ORANGE, "Local vision")],
        "Figma editor mockup. Orange detections come from local OCR and icon detection.",
    )


def jev():
    data = json.loads((DESKTOP / "jev-example.json").read_text())
    ranked = data["ranked"]
    assert ranked[0]["id"] == data["choice"].split(":", 1)[1]
    assert abs(sum(row["probability"] for row in ranked) - 1) < 0.0001
    source = load("desktop/vscode-accessibility.png")
    value, p = canvas(1600, 1100, BG)
    text(p, "Jev chooses the next action", 60, 115, 84, INK, QFont.Weight.DemiBold)
    text(p, "Jev model scores labelled items against your goal.",
         62, 193, 46, MUTED, QFont.Weight.Normal)
    panel(p, QRectF(60, 230, 1480, 68), "#242a32")
    text(p, "Your goal", 82, 273, 31, MUTED)
    text(p, data["goal"], 248, 275, 36, INK, QFont.Weight.DemiBold)
    assert p.fontMetrics().horizontalAdvance(data["goal"]) <= 1270
    photo(p, source.copy(0, 168, 760, 552), QRectF(60, 338, 824, 598))
    ys = {"capture-27": 384, "capture-28": 416, "capture-29": 448, "capture-30": 480}
    winner = ranked[0]
    scale = 824 / 760
    selected = QRectF(60 + 16 * scale, 338 + (ys[winner["id"]] - 168) * scale,
                      223 * scale, 34 * scale)
    p.setPen(QPen(QColor(BLUE), 4))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(selected, 5, 5)
    image(p, load("pointer.png"), selected.right() - 28, selected.bottom() - 3, 66)
    x, y, w = 966, 387, 528
    text(p, "Example probabilities", x, y, 38, INK, QFont.Weight.DemiBold)
    for i, row in enumerate(ranked):
        yy = y + 34 + i * 105
        win = i == 0
        if win:
            panel(p, QRectF(x - 16, yy - 4, w + 32, 95), "#23362e", MINT, 2)
        text(p, row["label"], x + 5, yy + 35, 36, INK if win else MUTED,
             QFont.Weight.DemiBold if win else QFont.Weight.Medium)
        p.setFont(font(39, weight=QFont.Weight.DemiBold))
        p.setPen(QColor(MINT))
        p.drawText(QRectF(x + w - 160, yy - 2, 150, 48),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   f"{row['probability'] * 100:.0f}%")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(MINT if win else "#65a98a"))
        p.drawRoundedRect(QRectF(x + 5, yy + 57, (w - 10) * row["probability"], 9), 4, 4)
    chosen = QRectF(951, 871, 563, 65)
    panel(p, chosen, "#23362e", MINT)
    p.setFont(font(34, weight=QFont.Weight.DemiBold))
    p.setPen(QColor(INK))
    p.drawText(chosen, Qt.AlignmentFlag.AlignCenter, f"Selected: {winner['label']}")
    start = QPointF(selected.right() + 10, selected.center().y())
    end = QPointF(942, 459)
    curve = QPainterPath(start)
    curve.cubicTo(start.x() + 160, start.y(), end.x() - 160, end.y(), end.x(), end.y())
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(BLUE), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawPath(curve)
    text(p, "Jev selects the item with the highest score.", 60, 1057, 29, MUTED)
    p.end()
    assert value.save(str(OUT / "nudge-jev.png"))


def main():
    app = QApplication.instance() or QApplication([])
    assert QFontDatabase.addApplicationFont(str(A / "fonts/Outfit.ttf")) != -1
    OUT.mkdir(exist_ok=True)
    accessibility()
    vision()
    jev()
    app.processEvents()
    print("Created accessibility, local vision and Jev graphics.")


if __name__ == "__main__":
    main()
