"""Read editor timing from HTML and refresh the export metadata."""

import json
import math
from html.parser import HTMLParser
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


class Timeline(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = {}
        self.scenes = []
        self.audio = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("data-composition-id") == "main":
            self.root = attrs
        elif "data-composition-src" in attrs:
            self.scenes.append(attrs)
        elif tag == "audio":
            self.audio.append(attrs)


def read_timeline():
    timeline = Timeline()
    timeline.feed((PROJECT / "index.html").read_text())
    duration = float(timeline.root["data-duration"])
    end = 0.0
    for scene in sorted(timeline.scenes, key=lambda s: float(s["data-start"])):
        start, length = [float(scene[k]) for k in ["data-start", "data-duration"]]
        assert math.isclose(start, end, abs_tol=0.001), scene["id"]
        assert length > 0 and (PROJECT / scene["data-composition-src"]).is_file()
        end = start + length
    assert math.isclose(end, duration, abs_tol=0.001), (end, duration)
    for audio in timeline.audio:
        assert audio.get("id") and (PROJECT / audio["src"]).is_file()
        assert float(audio["data-duration"]) > 0
        assert (
            float(audio["data-start"]) + float(audio["data-duration"])
            <= duration + 0.001
        )
    return timeline


def sync_metadata():
    timeline = read_timeline()
    slots = [
        [s["id"], float(s["data-start"]), float(s["data-duration"])]
        for s in timeline.scenes
    ]
    cues = [
        [
            Path(a["src"]).name,
            float(a["data-start"]),
            float(a.get("data-volume", 1)),
            float(a["data-duration"]),
        ]
        for a in timeline.audio
        if a["id"] != "music"
    ]
    for name, value in [("shot-slots.json", slots), ("audio-cues.json", cues)]:
        (PROJECT / name).write_text(json.dumps(value, indent=2) + "\n")
    print(
        f"Synced {len(slots)} scenes and {len(cues)} audio cues from the editor HTML."
    )
    return timeline


if __name__ == "__main__":
    sync_metadata()
