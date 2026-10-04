from nudge.core.loop import NudgeLoop
from nudge.platform.fake import FakeAdapter

from helpers import FakeWriter, RecordingEvents, ScriptedJev

LIVE_CAPTION = ["Chrome", "Settings", "Accessibility", "Live Caption"]
EMAIL_GOAL = "email prof.lee@sfu.ca that I'm sick and will miss lecture"
DRAFT = {
    "To recipients": "prof.lee@sfu.ca",
    "Subject": "Missing lecture today",
    "Message Body": "Hi Professor Lee, I'm sick and will miss lecture today.",
}


def make_loop(adapter, jev, events, writer=None):
    return NudgeLoop(adapter, jev, writer, events, hold_seconds=0, own_pid=1, settle_timeout=0.05, startup_delay=0, step_delay=0)


def test_live_caption_flow_presses_four_controls_and_finishes():
    adapter = FakeAdapter.from_fixture("live_caption")
    jev = ScriptedJev(LIVE_CAPTION)
    events = RecordingEvents()
    outcome = make_loop(adapter, jev, events).run("turn on Live Caption", adapter.app)

    assert outcome.ok, outcome.message
    assert adapter.log == ["press b4", "press m3", "press s3", "press a1"]
    assert adapter.snapshot(adapter.app).by_id("a1").value == "on"
    assert jev.seen_history[-1][-1] == "Press “Live Caption”: worked"
    assert events.result[0] is True


def test_gmail_flow_drafts_with_gemini_and_confirms_send():
    adapter = FakeAdapter.from_fixture("gmail")
    jev = ScriptedJev(["Compose", "fill", "Send"])
    writer = FakeWriter(DRAFT)
    events = RecordingEvents()
    outcome = make_loop(adapter, jev, events, writer).run(EMAIL_GOAL, adapter.app)

    assert outcome.ok, outcome.message
    assert "set c1='prof.lee@sfu.ca'" in adapter.log
    assert adapter.log[-1] == "press c4"
    assert adapter.screen == "sent"
    assert any(line.startswith("confirm") and "send" in line for line in events.log)
    assert writer.fill_calls == 1


def test_declining_send_confirmation_never_presses_send():
    adapter = FakeAdapter.from_fixture("gmail")
    events = RecordingEvents(confirm_answer=False)
    outcome = make_loop(adapter, ScriptedJev(["Compose", "fill", "Send"]), events, FakeWriter(DRAFT)).run(EMAIL_GOAL, adapter.app)

    assert not outcome.ok
    assert outcome.reason == "declined"
    assert "press c4" not in adapter.log


def test_user_edits_to_draft_are_what_gets_typed():
    adapter = FakeAdapter.from_fixture("gmail")
    events = RecordingEvents(approve_edits={"Subject": "Sick today"})
    make_loop(adapter, ScriptedJev(["Compose", "fill", "Send"]), events, FakeWriter(DRAFT)).run(EMAIL_GOAL, adapter.app)
    assert "set c2='Sick today'" in adapter.log


def test_without_gemini_the_user_types_the_draft():
    adapter = FakeAdapter.from_fixture("gmail")
    events = RecordingEvents(approve_edits={"Subject": "typed by me"})
    outcome = make_loop(adapter, ScriptedJev(["Compose", "fill"]), events, writer=None).run(EMAIL_GOAL, adapter.app)
    assert outcome.ok
    assert "set c2='typed by me'" in adapter.log
    assert not any(line.startswith("set c1") for line in adapter.log)


def test_low_confidence_asks_user_to_pick():
    adapter = FakeAdapter.from_fixture("live_caption")
    events = RecordingEvents()
    make_loop(adapter, ScriptedJev([("Chrome", 0.4)]), events).run("turn on Live Caption", adapter.app)
    assert any(line.startswith("choose") for line in events.log)
    assert adapter.log[0] == "press b4"


def test_picker_cancel_stops_without_acting():
    adapter = FakeAdapter.from_fixture("live_caption")
    events = RecordingEvents(choose_answer=None)
    outcome = make_loop(adapter, ScriptedJev([("Chrome", 0.4)]), events).run("turn on Live Caption", adapter.app)
    assert outcome.reason == "cancelled"
    assert adapter.log == []


