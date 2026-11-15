"""Normalize the delivery mix and attach the required music credit."""

from pathlib import Path
import json
import subprocess
import tempfile

VIDEO = Path(__file__).resolve().parents[2] / "assets" / "nudge-launch.mp4"
CREDIT = (
    '"Inspired" Kevin MacLeod (incompetech.com). Licensed under '
    "Creative Commons: By Attribution 4.0. https://creativecommons.org/licenses/by/4.0/"
)


def main():
    measured = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(VIDEO),
            "-af",
            "loudnorm=I=-17:TP=-1.5:LRA=11:print_format=json",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stderr
    levels, _ = json.JSONDecoder().raw_decode(measured[measured.rindex("{") :])
    filters = (
        "loudnorm=I=-17:TP=-1.5:LRA=11:linear=true:"
        f"measured_I={levels['input_i']}:measured_TP={levels['input_tp']}:"
        f"measured_LRA={levels['input_lra']}:measured_thresh={levels['input_thresh']}:"
        f"offset={levels['target_offset']}"
    )
    with tempfile.TemporaryDirectory(
        prefix="nudge-mix-", dir=VIDEO.parent
    ) as temporary:
        result = Path(temporary) / "delivery.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(VIDEO),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0",
                "-c:v",
                "copy",
                "-af",
                filters,
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-metadata",
                "title=Nudge launch",
                "-metadata",
                "comment=" + CREDIT,
                "-metadata",
                "copyright=" + CREDIT,
                "-movflags",
                "+faststart",
                str(result),
            ],
            check=True,
        )
        result.replace(VIDEO)
    print("Normalized the audio mix and added the music credit.")


if __name__ == "__main__":
    main()
