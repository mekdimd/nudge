import io
import sys

import pytest

from nudge import startup as module
from nudge.startup import ASCII_FRAMES, BANNER, Startup


class Terminal(io.StringIO):
    def __init__(self, encoding="utf-8"):
        super().__init__()
        self._encoding = encoding

    @property
    def encoding(self):
        return self._encoding

    def isatty(self):
        return True


@pytest.fixture(autouse=True)
def slow_spinner(monkeypatch):
    monkeypatch.setattr(module, "TICK", 60)
    monkeypatch.setenv("NO_COLOR", "1")


def test_terminal_prints_the_banner_at_once_then_a_spinner_until_ready():
    terminal = Terminal()
    progress = Startup("1.2.3", terminal)
    assert terminal.getvalue() == "\n" + BANNER + "\nv1.2.3\n\n"
    progress.step("Loading Qt and Nudge modules")
    assert terminal.getvalue().endswith("\r\x1b[2K⠋ Loading Qt and Nudge modules")
    progress.ready()
    assert terminal.getvalue().endswith("\r\x1b[2K✓ Ready in 0.0 s\n")


def test_terminal_without_unicode_uses_an_ascii_spinner():
    terminal = Terminal("cp1252")
    progress = Startup("1.2.3", terminal)
    terminal.getvalue().encode("cp1252")
    progress.step("Starting Qt")
    assert terminal.getvalue().rsplit("\r\x1b[2K", 1)[1][0] in ASCII_FRAMES
    progress.ready()
    assert terminal.getvalue().endswith("\r\x1b[2KReady in 0.0 s\n")


def test_redirected_output_gets_plain_status_lines():
    stream = io.StringIO()
    progress = Startup("1.2.3", stream)
    progress.step("Loading Qt and Nudge modules")
    progress.step("Starting Qt")
    progress.ready()
    progress.step("Late step")
    assert stream.getvalue().splitlines() == [
        "Starting Nudge 1.2.3",
        "  Loading Qt and Nudge modules...",
        "  Starting Qt...",
        "Ready in 0.0 s",
    ]


def test_other_output_erases_the_spinner_line_first(capsys):
    terminal = Terminal()
    progress = Startup("1.2.3", terminal)
    progress.step("Starting Qt")
    print("qt warning", file=sys.stderr)
    assert terminal.getvalue().endswith("⠋ Starting Qt\r\x1b[2K")
    progress.ready()
    assert capsys.readouterr().err == "qt warning\n"


def test_failure_clears_the_spinner_names_the_step_and_restores_streams(capsys):
    stdout, stderr = sys.stdout, sys.stderr
    terminal = Terminal()
    progress = Startup("1.2.3", terminal)
    progress.step("Starting Qt")
    assert sys.stderr is not stderr
    progress.fail()
    progress.ready()
    assert (sys.stdout, sys.stderr) == (stdout, stderr)
    assert terminal.getvalue().endswith("⠋ Starting Qt\r\x1b[2K")
    assert capsys.readouterr().err == "Startup failed while starting Qt.\n"
