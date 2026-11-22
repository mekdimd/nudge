import os

import pytest

from nudge import background
from process_helpers import Processes, wait_for

MODES = [[], ["--keep-running"], ["--background"], ["--detach"],
         ["--keep-running", "--background"], ["--background", "--keep-running"]]


@pytest.mark.parametrize("flag", ["--background", "--detach"])
@pytest.mark.parametrize("keep_running", [[], ["--keep-running"]])
def test_child_args_enable_keep_running(flag, keep_running):
    assert background.child_args([flag, "--debug", *keep_running]) == ["--debug", "--keep-running"]


def test_child_args_drop_both_detached_flags():
    assert background.child_args(["--background", "--detach"]) == ["--keep-running"]


@pytest.fixture
def processes(tmp_path, monkeypatch):
    monkeypatch.setattr(background, "STATE", tmp_path / "state")
    fixture = Processes(tmp_path)
    yield fixture
    fixture.close()


@pytest.mark.parametrize("first", MODES)
@pytest.mark.parametrize("second", MODES)
@pytest.mark.parametrize("starting", [True, False])
def test_all_launch_modes_share_one_owner(first, second, starting, processes):
    first_process = processes.start(first, NUDGE_TEST_GATE="1")
    processes.wait_initialized()
    if not starting:
        (processes.root / "continue").touch()
        wait_for(lambda: background.owner_status() and background.owner_status()["ready"])
    result = processes.run(second)
    assert result.returncode == 0, result.stderr
    assert "already running" in result.stdout
    assert len((processes.root / "initialized").read_text().splitlines()) == 1
    (processes.root / "continue").touch()
    if "--background" in first or "--detach" in first:
        stdout, stderr = first_process.communicate(timeout=5)
        assert first_process.returncode == 0, stderr
        assert "running in the background" in stdout
        assert "keep_running=True" in background.log_path().read_text()
    owner = background.running_pid()
    assert background.stop() == owner
    assert background.running_pid() is None
    assert processes.run(["--stop"]).returncode == 0


@pytest.mark.parametrize("mode", MODES)
def test_stop_reaches_owner_during_initialization(mode, processes):
    child = processes.start(mode, NUDGE_TEST_GATE="1")
    processes.wait_initialized()
    result = processes.run(["--background", "--stop"])
    assert result.returncode == 0, result.stderr
    assert "Stopped Nudge" in result.stdout
    assert background.running_pid() is None
    child.communicate(timeout=5)
    if "--background" in mode or "--detach" in mode:
        assert child.returncode != 0


@pytest.mark.parametrize("mode", [["--background"], ["--detach"]])
def test_detached_launcher_waits_for_readiness(mode, processes):
    launcher = processes.start(mode, NUDGE_TEST_GATE="1")
    processes.wait_initialized()
    assert launcher.poll() is None
    assert not background.owner_status()["ready"]
    (processes.root / "continue").touch()
    stdout, stderr = launcher.communicate(timeout=5)
    assert launcher.returncode == 0, stderr
    assert "running in the background" in stdout
    assert stdout.index("Ready in") < stdout.index("running in the background")
    assert background.owner_status()["ready"]


@pytest.mark.parametrize("mode", [[], ["--background"], ["--detach"]])
def test_startup_failure_reports_failure_and_releases_ownership(mode, processes):
    result = processes.run(mode, NUDGE_TEST_FAIL="1")
    assert result.returncode != 0
    assert "running in the background" not in result.stdout
    assert "startup" in result.stderr.lower() or "deliberate startup failure" in result.stderr
    assert background.running_pid() is None
    if mode:
        assert "deliberate startup failure" in background.log_path().read_text()
    recovered = background.acquire()
    assert recovered is not None
    recovered.close()


@pytest.mark.parametrize("mode", [[], ["--background"]])
def test_redirected_startup_prints_plain_steps_and_keeps_errors_visible(mode, processes):
    result = processes.run(mode, NUDGE_TEST_FAIL="1")
    assert result.returncode == 1
    assert result.stdout.startswith("Starting Nudge ")
    assert "\x1b[" not in result.stdout + result.stderr
    child = background.log_path().read_text() if mode else result.stdout + result.stderr
    assert "  Loading Qt and Nudge modules..." in child
    assert "Startup failed while loading Qt and Nudge modules." in child
    assert "RuntimeError: deliberate startup failure" in child
    if mode:
        assert "Startup failed while waiting for the background process to start." in result.stderr


def test_crash_releases_lock_and_allows_restart(processes):
    child = processes.start([], NUDGE_TEST_GATE="1")
    processes.wait_initialized()
    child.kill()
    child.communicate(timeout=5)
    assert background.running_pid() is None
    (processes.root / "continue").touch()
    processes.start(["--keep-running"])
    replacement_pid = processes.wait_initialized(count=2)
    wait_for(lambda: background.owner_status() and background.owner_status()["ready"])
    assert background.running_pid() == replacement_pid


