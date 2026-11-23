"""RemiX Duo V8.75 per-user installer hook and Smaart/Documents scanner.

Installer can call --enable after copying Duo & watcher (unprivileged HKCU).
--disable cleanly removes only the registration made by this installation.
No installer automatically opens Smaart or takes over a soundcard.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

REGISTRY_NAME = "RemiXDuoSmaartCompanion"
RUN_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def install_dir() -> Path:
    return Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent


def watcher_command(directory: Path | None = None,
                    interpreter: Path | None = None) -> str | None:
    folder = install_dir() if directory is None else Path(directory)
    packaged = folder / "RemiXDuoSmaartWatcher.exe"
    if packaged.is_file():
        return subprocess.list2cmdline([str(packaged), "--watch"])
    # Source development only: Pythonw and source have to be present.
    watcher = folder / "smaart_autostart_v875.py"
    py = Path(sys.executable) if interpreter is None else Path(interpreter)
    windowless = py.with_name("pythonw.exe")
    if (not watcher.is_file() or
        py.name.lower() not in ("python.exe", "pythonw.exe") or
        not windowless.is_file()):
        return None
    return subprocess.list2cmdline([str(windowless), str(watcher), "--watch"])


def _reg_open(create: bool = False):
    import winreg
    if create:
        return winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_SUBKEY, 0,
                                  winreg.KEY_READ | winreg.KEY_WRITE)
    return winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_SUBKEY, 0,
                          winreg.KEY_READ | winreg.KEY_WRITE)


def registered_command() -> str | None:
    if sys.platform != "win32":
        return None
    try:
        import winreg
        with _reg_open() as key:
            value, typ = winreg.QueryValueEx(key, REGISTRY_NAME)
            return value if typ == winreg.REG_SZ and isinstance(value,str) else None
    except OSError:
        return None


def _owned_v887_startup(command: str | None) -> bool:
    """Only the confirmed RemiX V8.87 *source* watcher may be migrated."""
    if not isinstance(command,str):
        return False
    try:
        argv=[part.strip('"').replace("/","\\").casefold()
              for part in shlex.split(command,posix=False)]
    except ValueError:
        return False
    if len(argv)!=3 or argv[2]!="--watch":
        return False
    python,script,_=argv
    if not (len(python)>=3 and python[1:3]==":\\" and
            len(script)>=3 and script[1:3]==":\\"):
        return False
    return (python.endswith("\\pythonw.exe") and
            script.endswith("\\remix_auto_align_v6_dev\\windows_v8_87_mac_overlay_qa\\smaart_autostart_v875.py"))


def _backup_legacy_startup(command: str) -> Path:
    """Write an exclusive, durable rollback record BEFORE changing HKCU Run."""
    base=Path(os.environ.get("LOCALAPPDATA",str(Path.home()))) / "RemiXDuo" / "backups"
    base.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    dest=base/("startup_v887_before_migration_"+stamp+".json")
    record=dict(name=REGISTRY_NAME,subkey=RUN_SUBKEY,
                previous_command=command,
                recorded_utc=datetime.now(timezone.utc).isoformat(),
                action="migrate_exact_v887_source_to_installed_watcher")
    with dest.open("x",encoding="utf-8") as handle:
        json.dump(record,handle,ensure_ascii=False,indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    return dest


def configure_autostart(enable: bool) -> str:
    if sys.platform != "win32":
        return "WINDOWS_ONLY"
    expected = watcher_command()
    if expected is None:
        return "WATCHER_NOT_DEPLOYED"
    current = registered_command()
    if enable:
        if current == expected:
            return "ALREADY_ENABLED"
        migrating=bool(current is not None and _owned_v887_startup(current))
        if current is not None and not migrating:
            return "OTHER_INSTALL_OWNS_STARTUP_ENTRY"
        if migrating:
            try:
                _backup_legacy_startup(current)
            except (OSError, ValueError):
                return "LEGACY_BACKUP_FAILED"
        import winreg
        try:
            with _reg_open(create=True) as key:
                winreg.SetValueEx(key, REGISTRY_NAME, 0, winreg.REG_SZ, expected)
        except OSError:
            return "REGISTRY_WRITE_FAILED"
        return ("MIGRATED_OWN_V887_SOURCE_ENTRY" if migrating
                else "ENABLED_AT_NEXT_USER_LOGON")
    if current is None:
        return "ALREADY_DISABLED"
    if current != expected:
        return "OTHER_INSTALL_OWNS_STARTUP_ENTRY"
    try:
        import winreg
        with _reg_open() as key:
            winreg.DeleteValue(key, REGISTRY_NAME)
        return "DISABLED"
    except OSError:
        return "REGISTRY_WRITE_FAILED"


def cleanup_legacy_autostart() -> str:
    """Installer unconditional preflight; remove only proven V8.87 source Run."""
    if sys.platform!="win32":
        return "WINDOWS_ONLY"
    current=registered_command()
    if current is None:
        return "NO_LEGACY_ENTRY"
    if not _owned_v887_startup(current):
        return "FOREIGN_ENTRY_UNCHANGED"
    try:
        _backup_legacy_startup(current)
    except (OSError,ValueError):
        return "LEGACY_BACKUP_FAILED"
    import winreg
    try:
        with _reg_open() as key:
            latest,typ=winreg.QueryValueEx(key,REGISTRY_NAME)
            if typ!=winreg.REG_SZ or latest!=current:
                return "ENTRY_CHANGED_DURING_CLEANUP"
            winreg.DeleteValue(key,REGISTRY_NAME)
        return "REMOVED_OWN_V887_SOURCE_ENTRY"
    except OSError:
        return "REGISTRY_WRITE_FAILED"


def scan_installation(*, max_names=12) -> dict:
    from smaart_discovery_v875 import (
        known_documents, installed_versions, running_versions, scan_traces
    )
    reports = []
    for edition in (8, 9):
        inv = scan_traces(edition, max_names=max_names)
        reports.append(dict(edition=edition, trace_folder=str(inv.folder),
                            folder_exists=inv.available,
                            trace_count=inv.count,
                            sample_trace_names=inv.filenames,
                            truncated=inv.truncated))
    return dict(documents=str(known_documents()),
                installed=[dict(edition=x.edition, executable=str(x.executable),
                                detection=x.origin) for x in installed_versions()],
                running=[dict(edition=v,pid=pid) for (v,pid,_) in running_versions()],
                traces=reports, startup_enabled=registered_command()==watcher_command())


def main(argv=None):
    p=argparse.ArgumentParser(description="RemiX Duo / Smaart setup and trace scan")
    actions=p.add_mutually_exclusive_group(required=True)
    actions.add_argument("--enable", action="store_true",
                         help="Opt-in to user-login watcher; launches Duo on next Smaart start")
    actions.add_argument("--disable", action="store_true")
    actions.add_argument("--cleanup-legacy", action="store_true",
                         help="Back up/remove ONLY exact owned V8.87 source autostart")
    actions.add_argument("--status", action="store_true")
    actions.add_argument("--scan", action="store_true",
                         help="Read-only Smaart install and Documents TRF scan")
    p.add_argument("--start-now", action="store_true",
                   help="With --enable: begin watching Smaart immediately, no reboot")
    args=p.parse_args(argv)
    if args.start_now and not args.enable:
        p.error("--start-now requires --enable")
    if args.cleanup_legacy:
        result=cleanup_legacy_autostart()
        print(result)
        return 0 if result in ("NO_LEGACY_ENTRY","FOREIGN_ENTRY_UNCHANGED",
                               "REMOVED_OWN_V887_SOURCE_ENTRY") else 2
    if args.enable or args.disable:
        result=configure_autostart(args.enable)
        success=result in ("ENABLED_AT_NEXT_USER_LOGON","ALREADY_ENABLED",
                           "ALREADY_DISABLED","DISABLED",
                           "MIGRATED_OWN_V887_SOURCE_ENTRY")
        if result=="MIGRATED_OWN_V887_SOURCE_ENTRY":
            # Old source watcher will self-exit after Run changes.
            # Never auto-open Duo next to a possibly live old overlay.
            result+=" + NEXT_USER_LOGON_ONLY"
        elif success and args.enable and args.start_now:
            command=watcher_command()
            try:
                subprocess.Popen(command, cwd=str(install_dir()),
                                 creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),
                                 close_fds=True)
                result += " + WATCHER_STARTED_NOW"
            except (OSError, ValueError, TypeError):
                result += " + WATCHER_START_FAILED"
                success=False
        print(result)
        return 0 if success else 2
    if args.status:
        current=registered_command()
        expected=watcher_command()
        print(json.dumps(dict(
            enabled=bool(expected and current == expected),
            launcher_present=expected is not None,
            status="UNCONFIGURED" if current is None else
                   "CONFIGURED" if current == expected else "FOREIGN_ENTRY"
        )))
        return 0
    print(json.dumps(scan_installation(), ensure_ascii=False, indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
