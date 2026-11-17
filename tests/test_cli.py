import os
import subprocess
import sys
from importlib.metadata import version

import pytest


def test_help_works_with_windows_output_encoding(tmp_path):
    environment = {**os.environ, 'PYTHONIOENCODING': 'cp1252:strict'}
    result = subprocess.run(
        [sys.executable, '-m', 'nudge', '--help'],
        cwd=tmp_path, env=environment, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode('cp1252')
    assert b'--persistent' in result.stdout


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
