import io

from nudge.core.models import Action, AppRef
from nudge.ui.console import Console
from nudge.ui.timeline import Entry, RunRecorder, Timeline

CHROME = AppRef("Google Chrome", 1)


def console():
    timeline, stream = Timeline(), io.StringIO()
    return timeline, Console(timeline, stream, color=False), stream


def test_prints_settled_entries_once_and_skips_running_ones():
    timeline, _, stream = console()
    recorder = RunRecorder(timeline)
    recorder.started("turn on Live Caption", CHROME)
    recorder.proposed(Action(kind="press", option_key="k", label="Settings"))
    recorder.acted(Action(kind="press", option_key="k", label="Settings"), True)
    recorder.finished(True, "Done in 1 step · 1.2 s · Jev 130 ms per decision")
    assert stream.getvalue().splitlines() == [
        "▶ turn on Live Caption · Google Chrome",
        "  Google Chrome Pressed “Settings”",
        "✓ Done in 1 step · 1.2 s · Jev 130 ms per decision",
    ]


def test_formats_failures_waits_and_details():
    _, out, _ = console()
    assert out.format(Entry("jev", "Picked", "Menu", detail="92% · 130 ms")) == "  Jev       Picked “Menu”  92% · 130 ms"
    assert out.format(Entry("app", "Pressed", "Play", state="failed", detail="nothing changed", app=CHROME)).endswith("nothing changed  ✕")
    assert out.format(Entry("nudge", "Waiting for your OK", state="waiting")).endswith("waiting for you")
    assert out.format(Entry("nudge", "Stopped.", state="failed")) == "✕ Stopped."


def test_a_wait_that_gets_answered_is_not_printed_twice():
    timeline, _, stream = console()
    recorder = RunRecorder(timeline)
    recorder.started("x", CHROME)
    recorder.waiting("Waiting for your OK")
    recorder.answered()
    assert stream.getvalue().count("Waiting for your OK") == 1


def test_clearing_starts_a_fresh_run():
    timeline, _, stream = console()
    recorder = RunRecorder(timeline)
    recorder.started("first", CHROME)
    recorder.started("second", CHROME)
    assert "▶ second" in stream.getvalue()


def test_banner_lists_features():
    _, out, stream = console()
    out.banner({"Jev": True, "Gemini": False})
    assert stream.getvalue().strip() == "Nudge · Jev  Gemini off"


def test_color_is_off_when_not_a_terminal():
    timeline = Timeline()
    assert Console(timeline, io.StringIO()).color is False
