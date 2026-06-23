from __future__ import annotations

import os
import shutil
import uuid

import pytest

from app.config import ROOT_DIR
from app.single_instance import AlreadyRunningError, acquire_lock


@pytest.fixture()
def lock_dir(monkeypatch):
    test_root = ROOT_DIR / ".pytest_tmp" / f"single_instance_{uuid.uuid4().hex}"
    test_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("app.single_instance.ROOT_DIR", test_root)
    yield test_root / "data"
    shutil.rmtree(test_root, ignore_errors=True)


def test_acquire_lock_creates_lock_file(lock_dir, monkeypatch):
    monkeypatch.setattr("app.single_instance._is_bot_process_running", lambda pid: False)

    lock_path = acquire_lock()

    assert lock_path == lock_dir / "bot.lock"
    assert lock_path.read_text(encoding="utf-8") == str(os.getpid())


def test_acquire_lock_removes_stale_lock_for_missing_process(lock_dir, monkeypatch):
    lock_dir.mkdir(parents=True)
    stale_lock = lock_dir / "bot.lock"
    stale_lock.write_text("42264", encoding="utf-8")
    monkeypatch.setattr("app.single_instance._is_bot_process_running", lambda pid: False)

    lock_path = acquire_lock()

    assert lock_path.exists()
    assert lock_path.read_text(encoding="utf-8") == str(os.getpid())


def test_acquire_lock_removes_invalid_lock_content(lock_dir, monkeypatch):
    lock_dir.mkdir(parents=True)
    stale_lock = lock_dir / "bot.lock"
    stale_lock.write_text("", encoding="utf-8")
    monkeypatch.setattr("app.single_instance._is_bot_process_running", lambda pid: False)

    lock_path = acquire_lock()

    assert lock_path.read_text(encoding="utf-8") == str(os.getpid())


def test_acquire_lock_removes_non_numeric_lock_content(lock_dir, monkeypatch):
    lock_dir.mkdir(parents=True)
    stale_lock = lock_dir / "bot.lock"
    stale_lock.write_text("not-a-pid", encoding="utf-8")
    monkeypatch.setattr("app.single_instance._is_bot_process_running", lambda pid: False)

    lock_path = acquire_lock()

    assert lock_path.read_text(encoding="utf-8") == str(os.getpid())


def test_acquire_lock_removes_lock_when_pid_is_not_bot(lock_dir, monkeypatch):
    lock_dir.mkdir(parents=True)
    stale_lock = lock_dir / "bot.lock"
    stale_lock.write_text("12345", encoding="utf-8")
    monkeypatch.setattr("app.single_instance._is_bot_process_running", lambda pid: False)

    lock_path = acquire_lock()

    assert lock_path.read_text(encoding="utf-8") == str(os.getpid())


def test_acquire_lock_raises_when_bot_already_running(lock_dir, monkeypatch):
    lock_dir.mkdir(parents=True)
    stale_lock = lock_dir / "bot.lock"
    stale_lock.write_text("42264", encoding="utf-8")
    monkeypatch.setattr("app.single_instance._is_bot_process_running", lambda pid: pid == 42264)

    with pytest.raises(AlreadyRunningError, match="bot already running with pid 42264"):
        acquire_lock()


def test_is_bot_process_running_requires_python_and_bot_cmdline(monkeypatch):
    from app.single_instance import _cmdline_indicates_bot, _is_bot_process_running, _is_python_process

    assert _is_python_process("python.exe")
    assert _cmdline_indicates_bot("python -m app.main")
    assert not _cmdline_indicates_bot("python -m pytest")

    monkeypatch.setattr(
        "app.single_instance._get_process_info",
        lambda pid: ("python.exe", "python -m app.main") if pid == 99 else None,
    )
    assert _is_bot_process_running(99) is True

    monkeypatch.setattr(
        "app.single_instance._get_process_info",
        lambda pid: ("notepad.exe", "python -m app.main"),
    )
    assert _is_bot_process_running(99) is False

    monkeypatch.setattr(
        "app.single_instance._get_process_info",
        lambda pid: ("python.exe", "python -m pytest"),
    )
    assert _is_bot_process_running(99) is False

    monkeypatch.setattr("app.single_instance._get_process_info", lambda pid: None)
    assert _is_bot_process_running(99) is False
