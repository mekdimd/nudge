import os
from importlib import import_module

import pytest

from docs.launch.scripts.capture_browser import BrowserCaptureAdapter
from nudge.core.actions import FILL_KEY, build_options


@pytest.mark.parametrize('script', ['capture_browser', 'capture_ui', 'capture_wake'])
def test_capture_scripts_can_construct_the_gui_controller(script):
    capture = import_module(f'docs.launch.scripts.{script}')
    from nudge.app import Nudge, NudgeLoop

    assert capture.main.Nudge is Nudge
    assert capture.main.NudgeLoop is NudgeLoop


def test_capture_adapter_exposes_search_fields_for_drafting(tmp_path):
    adapter = BrowserCaptureAdapter(tmp_path, app_pid=os.getpid())
    adapter.rpc = lambda operation: {
        'title': 'Video search', 'width': 1280, 'height': 800,
        'controls': [
            {'id': 'query', 'label': 'Search', 'role': 'text field', 'value': '',
             'bounds': {'x': 300, 'y': 8, 'w': 500, 'h': 40}},
            {'id': 'search', 'label': 'Search', 'role': 'button',
             'bounds': {'x': 800, 'y': 8, 'w': 60, 'h': 40}},
        ],
    }

    snapshot = adapter.snapshot(adapter.app)

    assert snapshot.app.pid == os.getpid()
    assert [field.id for field in snapshot.empty_fields] == ['query']
    assert [control.id for control in snapshot.pressables] == ['search']
    assert FILL_KEY in build_options(snapshot).criteria


def test_capture_adapter_preserves_browser_loading_state(tmp_path):
    adapter = BrowserCaptureAdapter(tmp_path, app_pid=os.getpid())
    adapter.rpc = lambda operation: {
        'title': 'Search results', 'width': 1280, 'height': 800,
        'controls': [], 'loading': True,
    }

    assert adapter.snapshot(adapter.app).loading is True
