import os
import subprocess
import sys
from importlib.metadata import version
from unittest.mock import Mock

import pytest

from nudge import background


@pytest.mark.parametrize('arguments, fixture', [
    (['--demo', 'gmail-email'], 'gmail'),
    (['--demo', 'chrome-live-caption'], 'live_caption'),
    (['--offline', 'gmail'], 'gmail'),
    (['--offline', 'live_caption'], 'live_caption'),
])
def test_demo_names_select_the_scripted_fixture(arguments, fixture, monkeypatch):
    import nudge.__main__ as cli
    from nudge import app

    monkeypatch.setattr(sys, 'argv', ['nudge', *arguments])
    owner = Mock()
    monkeypatch.setattr(background, 'acquire', lambda: owner)
    selected = []
    monkeypatch.setattr(app, 'run', lambda args, owner, startup: selected.append(args.offline))
    cli.main()
    assert selected == [fixture]


def test_demo_and_legacy_offline_cannot_be_combined(monkeypatch):
    import nudge.__main__ as cli

    monkeypatch.setattr(sys, 'argv', ['nudge', '--demo', 'gmail-email', '--offline', 'live_caption'])
    with pytest.raises(SystemExit) as result:
        cli.main()
    assert result.value.code == 2


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


@pytest.mark.parametrize('entry', ['module', 'console'])
@pytest.mark.parametrize('flag', ['--version', '--doctor'])
def test_diagnostics_work_without_ui_or_network(tmp_path, entry, flag):
    script = '''
import builtins
import runpy
import socket
import sys

original_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    if name.split('.')[0] in {'PySide6', 'httpx', 'google', 'torch', 'ultralytics'} or name in {'nudge.app', 'nudge.background', 'nudge.vision.parser'}:
        raise AssertionError('Unexpected startup import: ' + name)
    return original_import(name, *args, **kwargs)

def no_network(*args, **kwargs):
    raise AssertionError('Diagnostics must run offline')

builtins.__import__ = guarded_import
socket.socket.connect = no_network
socket.create_connection = no_network
sys.argv = ['nudge', sys.argv[2]]
if ENTRY == 'module':
    runpy.run_module('nudge', run_name='__main__')
else:
    from importlib.metadata import distribution
    next(e for e in distribution('nudge').entry_points if e.name == 'nudge').load()()
'''.replace('ENTRY', repr(entry))
    environment = {**os.environ, 'TYPESAFE_API_KEY': '', 'GEMINI_API_KEY': '',
                   'ELEVENLABS_API_KEY': '', 'PYTHONIOENCODING': 'cp1252:strict'}
    result = subprocess.run(
        [sys.executable, '-c', script, entry, flag],
        cwd=tmp_path, env=environment, capture_output=True, timeout=30,
    )
    assert result.returncode == (0 if flag == '--version' else 1), result.stderr.decode('cp1252')
    output = result.stdout.decode('cp1252')
    assert '\x1b[' not in output
    assert f'Nudge {version("nudge")}' in output
    if flag == '--doctor':
        assert 'Python ' in output and 'OS ' in output
        assert 'TYPESAFE_API_KEY: missing' in output
        assert 'GEMINI_API_KEY: missing' in output


@pytest.mark.parametrize("flag", ["--background", "--detach"])
def test_detached_flags_launch_without_starting_the_ui(flag, monkeypatch, capsys):
    import nudge.__main__ as cli
    from nudge import app

    monkeypatch.setattr(sys, "argv", ["nudge", flag, "--debug"])
    monkeypatch.setattr(background, "running_pid", lambda: None)
    launch = Mock(return_value=123)
    monkeypatch.setattr(background, "detach", launch)
    monkeypatch.setattr(app, "QApplication", Mock(side_effect=AssertionError("UI started in parent")))
    cli.main()
    launch.assert_called_once_with([flag, "--debug"])
    output = capsys.readouterr().out
    assert "pid 123" in output
    assert str(background.log_path()) in output


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


@pytest.mark.parametrize("operation", ["stop", "detach"])
def test_process_failures_have_a_nonzero_exit(operation, monkeypatch, capsys):
    import nudge.__main__ as cli

    flag = "--stop" if operation == "stop" else "--background"
    monkeypatch.setattr(sys, "argv", ["nudge", flag])
    monkeypatch.setattr(background, "running_pid", lambda: None)
    monkeypatch.setattr(background, operation, Mock(side_effect=background.ProcessError("startup or exit failed")))
    with pytest.raises(SystemExit) as result:
        cli.main()
    assert result.value.code == 1
    assert "failed" in capsys.readouterr().err
