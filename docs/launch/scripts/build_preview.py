"""Build the bank demo GIF and poster from the delivered launch film."""

import subprocess
from pathlib import Path

from sync_timeline import sync_metadata

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT.parent / "assets"


def run(*args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *map(str, args)], check=True)


def main():
    video = OUT / "nudge-launch.mp4"
    if not video.is_file():
        raise SystemExit("Render the launch MP4 first.")
    timeline = sync_metadata()
    bank = next(s for s in timeline.scenes if s["id"] == "bank")
    start, duration = [float(bank[k]) for k in ["data-start", "data-duration"]]
    # Begin after the request window settles so the GIF has a visible first frame.
    gif_start, gif_duration = start + 0.3, duration - 0.3
    run(
        "-ss",
        start + duration - 0.7,
        "-i",
        video,
        "-frames:v",
        1,
        "-update",
        1,
        OUT / "nudge-launch-poster.png",
    )
    for fps, width, colors in [
        (12, 960, 128),
        (10, 960, 128),
        (10, 880, 128),
        (10, 880, 96),
    ]:
        filters = (
            f"fps={fps},trim=duration={gif_duration - 0.4},"
            f"tpad=stop_mode=clone:stop_duration=0.4,scale={width}:-1:flags=lanczos,split[a][b];"
            f"[a]palettegen=max_colors={colors}:stats_mode=diff[p];"
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
        if (OUT / "nudge-demo.gif").stat().st_size < 2.5 * 1024 * 1024:
            break
    size = (OUT / "nudge-demo.gif").stat().st_size
    assert size < 2.5 * 1024 * 1024, f"GIF is too large: {size} bytes"
    print(
        f"Created the poster and one {gif_duration:g}-second bank GIF ({size / 1024:.0f} KiB)."
    )


if __name__ == "__main__":
    main()
