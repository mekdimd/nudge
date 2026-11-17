import os
import subprocess
import sys
from unittest.mock import Mock

import pytest

from nudge import background


def test_help_works_with_windows_output_encoding(tmp_path):
    environment = {**os.environ, 'PYTHONIOENCODING': 'cp1252:strict'}
    result = subprocess.run(
        [sys.executable, '-m', 'nudge', '--help'],
        cwd=tmp_path, env=environment, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode('cp1252')
    for flag in (b'--keep-running', b'--background', b'--detach', b'--stop'):
        assert flag in result.stdout
    assert b'--persistent' not in result.stdout


@pytest.mark.parametrize("flag", ["--background", "--detach"])
def test_detached_flags_launch_without_starting_the_ui(flag, monkeypatch, capsys):
    import nudge.__main__ as cli

    monkeypatch.setattr(sys, "argv", ["nudge", flag, "--debug"])
    monkeypatch.setattr(background, "running_pid", lambda: None)
    launch = Mock(return_value=123)
    monkeypatch.setattr(background, "detach", launch)
    monkeypatch.setattr(cli, "QApplication", Mock(side_effect=AssertionError("UI started in parent")))
    cli.main()
    launch.assert_called_once_with([flag, "--debug"])
    output = capsys.readouterr().out
    assert "pid 123" in output
    assert str(background.log_path()) in output


@pytest.mark.parametrize("flag", ["--keep-running", "--background", "--detach"])
def test_running_modes_detect_an_existing_instance(flag, monkeypatch, capsys):
    import nudge.__main__ as cli

    monkeypatch.setattr(sys, "argv", ["nudge", flag])
    monkeypatch.setattr(background, "running_pid", lambda: 123)
    launch = Mock()
    monkeypatch.setattr(background, "detach", launch)
    monkeypatch.setattr(cli, "QApplication", Mock(side_effect=AssertionError("UI started twice")))
    cli.main()
    launch.assert_not_called()
    assert "already running (pid 123)" in capsys.readouterr().out


@pytest.mark.parametrize("flag", ["--keep-running", "--background", "--detach"])
def test_stop_takes_precedence_over_launch_flags(flag, monkeypatch, capsys):
    import nudge.__main__ as cli

    monkeypatch.setattr(sys, "argv", ["nudge", flag, "--stop"])
    stop = Mock(return_value=123)
    monkeypatch.setattr(background, "stop", stop)
    monkeypatch.setattr(background, "running_pid", Mock(side_effect=AssertionError("launch checked")))
    cli.main()
    stop.assert_called_once_with()
    assert "Stopped Nudge (pid 123)" in capsys.readouterr().out
