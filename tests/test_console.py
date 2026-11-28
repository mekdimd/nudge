import io

from nudge.core.models import Action, AppRef
from nudge.logs import REDACTED
from nudge.ui.console import Console
from nudge.ui.timeline import Entry, RunRecorder, Timeline

CHROME = AppRef("Google Chrome", 1)


def console(detailed: bool = False):
    timeline, stream = Timeline(), io.StringIO()
    return timeline, Console(timeline, stream, color=False, detailed=detailed), stream


def test_prints_settled_entries_once_and_omits_full_goal_by_default():
    timeline, _, stream = console()
    recorder = RunRecorder(timeline)
    recorder.started("email prof.lee@sfu.ca that I am sick", CHROME)
    recorder.proposed(Action(kind="press", option_key="k", label="Settings"))
    recorder.acted(Action(kind="press", option_key="k", label="Settings"), True)
    recorder.finished(True, "Done in 1 step · 1.2 s · Jev 130 ms per decision")
    assert stream.getvalue().splitlines() == [
        "▶ Task started · Google Chrome",
        "  Google Chrome Pressed “Settings”",
        "✓ Done in 1 step · 1.2 s · Jev 130 ms per decision",
    ]
    assert "prof.lee@sfu.ca" not in stream.getvalue()


def test_detailed_logs_opt_in_includes_full_goal_and_url():
    timeline, _, stream = console(detailed=True)
    recorder = RunRecorder(timeline)
    recorder.started("turn on Live Caption", CHROME)
    recorder.acted(
        Action(kind="go_to_url", option_key="u", url="https://www.youtube.com/results?search_query=captions"),
        True,
    )
    assert stream.getvalue().splitlines() == [
        "▶ turn on Live Caption · Google Chrome",
        "  Google Chrome Opened “https://www.youtube.com/results?search_query=captions”",
    ]


def test_default_logs_strip_url_path_and_query():
    timeline, _, stream = console()
    recorder = RunRecorder(timeline)
    recorder.started("find my bank statement", CHROME)
    recorder.acted(
        Action(kind="go_to_url", option_key="u", url="https://user:pass@www.youtube.com/results?search_query=private+query"),
        True,
    )
    assert stream.getvalue().splitlines() == [
        "▶ Task started · Google Chrome",
        "  Google Chrome Opened “https://www.youtube.com”",
    ]
    assert "private+query" not in stream.getvalue()
    assert "user:pass" not in stream.getvalue()


def test_console_never_logs_api_keys_even_with_detailed_logs(monkeypatch):
    secret = "ts_secret_console_key_99"
    monkeypatch.setenv("TYPESAFE_API_KEY", secret)
    timeline, out, stream = console(detailed=True)
    recorder = RunRecorder(timeline)
    recorder.started(f"use {secret}", CHROME)
    recorder.finished(False, f"Jev returned 401: {secret}")
    out.note(f"token={secret}")
    output = stream.getvalue()
    assert secret not in output
    assert REDACTED in output


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
    timeline, _, stream = console(detailed=True)
    recorder = RunRecorder(timeline)
    recorder.started("first", CHROME)
    recorder.started("second", CHROME)
    assert "▶ second" in stream.getvalue()


def test_banner_lists_features():
    _, out, stream = console()
    out.banner({"Jev": True, "Gemini": False})
    assert stream.getvalue() == "\nNudge · Jev  Gemini off\n"


def test_color_is_off_when_not_a_terminal():
    timeline = Timeline()
    assert Console(timeline, io.StringIO()).color is False
