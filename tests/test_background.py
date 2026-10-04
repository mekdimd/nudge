import os

from nudge import background


def test_child_args_drop_background_and_add_persistent():
    assert background.child_args(["--background", "--debug"]) == ["--debug", "--persistent"]
    assert background.child_args(["--background", "--persistent"]) == ["--persistent"]


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
