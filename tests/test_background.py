import os
import subprocess
import sys
from unittest.mock import Mock

import pytest

from nudge import background


@pytest.mark.parametrize("flag", ["--background", "--detach"])
@pytest.mark.parametrize("keep_running", [[], ["--keep-running"]])
def test_child_args_drop_detached_flags_and_enable_keep_running(flag, keep_running):
    assert background.child_args([flag, "--debug", *keep_running]) == ["--debug", "--keep-running"]


def test_child_args_drop_both_detached_flags():
    assert background.child_args(["--background", "--detach"]) == ["--keep-running"]


@pytest.mark.parametrize("flag", ["--background", "--detach"])
def test_detach_launches_a_keep_running_child_with_file_logs(flag, tmp_path, monkeypatch):
    monkeypatch.setattr(background, "STATE", tmp_path)
    launch = Mock(return_value=Mock(pid=123))
    monkeypatch.setattr(subprocess, "Popen", launch)
    assert background.detach([flag, "--offline", "gmail"]) == 123
    argv = launch.call_args.args[0]
    assert argv == [sys.executable, "-m", "nudge", "--offline", "gmail", "--keep-running"]
    options = launch.call_args.kwargs
    assert options["stdin"] == subprocess.DEVNULL
    assert options["stderr"] == subprocess.STDOUT
    log = options["stdout"]
    try:
        assert log.name == str(background.log_path())
        assert log.mode == "a"
        if sys.platform == "win32":
            assert options["creationflags"] == subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            assert options["start_new_session"] is True
    finally:
        log.close()


def test_running_pid_reads_a_live_process(tmp_path, monkeypatch):
    monkeypatch.setattr(background, "STATE", tmp_path)
    assert background.running_pid() is None
    background.write_pid()
    assert background.running_pid() == os.getpid()
    background.clear_pid()
    assert background.running_pid() is None


def test_a_stale_pid_file_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(background, "STATE", tmp_path)
    (tmp_path / "nudge.pid").write_text("999999999")
    assert background.running_pid() is None


def test_clear_pid_leaves_another_instances_file_alone(tmp_path, monkeypatch):
    monkeypatch.setattr(background, "STATE", tmp_path)
    (tmp_path / "nudge.pid").write_text("1")
    background.clear_pid()
    assert (tmp_path / "nudge.pid").exists()