def test_lock_is_atomic_and_can_be_reacquired(tmp_path, monkeypatch):
    monkeypatch.setattr(background, "STATE", tmp_path)
    owner = background.acquire()
    assert owner is not None
    try:
        assert background.acquire() is None
        assert background.running_pid() == os.getpid()
    finally:
        owner.close()
    replacement = background.acquire()
    assert replacement is not None
    replacement.close()


@pytest.mark.parametrize("pid", ["999999999", str(os.getpid()), "0", "-1", "invalid"])
def test_stale_or_unrelated_pid_is_never_signaled(pid, tmp_path, monkeypatch):
    monkeypatch.setattr(background, "STATE", tmp_path)
    (tmp_path / "nudge.pid").write_text(pid)
    monkeypatch.setattr(os, "kill", lambda *args: pytest.fail("Signaled an unverified PID"))
    assert background.running_pid() is None
    assert background.stop() is None


def test_stop_timeout_reports_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(background, "STATE", tmp_path)
    owner = background.acquire()
    owner.mark_ready()
    try:
        with pytest.raises(background.ProcessError, match="exit"):
            background.stop(timeout=0.2)
        assert owner.stop_requested.is_set()
        assert background.running_pid() == os.getpid()
    finally:
        owner.close()


def test_simultaneous_launches_initialize_only_one_app(processes):
    first = processes.start(["--background"], NUDGE_TEST_GATE="1")
    second = processes.start(["--background"], NUDGE_TEST_GATE="1")
    processes.wait_initialized()
    (processes.root / "continue").touch()
    for child in (first, second):
        stdout, stderr = child.communicate(timeout=5)
        assert child.returncode == 0, stderr
        assert "running" in stdout
    assert len((processes.root / "initialized").read_text().splitlines()) == 1


def test_wrong_owner_token_cannot_stop_a_process(tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(background, "STATE", tmp_path)
    owner = background.acquire()
    owner.mark_ready()
    try:
        record = {**owner.record, "token": "0" * 64}
        (tmp_path / "nudge.owner").write_text(json.dumps(record))
        with pytest.raises(background.ProcessError, match="contact"):
            background.stop(timeout=0.2)
        assert not owner.stop_requested.is_set()
    finally:
        owner.close()


def test_startup_timeout_kills_only_the_launched_child(processes, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", processes.environment["PYTHONPATH"])
    monkeypatch.setenv("NUDGE_TEST_STATE", processes.environment["NUDGE_TEST_STATE"])
    monkeypatch.setenv("NUDGE_TEST_ROOT", processes.environment["NUDGE_TEST_ROOT"])
    monkeypatch.setenv("NUDGE_TEST_GATE", "1")
    with pytest.raises(background.ProcessError, match="timed out"):
        background.detach(["--background"], timeout=0.5)
    assert background.running_pid() is None


def test_startup_failure_exits_even_with_an_initialized_worker(processes):
    result = processes.run([], NUDGE_TEST_FAIL="1", NUDGE_TEST_FAIL_THREAD="1")
    assert result.returncode != 0
    assert background.running_pid() is None


def test_transient_lock_contention_does_not_skip_initialization(processes):
    import threading

    fd = background._try_lock()
    assert fd is not None
    release = threading.Timer(0.3, lambda: os.close(fd))
    release.start()
    try:
        child = processes.start([])
        processes.wait_initialized()
        assert child.poll() is None
    finally:
        release.join()


def test_duplicate_waits_for_owner_endpoint_publication(processes):
    import time

    processes.start([], NUDGE_TEST_PUBLISH_GATE="1")
    wait_for(lambda: (processes.root / "locked").exists())
    second = processes.start(["--background"])
    # Hold endpoint publication while the duplicate tries to acquire ownership.
    time.sleep(0.3)
    try:
        assert second.poll() is None
    finally:
        (processes.root / "publish").touch()
    stdout, stderr = second.communicate(timeout=5)
    assert second.returncode == 0, stderr
    assert "running" in stdout
    first_pid = processes.wait_initialized()
    assert len((processes.root / "initialized").read_text().splitlines()) == 1
    assert background.running_pid() == first_pid


def test_detach_checks_child_exit_before_observing_owner(processes, monkeypatch):
    import subprocess

    processes.start([], NUDGE_TEST_PUBLISH_GATE="1")
    wait_for(lambda: (processes.root / "locked").exists())
    for key in ("PYTHONPATH", "NUDGE_TEST_STATE", "NUDGE_TEST_ROOT"):
        monkeypatch.setenv(key, processes.environment[key])
    real_launch = subprocess.Popen
    children = []

    def launch(*args, **kwargs):
        child = real_launch(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", launch)
    real_status = background.owner_status
    observed = False

    def observe_status():
        nonlocal observed
        status = real_status()
        if status is None and not observed:
            observed = True
            (processes.root / "publish").touch()
            wait_for(lambda: real_status() and real_status()["ready"])
            wait_for(lambda: children[0].poll() is not None)
        return status

    monkeypatch.setattr(background, "owner_status", observe_status)
    owner_pid = background.detach(["--background"], timeout=5)
    assert owner_pid == processes.wait_initialized()
    assert children[0].returncode == 0
