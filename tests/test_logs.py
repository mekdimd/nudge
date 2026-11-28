from __future__ import annotations

import threading
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from nudge.core.jev import JevClient, JevError
from nudge.core.loop import NudgeLoop
from nudge.core.models import AppRef
from nudge.core.writer import Writer, WriterError
from nudge.logs import REDACTED, RotatingLogStream, log_files, redact_secrets
from nudge.platform.fake import FakeAdapter
from nudge.ui.voice import Voice


def test_rotating_log_bounds_file_size_and_backup_count(tmp_path):
    path = tmp_path / "nudge.log"
    stream = RotatingLogStream(path, max_bytes=120, backup_count=2)
    for i in range(25):
        stream.write(f"entry-{i:02d}: " + ("x" * 35) + "\n")
    stream.flush()

    files = log_files(path)
    assert [f.name for f in files] == ["nudge.log", "nudge.log.1", "nudge.log.2"]
    for log_file in files:
        assert log_file.stat().st_size <= 120
    combined = "".join(f.read_text(encoding="utf-8") for f in files)
    assert "entry-24:" in path.read_text(encoding="utf-8")
    assert "entry-00:" not in combined


def test_rotating_log_with_zero_backups_keeps_only_active_file(tmp_path):
    path = tmp_path / "nudge.log"
    stream = RotatingLogStream(path, max_bytes=80, backup_count=0)
    for i in range(10):
        stream.write(f"line-{i:02d} " + ("a" * 25) + "\n")
    stream.flush()

    files = log_files(path)
    assert files == [path]
    assert path.stat().st_size <= 80
    assert "line-09" in path.read_text(encoding="utf-8")


def test_rotating_log_prunes_stale_extra_backups_and_rotates_oversized_existing_log(tmp_path):
    path = tmp_path / "nudge.log"
    path.write_text("old-data-" * 30, encoding="utf-8")
    (tmp_path / "nudge.log.4").write_text("stale-4", encoding="utf-8")
    (tmp_path / "nudge.log.9").write_text("stale-9", encoding="utf-8")

    stream = RotatingLogStream(path, max_bytes=100, backup_count=2)
    stream.write("fresh line\n")

    assert [f.name for f in log_files(path)] == ["nudge.log", "nudge.log.1"]
    assert path.read_text(encoding="utf-8") == "fresh line\n"
    assert not (tmp_path / "nudge.log.4").exists()
    assert not (tmp_path / "nudge.log.9").exists()


def test_rotating_log_handles_oversized_single_write_with_multibyte_utf8(tmp_path):
    path = tmp_path / "nudge.log"
    stream = RotatingLogStream(path, max_bytes=64, backup_count=2)
    stream.write(("▶ café " * 80) + "\n")
    stream.flush()

    files = log_files(path)
    assert len(files) == 3
    for log_file in files:
        assert log_file.stat().st_size <= 64
        log_file.read_text(encoding="utf-8")  # valid UTF-8 on every chunk boundary


def test_deleting_log_files_while_active_recreates_fresh_log(tmp_path):
    path = tmp_path / "nudge.log"
    stream = RotatingLogStream(path, max_bytes=100, backup_count=2)
    stream.write("before clear\n")
    for log_file in log_files(path):
        log_file.unlink()
    assert log_files(path) == []

    stream.write("after clear\n")
    assert log_files(path) == [path]
    assert path.read_text(encoding="utf-8") == "after clear\n"


def test_rotating_log_is_thread_safe(tmp_path):
    path = tmp_path / "nudge.log"
    stream = RotatingLogStream(path, max_bytes=200, backup_count=2)
    errors = []

    def worker(worker_id: int) -> None:
        try:
            for i in range(20):
                stream.write(f"w{worker_id}-{i:02d}\n")
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    stream.flush()

    assert errors == []
    files = log_files(path)
    assert len(files) <= 3
    for log_file in files:
        assert log_file.stat().st_size <= 200


