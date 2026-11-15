"""Build the bank demo GIF and poster from the delivered launch film."""

import json
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT.parent / "assets"


def run(*args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *map(str, args)], check=True)


def main():
    video = OUT / "nudge-launch.mp4"
    if not video.is_file():
        raise SystemExit("Render the launch MP4 first.")
    slots = json.loads((PROJECT / "shot-slots.json").read_text())
    _, start, duration = next(s for s in slots if s[0] == "bank")
    # Begin after the request window settles so the GIF has a visible first frame.
    gif_start, gif_duration = start + .3, duration - .3
    run(
        "-ss",
        start + duration - 2.7,
        "-i",
        video,
        "-frames:v",
        1,
        "-update",
        1,
        OUT / "nudge-launch-poster.png",
    )
    filters = (
        f"fps=12,trim=duration={gif_duration - .4},"
        "tpad=stop_mode=clone:stop_duration=0.4,scale=960:-1:flags=lanczos,split[a][b];"
        "[a]palettegen=max_colors=128:stats_mode=diff[p];"
        "[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle"
    )
    run(
        "-ss",
        gif_start,
        "-t",
        gif_duration,
        "-i",
        video,
        "-filter_complex",
        filters,
        "-an",
        "-loop",
        0,
        OUT / "nudge-demo.gif",
    )
    size = (OUT / "nudge-demo.gif").stat().st_size
    assert size < 2.5 * 1024 * 1024, f"GIF is too large: {size} bytes"
    print(
        f"Created the poster and one {gif_duration:g}-second bank GIF ({size / 1024:.0f} KiB)."
    )


if __name__ == "__main__":
    main()
