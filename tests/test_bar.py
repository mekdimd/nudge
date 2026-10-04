import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton

OPTIONS = [("k1", "Search", 0.41), ("k2", "Home", 0.33), ("k3", "Your Library", 0.12)]


@pytest.fixture
def bar(qapp):
    from nudge.ui.bar import Bar
    from nudge.ui.timeline import Timeline

    b = Bar(Timeline())
    b.show()
    yield b
    b.close()
    b.deleteLater()


def visible_in_panel(bar, kind):
    QApplication.processEvents()  # widgets added to a shown parent appear on the next event loop pass
    return [w for w in bar.panel.findChildren(kind) if w.isVisibleTo(bar.panel)]


def panel_buttons(bar, kind=None):
    QApplication.processEvents()
    return [
        b for b in bar.panel.findChildren(QPushButton)
        if b.isVisibleTo(bar.panel) and (kind is None or b.property("kind") == kind)
    ]


def test_choice_spoken_number_replies_with_key(bar):
    got = []
    bar.show_choice("Pick one:", OPTIONS, got.append)
    assert bar.spoken("two") is True
    assert got == ["k2"]
    assert not bar.panel.isVisible()


def test_choice_spoken_stop_replies_none(bar):
    got = []
    bar.show_choice("Pick one:", OPTIONS, got.append)
    assert bar.spoken("stop") is True
    assert got == [None]


def test_choice_unrecognised_speech_keeps_prompt_open(bar):
    got = []
    bar.show_choice("Pick one:", OPTIONS, got.append)
    assert bar.spoken("banana bread") is False
    assert got == []
    assert bar.panel.isVisible()


@pytest.mark.parametrize("said,expected", [("yes", True), ("no", False), ("stop", False)])
def test_confirm_by_voice(bar, said, expected):
    got = []
    bar.show_confirm("Press “Send”? This will send and may not be undoable.", got.append)
    assert bar.spoken(said) is True
    assert got == [expected]


@pytest.mark.parametrize("said,expected", [("try again", "retry"), ("click it", "click"), ("something else", "other"), ("stop", "stop")])
def test_recover_by_voice(bar, said, expected):
    got = []
    bar.show_recover("Press “Play” didn't change anything.", got.append)
    assert bar.spoken(said) is True
    assert got == [expected]


def test_draft_enter_types_the_edited_values(bar):
    got = []
    bar.show_draft("Check the draft.", [("f1", "Subject", "Missing lecture")], got.append)
    editor = visible_in_panel(bar, QLineEdit)[0]
    editor.setText("Sick today")
    QTest.keyClick(bar, Qt.Key.Key_Return)
    assert got == [{"f1": "Sick today"}]


def test_draft_primary_button_types(bar):
    got = []
    bar.show_draft("Check the draft.", [("f1", "Subject", "Hi")], got.append)
    panel_buttons(bar, "primary")[0].click()
    assert got == [{"f1": "Hi"}]


def test_draft_spoken_stop_replies_none(bar):
    got = []
    bar.show_draft("Check the draft.", [("f1", "Subject", "Hi")], got.append)
    assert bar.spoken("stop") is True
    assert got == [None]


def test_url_spoken_yes_replies_with_the_address(bar):
    got = []
    bar.show_url("https://www.sfu.ca", "sfu", got.append)
    assert bar.spoken("yes") is True
    assert got == ["https://www.sfu.ca"]


def test_ask_spoken_detail_becomes_the_reply(bar):
    got = []
    bar.show_ask("I can't see the control.", got.append)
    assert bar.spoken("the blue one at the top") is True
    assert got == ["the blue one at the top"]


def test_ask_spoken_stop_replies_none(bar):
    got = []
    bar.show_ask("I can't see the control.", got.append)
    assert bar.spoken("stop") is True
    assert got == [None]


def test_answering_closes_the_panel_and_says_so(bar):
    closed = []
    bar.panel_closed.connect(lambda: closed.append(True))
    bar.show_confirm("Press “Send”? This will send and may not be undoable.", lambda _: None)
    closed.clear()
    bar.spoken("yes")
    assert closed and not bar.panel.isVisible() and bar.spoken is None


def test_running_swaps_go_for_stop_and_locks_the_input(bar):
    bar.set_running(True)
    assert bar.stop.isVisible() and not bar.go.isVisible() and bar.input.isReadOnly()
    bar.set_running(False)
    assert bar.go.isVisible() and not bar.stop.isVisible() and not bar.input.isReadOnly()