def test_redact_secrets_strips_env_keys_headers_urls_and_prefixes(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "ts_live_secret_987654")
    monkeypatch.setenv("GEMINI_API_KEY", "gem-secret+value/123")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el_secret_abcdef123456")

    sample = (
        "env TYPESAFE_API_KEY=ts_live_secret_987654 "
        "bare ts_live_secret_987654 "
        "url https://example.test/v1?key=gem-secret%2Bvalue%2F123&other=1 "
        "auth Authorization: Bearer some_bearer_token_12345 "
        "xi xi-api-key: el_secret_abcdef123456 "
        "google AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz "
        "sk sk_live_0123456789abcdef0123"
    )
    cleaned = redact_secrets(sample)
    for forbidden in (
        "ts_live_secret_987654",
        "gem-secret+value/123",
        "gem-secret%2Bvalue%2F123",
        "el_secret_abcdef123456",
        "some_bearer_token_12345",
        "AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz",
        "sk_live_0123456789abcdef0123",
    ):
        assert forbidden not in cleaned
    assert REDACTED in cleaned
    assert "other=1" in cleaned


def test_redact_secrets_preserves_normal_nudge_output():
    lines = [
        "Starting Nudge 0.1.0",
        "UI stub ready; keep_running=True",
        "TYPESAFE_API_KEY: missing",
        "  Jev       Picked “Settings”  92% · 130 ms",
        "  Chrome    Opened “https://www.youtube.com/results?search_query=pivot+tables”",
    ]
    for line in lines:
        assert redact_secrets(line) == line


def test_rotating_log_redacts_secrets_across_split_writes(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "super-secret-ts-key")
    path = tmp_path / "nudge.log"
    stream = RotatingLogStream(path, max_bytes=1024, backup_count=1)
    print("Authorization:", "Bearer", "other-bearer-token-999", file=stream)
    print("key:", "super-secret-ts-key", file=stream, flush=True)

    text = path.read_text(encoding="utf-8")
    assert "super-secret-ts-key" not in text
    assert "other-bearer-token-999" not in text
    assert REDACTED in text


def test_jev_client_redacts_api_key_in_http_and_status_errors():
    secret = "ts_secret_jev_token_42"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(401, text=f"Invalid key {secret} in Authorization: Bearer {secret}")
    )
    client = JevClient(secret, client=httpx.Client(transport=transport))
    with pytest.raises(JevError) as exc_info:
        client.ask({}, {"pick": {"type": "choice", "criteria": {"a": "A"}}})
    assert secret not in str(exc_info.value)
    assert REDACTED in str(exc_info.value)

    def boom(request):
        raise httpx.ConnectError(f"failed with {secret}", request=request)

    failing = JevClient(secret, client=httpx.Client(transport=httpx.MockTransport(boom)))
    with pytest.raises(JevError) as exc_info:
        failing.ask({}, {"pick": {"type": "choice", "criteria": {"a": "A"}}})
    assert secret not in str(exc_info.value)


def test_writer_redacts_api_key_in_errors():
    secret = "AIzaSySecretGeminiKeyForTesting1234"
    writer = Writer.__new__(Writer)
    writer._api_key = secret
    writer.model = "gemini-test"
    writer._client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=Mock(side_effect=RuntimeError(f"Request failed for key={secret}"))
        )
    )
    with pytest.raises(WriterError) as exc_info:
        writer.url("open example")
    assert secret not in str(exc_info.value)
    assert REDACTED in str(exc_info.value)


def test_loop_redacts_api_key_in_unexpected_exception_and_traceback(monkeypatch, capsys):
    secret = "el_secret_loop_crash_9999"
    monkeypatch.setenv("ELEVENLABS_API_KEY", secret)
    adapter = FakeAdapter.from_fixture("live_caption")
    adapter.activate_app = Mock(side_effect=RuntimeError(f"boom {secret}"))
    events = Mock()
    events.cancelled.return_value = False

    loop = NudgeLoop(adapter, Mock(), None, events)
    outcome = loop.run("secret goal", AppRef("Chrome", 1))

    assert not outcome.ok
    assert secret not in outcome.message
    assert REDACTED in outcome.message
    stderr = capsys.readouterr().err
    assert secret not in stderr
    assert REDACTED in stderr


def test_voice_redacts_api_key_in_error_messages(qapp, monkeypatch):
    secret = "el_secret_voice_token_77"
    voice = Voice(secret)
    seen = []
    voice._failed.connect(seen.append)

    class BadSocket:
        def __enter__(self):
            raise OSError(f"handshake failed with xi-api-key={secret}")

        def __exit__(self, *args):
            return False

    import websockets.sync.client as ws_client

    monkeypatch.setattr(ws_client, "connect", lambda *a, **k: BadSocket())
    voice._session(voice._audio, threading.Event())
    qapp.processEvents()
    assert seen
    assert secret not in seen[0]
    assert REDACTED in seen[0]
