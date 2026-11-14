"""Capture the real Nudge loop through a browser RPC adapter for the launch film.

The host answers request.json with response.json after reading or acting in its
owned browser tab. This adapter is for recording, not a shipped platform backend.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import sys
import tempfile
import time

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QT_SCALE_FACTOR'] = '2'
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from PySide6.QtCore import QObject, QSettings, QTimer, Signal
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton
import nudge.__main__ as main
from nudge.core.jev import JevClient
from nudge.core.models import AppRef, Control, Rect, Snapshot
from nudge.core.writer import Writer
from nudge.ui.audio_settings import AudioSettings

ASSETS = Path(__file__).resolve().parents[1] / 'assets' / 'browser'


class RecordingHotkeys(QObject):
    summon = Signal()
    escape = Signal()


class BrowserCaptureAdapter:
    name = 'Browser recording harness'

    def __init__(self, directory):
        self.directory = directory
        self.app = AppRef(name='Google Chrome', pid=999999)
        self.sequence = 0
        self.address = False
        self.pending_url = ''

    def rpc(self, operation, **values):
        self.sequence += 1
        request = {'id': self.sequence, 'operation': operation, **values}
        temporary = self.directory / 'request.tmp'
        temporary.write_text(json.dumps(request))
        temporary.replace(self.directory / 'request.json')
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            response = self.directory / 'response.json'
            if response.exists():
                try:
                    reply = json.loads(response.read_text())
                except json.JSONDecodeError:
                    reply = {}
                if reply.get('id') == self.sequence:
                    if reply.get('error'):
                        raise RuntimeError(reply['error'])
                    return reply.get('value')
            time.sleep(.02)
        raise TimeoutError('The recording host did not answer ' + operation)

    def thread_context(self):
        return nullcontext()

    def permission_problem(self):
        return None

    def frontmost_app(self):
        return self.app

    def activate_app(self, app):
        pass

    def shell_controls(self, app):
        return []

    def snapshot(self, app):
        started = time.monotonic()
        page = self.rpc('snapshot')
        controls = []
        for item in page['controls']:
            bounds = item.pop('bounds')
            item['is_text_field'] = item['role'] in ('text field', 'search field', 'text area')
            controls.append(Control(**item, bounds=Rect(**bounds), ref=item['id']))
        return Snapshot(app=app, window_title=page['title'], controls=controls,
                        window_bounds=Rect(0, 0, page['width'], page['height']),
                        focused_id=page.get('focused'), loading=page.get('loading', False),
                        elapsed_ms=round((time.monotonic() - started) * 1000))

    def press(self, control):
        self.rpc('click', control_id=control.id, label=control.label,
                 center=control.bounds.center)

    def click(self, control, double=False):
        self.rpc('click', control_id=control.id, label=control.label,
                 center=control.bounds.center, count=2 if double else 1)

    def set_text(self, control, text):
        self.rpc('type', control_id=control.id, text=text, label=control.label,
                 center=control.bounds.center)

    def type_text(self, text):
        if self.address:
            self.pending_url = text
        else:
            self.rpc('type_focused', text=text)

    def scroll(self, direction, near, window):
        self.rpc('scroll', delta=550 if direction == 'down' else -550)

    def key(self, name):
        if name == 'address_bar':
            self.address = True
        elif name == 'enter' and self.address:
            self.rpc('navigate', url=self.pending_url)
            self.address = False
        else:
            self.rpc('key', name=name)


def main_capture():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', required=True)
    parser.add_argument('--goal', required=True)
    parser.add_argument('--rpc', type=Path, required=True)
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    args = parser.parse_args()
    load_dotenv(args.env_file)
    if not os.environ.get('TYPESAFE_API_KEY') or not os.environ.get('GEMINI_API_KEY'):
        raise SystemExit('The recording harness requires TypeSafe and Gemini keys.')
    args.rpc.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    qapp = QApplication([])
    main.Hotkeys = RecordingHotkeys
    class RecordingLoop(main.NudgeLoop):
        def __init__(self, *values, **options):
            options['settle_timeout'] = 15
            super().__init__(*values, **options)

    main.NudgeLoop = RecordingLoop
    adapter = BrowserCaptureAdapter(args.rpc)
    trace = {'case': args.case, 'goal': args.goal, 'prompts': [], 'outcome': None}
    started = time.monotonic()

    with tempfile.TemporaryDirectory(prefix='nudge-browser-') as temporary:
        audio = AudioSettings(QSettings(str(Path(temporary) / 'audio.ini'), QSettings.Format.IniFormat))
        audio.set_sounds_muted(True)
        app = main.Nudge(adapter, JevClient(os.environ['TYPESAFE_API_KEY']),
                         Writer(os.environ['GEMINI_API_KEY']), audio=audio)
        app.bar.input.setText(args.goal)
        app.bar.input.deselect()
        app.bar.input.clearFocus()

        def save(tag, widget=None):
            QApplication.processEvents()
            image = (widget or app.bar).grab().toImage()
            image.setDevicePixelRatio(1)
            path = ASSETS / (args.case + '-' + tag + '.png')
            assert image.save(str(path))
            return {'file': path.name, 'width': image.width(), 'height': image.height()}

        def prompt(kind):
            def capture_and_approve():
                record = {'kind': kind, 'at': round(time.monotonic() - started, 3),
                          'panel': save(kind, app.bar.panel), 'bar': save(kind + '-bar')}
                trace['prompts'].append(record)
                if kind == 'draft' and args.case == 'mail':
                    fields = app.bar.panel.findChildren(QLineEdit)
                    if len(fields) > 1:
                        fields[1].setText("Missing today's lecture")
                        record['edited'] = save('draft-edited', app.bar.panel)
                if kind == 'confirm':
                    trace['confirmed_before_action'] = True
                if kind in ('draft', 'url', 'confirm'):
                    QTimer.singleShot(900, lambda: app.bar.spoken('yes'))
                else:
                    app.stop()
            QTimer.singleShot(150, capture_and_approve)

        app.bridge.sig_draft.connect(lambda *_: prompt('draft'))
        app.bridge.sig_url.connect(lambda *_: prompt('url'))
        app.bridge.sig_confirm.connect(lambda *_: prompt('confirm'))
        app.bridge.sig_choose.connect(lambda *_: prompt('choice'))
        app.bridge.sig_ask.connect(lambda *_: prompt('ask'))
        app.bridge.sig_recover.connect(lambda *_: prompt('recover'))

        def finished(ok, message):
            trace['outcome'] = {'ok': ok, 'message': message}
            trace['done'] = save('done')
            (ASSETS / (args.case + '-trace.json')).write_text(json.dumps(trace, indent=2) + '\n')
            print(json.dumps({'finished': args.case, 'ok': ok}), flush=True)
            QTimer.singleShot(300, qapp.quit)

        app.bridge.sig_finished.connect(finished)
        QTimer.singleShot(300, lambda: trace.update(idle=save('idle')))
        QTimer.singleShot(700, lambda: app.start(args.goal))
        QTimer.singleShot(180000, app.stop)
        qapp.exec()
        if app.worker:
            app.worker.wait(5000)
        assert trace['outcome'] and trace['outcome']['ok'], trace['outcome']


if __name__ == '__main__':
    main_capture()
