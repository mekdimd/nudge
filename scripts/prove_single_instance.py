"""Capture real CLI results with an isolated state directory and a UI stub."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from nudge import background
from process_helpers import Processes


def capture():
    rows = []
    original_state = background.STATE
    with tempfile.TemporaryDirectory(prefix="nudge-proof-") as directory:
        root = Path(directory)
        background.STATE = root / "state"
        processes = Processes(root)

        def record(flags, result):
            rows.append(("$ python -m nudge " + " ".join(flags)).rstrip())
            output = (result.stdout + result.stderr).replace(directory, "<demo>").strip()
            rows.extend(output.splitlines())
            rows.append(f"exit code: {result.returncode}")

        try:
            flags = ["--background"]
            first = processes.start(flags, NUDGE_TEST_GATE="1")
            processes.wait_initialized()
            rows.extend(["$ python -m nudge --background", "[First launch is still initializing]"])
            assert first.poll() is None
            result = processes.run(flags)
            assert result.returncode == 0 and "already running" in result.stdout
            record(flags, result)
            count = len((root / "initialized").read_text().splitlines())
            assert count == 1
            rows.append(f"Verified app initializations: {count}")
            (root / "continue").touch()
            stdout, stderr = first.communicate(timeout=5)
            assert first.returncode == 0 and "running in the background" in stdout
            rows.append("[First launch finishes initialization]")
            rows.extend(stdout.replace(directory, "<demo>").strip().splitlines())
            result = processes.run([])
            assert result.returncode == 0 and "already running" in result.stdout
            record([], result)
            result = processes.run(["--stop"])
            assert result.returncode == 0 and "Stopped Nudge" in result.stdout
            record(["--stop"], result)
            assert background.running_pid() is None
            rows.append("Verified ownership released after stop")
            result = processes.run(["--stop"])
            assert result.returncode == 0 and "isn't running" in result.stdout
            record(["--stop"], result)
            result = processes.run(["--detach"], NUDGE_TEST_FAIL="1")
            assert result.returncode != 0 and "startup failed" in result.stderr
            record(["--detach"], result)
            rows.append("[The UI stub deliberately fails startup in the last command]")
        finally:
            processes.close()
            background.STATE = original_state
    return rows


def render(rows, destination):
    from PySide6.QtGui import QColor, QFont, QImage, QPainter
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    destination.parent.mkdir(parents=True, exist_ok=True)
    lines = [line for row in rows for line in textwrap.wrap(row, width=92) or [""]]
    with tempfile.TemporaryDirectory(prefix="nudge-gif-") as directory:
        root = Path(directory)
        for frame in range(1, len(lines) + 1):
            canvas = QImage(1120, 900, QImage.Format.Format_RGB32)
            canvas.fill(QColor("#10151d"))
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            painter.setFont(QFont("Menlo", 16, QFont.Weight.Bold))
            painter.setPen(QColor("#edf3f9"))
            painter.drawText(32, 45, "Nudge allows one process per user")
            painter.setFont(QFont("Menlo", 12))
            painter.setPen(QColor("#9daebf"))
            painter.drawText(32, 78, "macOS | terminal replay | CLI subprocesses | UI stub | isolated state")
            painter.setFont(QFont("Menlo", 13))
            visible = lines[:frame][-27:]
            for index, line in enumerate(visible):
                painter.setPen(QColor("#7ed9a6" if line.startswith("$") else "#dae2ec"))
                painter.drawText(32, 126 + 27 * index, line)
            painter.end()
            assert canvas.save(str(root / f"{frame:03}.png"))
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-framerate", "3", "-i", str(root / "%03d.png"),
            "-filter_complex", "tpad=stop_mode=clone:stop_duration=3,split[a][b];[a]palettegen[p];[b][p]paletteuse",
            "-loop", "0", str(destination),
        ], check=True)
    app.quit()


def main():
    destination = ROOT / "docs" / "assets" / "nudge-single-instance.gif"
    rows = capture()
    render(rows, destination)
    destination.with_suffix(".json").write_text(json.dumps({"platform": sys.platform,
        "ui": "stub", "state": "temporary directory", "transcript": rows}, indent=2) + "\n")
    print("\n".join(rows))
    print(f"Saved {destination}")


if __name__ == "__main__":
    main()
