"""Build one complete CLI-to-result bank GIF and the video poster."""

from pathlib import Path
import os
import subprocess
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT.parent / "assets"


def run(*args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *map(str, args)], check=True)


def terminal_intro(destination):
    app = QApplication.instance() or QApplication([])
    canvas = QImage(1920, 1080, QImage.Format.Format_RGB32)
    canvas.fill(QColor("#11151c"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont("Menlo")
    font.setPixelSize(38)
    painter.setFont(font)
    painter.setPen(QColor("#dce4ef"))
    lines = [
        "$ node docs/launch/scripts/capture_host.mjs bank",
        "  'http://127.0.0.1:8765/?app=bank&theme=light'",
        "  'download my October bank statement'",
    ]
    for i, line in enumerate(lines):
        painter.drawText(100, 200 + i * 68, line)
    output = QImage(str(OUT / "nudge-terminal.png"))
    assert not output.isNull()
    painter.drawImage(QRectF(55, 500, 1800, 99), output, QRectF(0, 84, 1600, 88))
    painter.end()
    assert canvas.save(str(destination))


def main():
    video = OUT / "nudge-launch.mp4"
    if not video.is_file():
        raise SystemExit("Render the launch MP4 first.")
    run(
        "-ss",
        "10.5",
        "-i",
        video,
        "-frames:v",
        "1",
        "-update",
        "1",
        OUT / "nudge-launch-poster.png",
    )
    with tempfile.TemporaryDirectory(prefix="nudge-gif-") as temporary:
        temp = Path(temporary)
        terminal_intro(temp / "intro.png")
        filters = (
            "[0:v]fps=15,trim=duration=1.4,setpts=PTS-STARTPTS[intro];"
            "[1:v]fps=15,trim=start=4.8:end=10.8,setpts=PTS-STARTPTS,"
            "tpad=stop_mode=clone:stop_duration=0.6[run];"
            "[intro][run]concat=n=2:v=1:a=0,scale=960:-1:flags=lanczos,split[a][b];"
            "[a]palettegen=max_colors=128:stats_mode=diff[p];"
            "[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle[out]"
        )
        run(
            "-loop",
            "1",
            "-t",
            "1.4",
            "-i",
            temp / "intro.png",
            "-i",
            video,
            "-filter_complex",
            filters,
            "-map",
            "[out]",
            "-an",
            "-loop",
            "0",
            OUT / "nudge-demo.gif",
        )
    size = (OUT / "nudge-demo.gif").stat().st_size
    assert size < 2.5 * 1024 * 1024, f"GIF is too large: {size} bytes"
    print(
        f"Created the poster and one complete 8-second bank GIF ({size / 1024:.0f} KiB)."
    )


if __name__ == "__main__":
    main()