def test_go_emits_the_goal(bar):
    goals = []
    bar.go_requested.connect(goals.append)
    bar.input.setText("turn on Live Caption")
    bar.go.click()
    assert goals == ["turn on Live Caption"]


def test_go_does_nothing_while_running(bar):
    goals = []
    bar.go_requested.connect(goals.append)
    bar.input.setText("x")
    bar.set_running(True)
    bar._go()
    assert goals == []


def test_stop_button_requests_stop(bar):
    stops = []
    bar.stop_requested.connect(lambda: stops.append(True))
    bar.set_running(True)
    bar.stop.click()
    assert stops == [True]


def test_escape_while_running_requests_stop(bar):
    stops = []
    bar.stop_requested.connect(lambda: stops.append(True))
    bar.set_running(True)
    bar._escape()
    assert stops == [True]


PROMPTS = [
    ("show_choice", ("Pick one:", OPTIONS)),
    ("show_draft", ("Check the draft.", [("f1", "Subject", "Hi")])),
    ("show_url", ("https://www.sfu.ca", "sfu")),
    ("show_confirm", ("Press “Send”? This will send and may not be undoable.",)),
    ("show_recover", ("Press “Play” didn't change anything.",)),
    ("show_ask", ("I can't see the control.",)),
]


@pytest.mark.parametrize("method,args", PROMPTS)
def test_question_cards_never_have_their_own_stop(bar, method, args):
    bar.set_running(True)
    getattr(bar, method)(*args, lambda _: None)
    assert not [b for b in panel_buttons(bar) if b.property("kind") in ("danger", "stop") or "Stop" in b.text()]
    assert bar.stop.isVisible()


@pytest.mark.parametrize("method,args", PROMPTS)
def test_waiting_for_an_answer_turns_the_bar_amber_and_back(bar, method, args):
    bar.set_running(True)
    getattr(bar, method)(*args, lambda _: None)
    assert bar.state == "waiting"
    bar.clear_panel()
    assert bar.state == "working"


def test_confirm_names_the_action(bar):
    bar.show_confirm("Press “Send”? This will send and may not be undoable.", lambda _: None)
    texts = [b.text() for b in panel_buttons(bar)]
    assert texts == ["Yes, send", "Not yet"]


def test_confirm_has_no_enter_shortcut(bar):
    got = []
    bar.show_confirm("Press “Send”? This will send and may not be undoable.", got.append)
    QTest.keyClick(bar, Qt.Key.Key_Return)
    assert got == []


def test_recover_enter_retries(bar):
    got = []
    bar.show_recover("Press “Play” didn't change anything.", got.append)
    QTest.keyClick(bar, Qt.Key.Key_Return)
    assert got == ["retry"]


def test_choice_number_keys_pick(bar):
    got = []
    bar.set_running(True)
    bar.show_choice("Pick one:", OPTIONS, got.append)
    QTest.keyClick(bar, Qt.Key.Key_3)
    assert got == ["k3"]


def test_failed_run_offers_retry_until_the_goal_is_edited(bar):
    bar.input.setText("turn on Live Caption")
    bar.set_running(True)
    bar.set_running(False)
    bar.show_result(False)
    assert "Retry" in bar.go.text()
    QTest.keyClicks(bar.input, "!")
    assert bar.go.text() == "Go"


def test_successful_run_keeps_go(bar):
    bar.input.setText("x")
    bar.set_running(True)
    bar.set_running(False)
    bar.show_result(True)
    assert bar.go.text() == "Go"


def test_target_chip_shows_the_app(bar):
    from nudge.core.models import AppRef

    bar.set_target(AppRef("Google Chrome", 4242))
    assert bar.target.text.text() == "in Google Chrome"
    bar.set_target(None)
    assert bar.target.text.text() == "no app selected"


def test_hint_is_hidden_during_a_run_unless_asked(bar):
    bar.set_running(True)
    bar.set_status("Peek: 12 controls")
    assert not bar.hint.isVisible()
    bar.set_status("Listening: open settings", during_run=True)
    assert bar.hint.isVisible()
    bar.set_running(False)
    bar.set_status("Add TYPESAFE_API_KEY to .env", tone="warn")
    assert bar.hint.isVisible()


def test_step_count_shows_in_the_hint(bar):
    bar.set_running(True)
    bar.set_step(3)
    assert bar.hint.isVisible() and bar.hint.text().startswith("Step 3 of 12")
