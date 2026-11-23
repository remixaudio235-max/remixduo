"""V8.75 optional per-user Smaart companion auto-launch watcher.

Run at Windows user login via HKCU Run (installed by postinstall tool).
The watcher does NOT start Smaart, open its API, or touch sound devices.
It launches RemiX Duo once for each new verified Smaart process lifetime.
If user closes Duo while Smaart stays open, it will NOT reopen Duo.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import time


def installation_dir() -> Path:
    return Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent


def launch_command(install: Path | None = None,
                   interpreter: Path | None = None) -> list[str] | None:
    """Never launch unrecognized Smaart or arbitrary external commands."""
    directory = installation_dir() if install is None else Path(install)
    for exe_name in ("RemiXDuo.exe", "RemiXDuo_QA.exe"):
        exe = directory / exe_name
        if exe.is_file():
            return [str(exe)]
    script = directory / "overlay_v7.py"
    if not script.is_file():
        return None
    py = Path(sys.executable) if interpreter is None else Path(interpreter)
    if py.name.lower() not in ("python.exe", "pythonw.exe"):
        return None
    windowless = py.with_name("pythonw.exe")
    return [str(windowless if windowless.is_file() else py), str(script)]


def duo_running(install: Path | None = None) -> bool:
    try:
        import psutil
        directory = installation_dir() if install is None else Path(install)
        packaged = {str((directory / n).resolve()).casefold()
                    for n in ("RemiXDuo.exe", "RemiXDuo_QA.exe")}
        script = str((directory / "overlay_v7.py").resolve()).casefold()
        for proc in psutil.process_iter(["name", "exe", "cmdline"]):
            try:
                if str(proc.info.get("exe") or "").casefold() in packaged:
                    return True
                argv = proc.info.get("cmdline") or []
                if any(str(arg).casefold() == script for arg in argv[1:]):
                    return True
                # V8.116: `python overlay_v7.py` started inside the install
                # dir is the same Duo; never open a second overlay next to it.
                if any(Path(str(arg)).name.casefold() == "overlay_v7.py"
                       and not Path(str(arg)).is_absolute() for arg in argv[1:]):
                    cwd = Path(proc.cwd()).resolve()
                    if str(cwd / "overlay_v7.py").casefold() == script:
                        return True
            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                continue
    except (ImportError, OSError):
        # Fail closed rather than accidentally opening many Duo instances.
        return True
    return False


class EpisodeWatcher:
    """One automatic launch per Smaart process PID+creation timestamp."""
    def __init__(self, *, running=None, is_duo_running=None, launch=None,
                 crashed=None):
        from smaart_discovery_v875 import running_versions
        self.running = running or running_versions
        self.is_duo_running = is_duo_running or duo_running
        self.launch = launch or self._launch
        if crashed is None:
            from duo_lifecycle_v8142 import previous_exit_unclean
            crashed=previous_exit_unclean
        self.crashed=crashed
        self.seen: set[tuple[int, int, float]] = set()
        self.restart_attempted:set[tuple[int,int,float]]=set()
        self.duo_seen_running:set[tuple[int,int,float]]=set()
        self.launches = 0

    def poll(self) -> bool:
        current = set(self.running())
        self.seen.intersection_update(current)
        unobserved = sorted(current - self.seen)
        running=self.is_duo_running()
        if running:self.duo_seen_running.update(current)
        if not unobserved:
            if (current and not running and current.issubset(self.duo_seen_running)
                    and self.crashed() and
                    not current.issubset(self.restart_attempted)):
                self.restart_attempted.update(current)
                try:launched=bool(self.launch())
                except Exception:launched=False
                if launched:self.launches+=1
                return launched
            return False
        # Mark *all* current Smaart process episodes before attempting launch,
        # including when Duo was already open, to prevent unwanted relaunch.
        self.seen.update(current)
        if running:
            return False
        # One Duo supports the active Smaart version and already switches
        # trace paths on target change; never open parallel Duo instances.
        try:
            launched = bool(self.launch())
        except Exception:
            launched = False
        if launched:
            self.launches += 1
        return launched

    @staticmethod
    def _launch() -> bool:
        command = launch_command()
        if command is None:
            return False
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(command, cwd=str(installation_dir()),
                         creationflags=flags, close_fds=True)
        return True


def _mutex():
    if sys.platform != "win32":
        return object()
    import ctypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                    ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel.CreateMutexW(None, 0, r"Local\RemiXDuoSmaartAutoStartV875")
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        kernel.CloseHandle(handle)
        return None
    return handle


def run_forever(interval: float = 3.0):
    if not 1 <= interval <= 30:
        raise ValueError("INVALID_INTERVAL")
    log = _watch_log()
    guard = _mutex()
    if guard is None:
        log("exit: another watcher already running")
        return 0
    log("start")
    watcher = EpisodeWatcher()
    from smaart_postinstall_v875 import registered_command, watcher_command
    while True:
        # Stop on uninstall/disable: no orphan background watcher left behind.
        registered, expected = registered_command(), watcher_command()
        if registered != expected:
            log(f"exit: registry {registered!r} != {expected!r}")
            return 0
        try:
            if watcher.poll():
                log(f"launched Duo for Smaart episodes {sorted(watcher.seen)}")
        except Exception as exc:
            log(f"poll error {type(exc).__name__}: {exc}")  # keep watching
        time.sleep(interval)


def _watch_log():
    """V8.120: the logon watcher exited silently after a reboot; keep a log."""
    import os
    folder = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "RemiXDuo" / "logs"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "watcher.log"
        if path.exists() and path.stat().st_size > 500_000:
            path.unlink()
    except OSError:
        return lambda message: None
    def write(message):
        try:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} pid={os.getpid()} {message}\n")
        except OSError:
            pass
    return write


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true",
                        help="Opt-in per-user launcher at Windows login")
    parser.add_argument("--one-shot", action="store_true",
                        help="Check once, never keep background process")
    args = parser.parse_args(argv)
    if args.watch:
        return run_forever()
    if args.one_shot:
        watcher = EpisodeWatcher()
        print("DUO_LAUNCHED" if watcher.poll() else "DUO_NOT_LAUNCHED")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
