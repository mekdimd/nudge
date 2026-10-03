"""See what Nudge can read in the frontmost app, on macOS or Windows.

    uv run python scripts/check_platform.py                    # dump + draw boxes
    uv run python scripts/check_platform.py --press "Settings" # also press one control and verify

Switch to the target app (e.g. Chrome) during the countdown. A JSON dump is saved in dumps/.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

from nudge.core.verify import fingerprint, wait_for_change
from nudge.platform.base import load_adapter
from nudge.ui.coords import physical_to_logical

ROOT = Path(__file__).resolve().parents[1]


class Boxes(QWidget):
    def __init__(self, controls):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setGeometry(QApplication.primaryScreen().virtualGeometry())
        self.controls = controls

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(QFont("Helvetica", 10, QFont.Weight.Bold))
        origin = self.geometry().topLeft()
        for c in self.controls:
            b = c.bounds
            rect = QRectF(b.x - origin.x(), b.y - origin.y(), b.w, b.h)
            color = QColor("#F7B24F") if c.is_text_field else QColor("#4F8EF7")
            painter.setPen(QPen(color, 2))
            painter.drawRect(rect)
            painter.fillRect(QRectF(rect.x(), rect.y() - 14, 34, 14), color)
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(QRectF(rect.x() + 2, rect.y() - 14, 34, 14), c.id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=float, default=4.0)
    parser.add_argument("--press", default="")
    parser.add_argument("--show", type=float, default=6.0, help="seconds to show boxes")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    adapter = load_adapter(physical_to_logical)
    problem = adapter.permission_problem()
    if problem:
        print(problem)
        return 2

    for i in range(int(args.delay), 0, -1):
        print(f"Switch to the target app... {i}", flush=True)
        time.sleep(1)
    target = adapter.frontmost_app()
    if target is None:
        print("No frontmost app found")
        return 1
    print(f"\nFrontmost app: {target.name} (pid {target.pid}) via {adapter.name}")

    with adapter.thread_context():
        snap = adapter.snapshot(target)
        print(f"Window: {snap.window_title!r}  read in {snap.elapsed_ms} ms  "
              f"controls={len(snap.controls)} empty_fields={len(snap.empty_fields)} focused={snap.focused_id}\n")
        for c in snap.controls:
            b = c.bounds
            flags = ("TEXT " if c.is_text_field else "") + ("" if c.enabled else "DISABLED ")
            print(f"{c.id:>5} {c.role:<14} {flags}{c.label[:50]!r:<54} value={c.value!r:<8} "
                  f"ctx={c.context[:24]!r:<26} @ {int(b.x)},{int(b.y)} {int(b.w)}x{int(b.h)}")

        dumps = ROOT / "dumps"
        dumps.mkdir(exist_ok=True)
        path = dumps / f"{sys.platform}-{target.name.replace(' ', '_')}-{int(time.time())}.json"
        path.write_text(json.dumps({
            "platform": sys.platform, "app": target.name, "window": snap.window_title,
            "elapsed_ms": snap.elapsed_ms, "focused": snap.focused_id,
            "controls": [{"id": c.id, "label": c.label, "role": c.role, "value": c.value, "enabled": c.enabled,
                          "text": c.is_text_field, "context": c.context,
                          "bounds": [c.bounds.x, c.bounds.y, c.bounds.w, c.bounds.h]} for c in snap.controls],
        }, indent=2))
        print(f"\nSaved {path}")

        if args.press:
            matches = [c for c in snap.controls if args.press.lower() in c.label.lower()]
            if not matches:
                print(f"No control label contains {args.press!r}")
            else:
                control = matches[0]
                print(f"Pressing {control.id} {control.label!r} ({control.role}) ...")
                before = fingerprint(snap)
                adapter.activate_app(target)
                started = time.perf_counter()
                try:
                    adapter.press(control)
                    how = "semantic press"
                except Exception as exc:
                    print(f"  semantic press failed ({exc}); clicking instead")
                    adapter.click(control)
                    how = "coordinate click"
                after, changed = wait_for_change(lambda: adapter.snapshot(target), before)
                print(f"  {how} took {int((time.perf_counter() - started) * 1000)} ms; UI changed: {changed}; "
                      f"now {len(after.controls)} controls in {after.window_title!r}")
                snap = after

    boxes = Boxes(snap.controls)
    boxes.show()
    QTimer.singleShot(int(args.show * 1000), app.quit)
    app.exec()
    return 0


if __name__ == "__main__":
    sys.exit(main())
