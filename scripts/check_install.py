"""Check an installed release package without API calls or desktop actions."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree


def main() -> None:
    with tempfile.TemporaryDirectory(prefix='nudge-install-') as directory:
        os.chdir(directory)
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        os.environ.pop('TYPESAFE_API_KEY', None)
        os.environ.pop('WAKE_WORD', None)
        Path('.env').write_text('TYPESAFE_API_KEY=package-check\nWAKE_WORD=models/custom.onnx\n')

        from nudge.config import load_config
        from nudge.platform.fake import FakeAdapter
        from nudge.ui.icons import ASSETS

        for fixture in ('live_caption', 'gmail'):
            adapter = FakeAdapter.from_fixture(fixture)
            snapshot = adapter.snapshot(adapter.app)
            assert snapshot.controls, f'{fixture} has no controls'
            adapter.press(snapshot.controls[0])
            assert adapter.log, f'{fixture} did not record its action'
        for name in ('mic', 'mic-off', 'eye', 'typesafe', 'gemini', 'chevron'):
            ElementTree.parse(ASSETS / f'{name}.svg')
        config = load_config()
        assert config.typesafe_api_key == 'package-check', 'Installed configuration did not load .env'
        assert config.wake_word == str(Path.cwd() / 'models' / 'custom.onnx')
        subprocess.run([sys.executable, '-m', 'nudge', '--help'], check=True)
    print('Installed package passed the offline checks.')


if __name__ == '__main__':
    main()