def test_no_change_is_never_retried_automatically():
    adapter = FakeAdapter.from_fixture("live_caption")
    events = RecordingEvents(recover_answers=["stop"])
    outcome = make_loop(adapter, ScriptedJev(["Reload"]), events).run("reload", adapter.app)
    assert outcome.reason == "no_change"
    assert adapter.log == ["press b2"]


def test_pick_another_excludes_the_failed_control():
    adapter = FakeAdapter.from_fixture("live_caption")
    jev = ScriptedJev(["Reload", "Chrome"])
    events = RecordingEvents(recover_answers=["other"])
    make_loop(adapter, jev, events).run("open the menu", adapter.app)
    assert adapter.log == ["press b2", "press b4"]


def test_target_absent_asks_user_then_stops_when_dismissed():
    adapter = FakeAdapter.from_fixture("live_caption")
    events = RecordingEvents(ask_answers=[None])
    outcome = make_loop(adapter, ScriptedJev(["__none__", "__none__"]), events).run("turn on Live Caption", adapter.app)
    assert outcome.reason == "cancelled"
    assert any(line.startswith("ask") for line in events.log)


def test_cancel_during_hold_stops_before_pressing():
    adapter = FakeAdapter.from_fixture("live_caption")
    events = RecordingEvents(cancel_after_proposals=1)
    outcome = make_loop(adapter, ScriptedJev(LIVE_CAPTION), events).run("turn on Live Caption", adapter.app)
    assert outcome.reason == "cancelled"
    assert adapter.log == []


def test_stops_when_another_app_comes_to_front():
    from nudge.core.models import AppRef

    adapter = FakeAdapter.from_fixture("live_caption")
    target = adapter.app
    adapter.app = AppRef(name="Slack", pid=999)
    outcome = make_loop(adapter, ScriptedJev(LIVE_CAPTION), RecordingEvents()).run("turn on Live Caption", target)
    assert outcome.reason == "app_changed"
    assert adapter.log == []


def test_step_budget():
    adapter = FakeAdapter.from_fixture("live_caption")
    loop = make_loop(adapter, ScriptedJev(["Chrome", "Settings", "Accessibility"], done_after=False), RecordingEvents())
    loop.max_steps = 2
    outcome = loop.run("turn on Live Caption", adapter.app)
    assert outcome.reason == "step_budget"
    assert len(adapter.log) == 2


def test_go_to_url_types_approved_address():
    adapter = FakeAdapter.from_fixture("live_caption")
    events = RecordingEvents()
    make_loop(adapter, ScriptedJev(["go_to_url"]), events, FakeWriter({}, url="https://www.sfu.ca/students.html")).run(
        "open the SFU students page", adapter.app
    )
    assert adapter.log[:3] == ["key address_bar", "type 'https://www.sfu.ca/students.html'", "key enter"]


def shell_adapter():
    screens = {"home": {"title": "Notes", "controls": [{"id": "a1", "label": "Save"}]}}
    shell = [{"id": "s1", "label": "Spotify", "app": "Spotify", "pid": 9}]
    return FakeAdapter(screens, "home", shell=shell)


def test_taskbar_word_in_goal_exposes_taskbar_and_follows_the_new_app():
    adapter = shell_adapter()
    jev = ScriptedJev(["Spotify"])
    outcome = make_loop(adapter, jev, RecordingEvents()).run("open Spotify from the taskbar", adapter.app)

    assert outcome.ok, outcome.message
    assert adapter.log == ["press s1"]
    assert adapter.app.name == "Spotify"


def test_taskbar_is_hidden_until_needed():
    adapter = shell_adapter()
    events = RecordingEvents()
    make_loop(adapter, ScriptedJev(["Save"]), events).run("save the note", adapter.app)
    assert all(not c.shell for s in events.snapshots for c in s.controls)


def test_taskbar_is_tried_when_nothing_in_the_app_fits():
    adapter = shell_adapter()
    events = RecordingEvents()
    jev = ScriptedJev(["__none__", "Spotify"])
    outcome = make_loop(adapter, jev, events).run("open Spotify", adapter.app)
    assert adapter.log == ["press s1"], (outcome.message, events.log)
