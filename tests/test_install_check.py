import importlib.util
from pathlib import Path


def test_install_check_restores_directory_before_cleanup(monkeypatch, tmp_path):
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'check_install.py'
    spec = importlib.util.spec_from_file_location('check_install', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.chdir(tmp_path)
    for key in ('TYPESAFE_API_KEY', 'WAKE_WORD', 'QT_QPA_PLATFORM'):
        monkeypatch.setenv(key, '')
    module.main()
    assert Path.cwd() == tmp_path
