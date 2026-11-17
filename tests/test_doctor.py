import sys
from types import SimpleNamespace

import pytest

from nudge import config


@pytest.fixture
def doctor_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, 'ROOT', tmp_path / 'site-packages')
    for key in ('TYPESAFE_API_KEY', 'GEMINI_API_KEY', 'ELEVENLABS_API_KEY', 'WAKE_THRESHOLD'):
        monkeypatch.setenv(key, '')
        monkeypatch.delenv(key)
    from nudge import doctor
    monkeypatch.setattr(doctor.sys, 'platform', 'win32')
    monkeypatch.setattr(doctor, 'find_spec', lambda name: object())
    return doctor


def test_doctor_reads_env_file_without_printing_secrets(doctor_env, tmp_path, capsys):
    (tmp_path / '.env').write_text(
        'TYPESAFE_API_KEY=private-typesafe\nGEMINI_API_KEY=private-gemini\n'
        'ELEVENLABS_API_KEY=private-voice\nWAKE_THRESHOLD=invalid-private-value\n'
    )
    assert doctor_env.run_doctor() == 0
    output = capsys.readouterr().out
    assert 'TYPESAFE_API_KEY: set' in output
    assert 'GEMINI_API_KEY: set' in output
    assert 'ELEVENLABS_API_KEY: set' in output
    assert 'private' not in output
    assert 'Accessibility: no global permission' in output
    assert 'Vision: dependencies installed' in output
    assert 'not checked' in output


def test_missing_required_key_fails_with_fix_and_optional_features_warn(doctor_env, monkeypatch, capsys):
    monkeypatch.setenv('TYPESAFE_API_KEY', '   ')
    monkeypatch.setattr(doctor_env, 'find_spec', lambda name: None if name == 'mss' else object())
    assert doctor_env.run_doctor() == 1
    output = capsys.readouterr().out
    assert 'TYPESAFE_API_KEY: missing' in output and 'Add TYPESAFE_API_KEY to .env' in output
    assert 'GEMINI_API_KEY: missing' in output and 'Add GEMINI_API_KEY to .env' in output
    assert 'ELEVENLABS_API_KEY: missing' in output and 'Add ELEVENLABS_API_KEY to .env' in output
    assert 'mss' in output and 'uv sync --frozen --extra vision' in output
    monkeypatch.setenv('TYPESAFE_API_KEY', 'test-key')
    assert doctor_env.run_doctor() == 0


@pytest.mark.parametrize('trusted', [True, False])
def test_mac_permissions_are_checked_without_requesting_access(doctor_env, monkeypatch, capsys, trusted):
    monkeypatch.setenv('TYPESAFE_API_KEY', 'test-key')
    monkeypatch.setattr(doctor_env.sys, 'platform', 'darwin')
    monkeypatch.setitem(sys.modules, 'ApplicationServices', SimpleNamespace(AXIsProcessTrusted=lambda: trusted))
    monkeypatch.setitem(sys.modules, 'Quartz', SimpleNamespace(CGPreflightScreenCaptureAccess=lambda: False))
    assert doctor_env.run_doctor() == (0 if trusted else 1)
    output = capsys.readouterr().out
    assert f'Accessibility: {"granted" if trusted else "missing"}' in output
    assert 'Screen Recording: missing' in output
    assert 'Privacy & Security > Screen Recording' in output
    if not trusted:
        assert 'Privacy & Security > Accessibility' in output


def test_missing_mac_bridge_reports_fix_and_continues(doctor_env, monkeypatch, capsys):
    monkeypatch.setattr(doctor_env.sys, 'platform', 'darwin')
    monkeypatch.setitem(sys.modules, 'ApplicationServices', None)
    monkeypatch.setitem(sys.modules, 'Quartz', None)
    assert doctor_env.run_doctor() == 1
    output = capsys.readouterr().out
    assert 'Accessibility: unable to check' in output
    assert 'uv sync --frozen' in output
    assert 'Vision:' in output


def test_unsupported_os_reports_fix(doctor_env, monkeypatch, capsys):
    monkeypatch.setattr(doctor_env.sys, 'platform', 'linux')
    assert doctor_env.run_doctor() == 1
    assert 'Use macOS or Windows' in capsys.readouterr().out
