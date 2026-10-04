from nudge.core.loop import NudgeLoop
from nudge.core.models import AppRef, Control, Rect
from nudge.platform.fake import FakeAdapter
from nudge.vision.parser import merge

from helpers import RecordingEvents, ScriptedJev


def test_text_inside_a_detected_box_names_it_and_the_rest_need_captions():
    icons = [(0, 0, 100, 40), (200, 0, 240, 40)]
    texts = [("Play", (10, 10, 50, 30)), ("Olivia", (52, 10, 90, 30)), ("Home", (400, 0, 450, 20))]
    labelled, unnamed = merge(icons, texts)
    assert ("Play Olivia", (0, 0, 100, 40)) in labelled
    assert ("Home", (400, 0, 450, 20)) in labelled
    assert unnamed == [(200, 0, 240, 40)]


class FakeVision:
    def __init__(self, controls):
        self.controls = controls
        self.calls = 0

    def find(self, snapshot):
        self.calls += 1
        return list(self.controls), 900


class ClickRecordingAdapter(FakeAdapter):
    def click(self, control, double=False):
        self.log.append(f"{'double ' if double else ''}click {control.id}")
        if control.source == "tree":
            self.press(control)
        else:
            self.screen = "playing"


SPARSE = {
    "home": {"title": "Spotify", "controls": [{"id": "t1", "label": "Close", "role": "button"}]},
    "playing": {"title": "Spotify", "controls": [{"id": "t1", "label": "Close", "role": "button"}, {"id": "t2", "label": "Pause", "role": "button"}]},
}


def make_loop(adapter, jev, events, vision):
    return NudgeLoop(adapter, jev, None, events, hold_seconds=0, own_pid=1, settle_timeout=0.05, startup_delay=0, vision=vision)


def test_sparse_tree_looks_with_vision_and_clicks_what_it_found():
    adapter = ClickRecordingAdapter(SPARSE, "home", AppRef("Spotify", 7))
    play = Control(id="v1", label="Play button icon", role="button", bounds=Rect(10, 10, 40, 40), source="vision")
    vision = FakeVision([play])
    events = RecordingEvents()
    outcome = make_loop(adapter, ScriptedJev(["Play button icon"]), events, vision).run("play music", adapter.app)

    assert outcome.ok, outcome.message
    assert vision.calls >= 1
    assert "click v1" in adapter.log
    assert any(c.source == "vision" for s in events.snapshots for c in s.controls)


def test_dock_icons_do_not_hide_a_sparse_app_from_vision():
    dock = [{"id": f"s{i}", "label": name} for i, name in enumerate(["Spotify", "Finder", "Notes", "Mail", "Maps", "Music", "News", "Photos", "Arc", "Zoom"])]
    adapter = ClickRecordingAdapter(SPARSE, "home", AppRef("Spotify", 7), shell=dock)
    play = Control(id="v1", label="Play button icon", role="button", bounds=Rect(10, 10, 40, 40), source="vision")
    vision = FakeVision([play])
    events = RecordingEvents()
    outcome = make_loop(adapter, ScriptedJev(["__none__", "Play button icon"]), events, vision).run("play music", adapter.app)

    assert outcome.ok, outcome.message
    assert vision.calls >= 2
    assert "click v1" in adapter.log
    shell_labels = {c.label for s in events.snapshots for c in s.controls if c.shell}
    assert "Finder" in shell_labels and "Spotify" not in shell_labels


def test_rich_tree_and_confident_jev_never_use_vision():
    adapter = FakeAdapter.from_fixture("live_caption")
    vision = FakeVision([])
    jev = ScriptedJev(["Chrome", "Settings", "Accessibility", "Live Caption"])
    for screen in adapter.screens.values():
        for i in range(10):
            screen["controls"].append({"id": f"pad{i}", "label": f"Filler {i}", "role": "button"})
    outcome = make_loop(adapter, jev, RecordingEvents(), vision).run("turn on Live Caption", adapter.app)

    assert outcome.ok, outcome.message
    assert vision.calls == 0


def test_unsure_jev_gets_a_second_opinion_after_vision():
    adapter = FakeAdapter.from_fixture("live_caption")
    for screen in adapter.screens.values():
        for i in range(10):
            screen["controls"].append({"id": f"pad{i}", "label": f"Filler {i}", "role": "button"})
    vision = FakeVision([Control(id="v1", label="Gear icon", role="button", bounds=Rect(5, 5, 20, 20), source="vision")])
    jev = ScriptedJev([("Chrome", 0.4), "Chrome", "Settings", "Accessibility", "Live Caption"])
    events = RecordingEvents()
    outcome = make_loop(adapter, jev, events, vision).run("turn on Live Caption", adapter.app)

    assert outcome.ok, outcome.message
    assert vision.calls == 1
    assert not any(line.startswith("choose") for line in events.log)
