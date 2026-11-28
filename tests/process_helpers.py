"""Run the real CLI and process control with a small replacement for the UI."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from nudge import background

STUB = '''
import os
import sys
import time
import threading
import types
from pathlib import Path
from nudge import background, logs

background.STATE = Path(os.environ['NUDGE_TEST_STATE'])
if os.environ.get('NUDGE_TEST_LOG_MAX_BYTES'):
    logs.MAX_LOG_BYTES = int(os.environ['NUDGE_TEST_LOG_MAX_BYTES'])
if os.environ.get('NUDGE_TEST_LOG_BACKUPS'):
    logs.LOG_BACKUPS = int(os.environ['NUDGE_TEST_LOG_BACKUPS'])
if os.environ.get('NUDGE_TEST_PUBLISH_GATE'):
    original_init = background.Instance.__init__
    def delayed_init(self, fd):
        root = Path(os.environ['NUDGE_TEST_ROOT'])
        (root / 'locked').touch()
        while not (root / 'publish').exists():
            time.sleep(0.01)
        original_init(self, fd)
    background.Instance.__init__ = delayed_init

def run(args, owner, startup=None):
    root = Path(os.environ['NUDGE_TEST_ROOT'])
    with (root / 'initialized').open('a') as log:
        log.write(str(os.getpid()) + '\\n')
    while os.environ.get('NUDGE_TEST_GATE') and not (root / 'continue').exists():
        time.sleep(0.01)
    if os.environ.get('NUDGE_TEST_FAIL_THREAD'):
        threading.Thread(target=lambda: time.sleep(60), daemon=False).start()
    if os.environ.get('NUDGE_TEST_FAIL'):
        raise RuntimeError('deliberate startup failure')
    if os.environ.get('NUDGE_TEST_LOG_LINES'):
        count = int(os.environ['NUDGE_TEST_LOG_LINES'])
        secret = os.environ.get('TYPESAFE_API_KEY', '')
        for index in range(count):
            print(f'log-line-{index:02d} secret={secret} ' + ('z' * 40), flush=True)
    print('UI stub ready; keep_running=' + str(args.keep_running) + ' detailed_logs=' + str(args.detailed_logs), flush=True)
    owner.mark_ready()
    if startup is not None:
        startup.ready()
    while not owner.stop_requested.wait(0.01):
        pass
    os._exit(0)

sys.modules['nudge.app'] = types.SimpleNamespace(run=run)
'''


class Processes:
    def __init__(self, root: Path):
        self.root = root
        self.children = []
        (root / 'sitecustomize.py').write_text(STUB)
        self.environment = {
            **os.environ,
            'PYTHONPATH': os.pathsep.join([str(root), str(Path(__file__).resolve().parents[1])]),
            'NUDGE_TEST_STATE': str(root / 'state'),
            'NUDGE_TEST_ROOT': str(root),
        }

    def start(self, flags=(), **environment):
        child = subprocess.Popen(
            [sys.executable, '-m', 'nudge', *flags], env={**self.environment, **environment},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self.children.append(child)
        return child

    def run(self, flags=(), **environment):
        child = self.start(flags, **environment)
        stdout, stderr = child.communicate(timeout=10)
        return subprocess.CompletedProcess(child.args, child.returncode, stdout, stderr)

    def wait_initialized(self, count=1):
        """Return the app PID. A Windows venv launcher has its own PID."""
        path = self.root / 'initialized'

        def initialized():
            if not path.exists():
                return None
            pids = path.read_text().splitlines()
            return int(pids[count - 1]) if len(pids) >= count else None

        return wait_for(initialized)

    def close(self):
        try:
            background.stop(timeout=2)
        finally:
            for child in self.children:
                if child.poll() is None:
                    child.kill()
                child.communicate(timeout=5)


def wait_for(predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.01)
    raise AssertionError('Timed out waiting for subprocess state')
