from docs.launch.scripts.capture_browser import BrowserCaptureAdapter
from nudge.core.actions import FILL_KEY, build_options


def test_capture_adapter_exposes_search_fields_for_drafting(tmp_path):
    adapter = BrowserCaptureAdapter(tmp_path)
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

    assert [field.id for field in snapshot.empty_fields] == ['query']
    assert [control.id for control in snapshot.pressables] == ['search']
    assert FILL_KEY in build_options(snapshot).criteria


def test_capture_adapter_preserves_browser_loading_state(tmp_path):
    adapter = BrowserCaptureAdapter(tmp_path)
    adapter.rpc = lambda operation: {
        'title': 'Search results', 'width': 1280, 'height': 800,
        'controls': [], 'loading': True,
    }

    assert adapter.snapshot(adapter.app).loading is True
