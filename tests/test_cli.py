import os
import subprocess
import sys


def test_help_works_with_windows_output_encoding(tmp_path):
    environment = {**os.environ, 'PYTHONIOENCODING': 'cp1252:strict'}
    result = subprocess.run(
        [sys.executable, '-m', 'nudge', '--help'],
        cwd=tmp_path, env=environment, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode('cp1252')
    assert b'--persistent' in result.stdout
