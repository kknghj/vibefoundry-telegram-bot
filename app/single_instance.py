from __future__ import annotations

import atexit
import os
import subprocess
from pathlib import Path

from app.config import ROOT_DIR

_BOT_CMD_MARKERS = ("app.main", "app/main.py", "app\\main.py")
_PYTHON_PROCESS_NAMES = {"python", "python3", "python.exe", "python3.exe"}


class AlreadyRunningError(RuntimeError):
    pass


def acquire_lock() -> Path:
    lock_path = ROOT_DIR / "data" / "bot.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        old_pid_text = lock_path.read_text(encoding="utf-8").strip()
        if old_pid_text.isdigit() and _is_bot_process_running(int(old_pid_text)):
            raise AlreadyRunningError(f"bot already running with pid {old_pid_text}")
        lock_path.unlink(missing_ok=True)
    lock_path.write_text(str(os.getpid()), encoding="utf-8")
    atexit.register(lambda: lock_path.unlink(missing_ok=True))
    return lock_path


def _is_bot_process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    process_info = _get_process_info(pid)
    if process_info is None:
        return False
    name, cmdline = process_info
    if not _is_python_process(name):
        return False
    return _cmdline_indicates_bot(cmdline)


def _is_python_process(name: str) -> bool:
    return name.lower() in _PYTHON_PROCESS_NAMES


def _cmdline_indicates_bot(cmdline: str) -> bool:
    lowered = cmdline.lower()
    return any(marker.lower() in lowered for marker in _BOT_CMD_MARKERS)


def _get_process_info(pid: int) -> tuple[str, str] | None:
    try:
        import psutil
    except ImportError:
        psutil = None

    if psutil is not None:
        return _get_process_info_psutil(psutil, pid)
    if os.name == "nt":
        return _get_process_info_windows(pid)
    return _get_process_info_posix(pid)


def _get_process_info_psutil(psutil, pid: int) -> tuple[str, str] | None:
    if not psutil.pid_exists(pid):
        return None
    try:
        proc = psutil.Process(pid)
        return proc.name(), " ".join(proc.cmdline())
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None


def _get_process_info_windows(pid: int) -> tuple[str, str] | None:
    script = (
        f"$p = Get-CimInstance Win32_Process -Filter \"ProcessId = {pid}\" -ErrorAction SilentlyContinue; "
        "if ($null -eq $p) { exit 1 }; "
        "Write-Output ($p.Name + '|' + $p.CommandLine)"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = result.stdout.strip()
    if result.returncode != 0 or not output or "|" not in output:
        return None
    name, cmdline = output.split("|", 1)
    if not name.strip():
        return None
    return name.strip(), cmdline.strip()


def _get_process_info_posix(pid: int) -> tuple[str, str] | None:
    try:
        os.kill(pid, 0)
    except OSError:
        return None
    cmdline_path = Path(f"/proc/{pid}/cmdline")
    comm_path = Path(f"/proc/{pid}/comm")
    try:
        cmdline = cmdline_path.read_bytes().replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
        name = comm_path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if not name:
        return None
    return name, cmdline
