"""RemiX Duo V8.75: read-only Smaart and redirected Documents discovery.

No Smaart execution or audio calls. Smaart 8 and Smaart 9 are isolated:
only actual Windows file-version / trusted process inspection identifies
an edition; the presence of old Documents files alone never proves the
corresponding Smaart process is installed or running.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
import os
from pathlib import Path
import sys
import uuid


@dataclass(frozen=True)
class TraceInventory:
    edition: int
    folder: Path
    available: bool
    count: int
    filenames: tuple[str, ...]
    truncated: bool = False


@dataclass(frozen=True)
class SmaartInstallation:
    edition: int
    executable: Path
    origin: str


def known_documents() -> Path:
    """Current Windows KNOWNFOLDERID_Documents, including OneDrive relocation.

    HKCU User Shell Folders fallback is used if the shell API is unavailable.
    Avoid heuristically probing another user's Documents folder.
    """
    if sys.platform == "win32":
        try:
            import uuid
            class GUID(ctypes.Structure):
                _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                            ("Data3", ctypes.c_ushort),
                            ("Data4", ctypes.c_ubyte * 8)]
            # FOLDERID_Documents: FDD39AD0-238F-46AF-ADB4-6C85480369C7
            u = uuid.UUID("fdd39ad0-238f-46af-adb4-6c85480369c7")
            ident = GUID(u.fields[0], u.fields[1], u.fields[2],
                         (ctypes.c_ubyte * 8).from_buffer_copy(u.bytes[8:]))
            ptr = ctypes.c_wchar_p()
            shell = ctypes.WinDLL("shell32", use_last_error=True)
            shell.SHGetKnownFolderPath.argtypes = [
                ctypes.POINTER(GUID), ctypes.c_ulong, ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_wchar_p)
            ]
            shell.SHGetKnownFolderPath.restype = ctypes.c_long
            hresult = shell.SHGetKnownFolderPath(ctypes.byref(ident), 0, None,
                                                 ctypes.byref(ptr))
            if hresult == 0 and ptr.value:
                path = Path(ptr.value)
                ctypes.WinDLL("ole32").CoTaskMemFree.argtypes = [ctypes.c_void_p]
                ctypes.WinDLL("ole32").CoTaskMemFree(ctypes.cast(ptr, ctypes.c_void_p))
                return path
            if ptr.value:
                ctypes.WinDLL("ole32").CoTaskMemFree(ctypes.cast(ptr, ctypes.c_void_p))
        except (OSError, ValueError, AttributeError, TypeError):
            pass
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
                value, _ = winreg.QueryValueEx(key, "Personal")
                if isinstance(value, str) and value.strip():
                    return Path(os.path.expandvars(value))
        except (OSError, ImportError):
            pass
    return Path.home() / "Documents"


TRF_SUFFIX = {
    8: Path("Smaart v8") / "Traces" / "Transfer Function" / "Session Data",
    9: Path("Smaart Suite") / "Data" / "Transfer Function" / "Session Data",
}
CONFIG_SUFFIX = {
    8: Path("Smaart v8") / "Config" / "SmaartConfig.xml",
    9: Path("Smaart Suite") / "Config" / "SmaartConfig.xml",
}


def trace_folder(edition: int, documents: Path | None = None) -> Path | None:
    return ((known_documents() if documents is None else Path(documents)) /
            TRF_SUFFIX[edition]) if edition in TRF_SUFFIX else None


def config_file(edition: int, documents: Path | None = None) -> Path | None:
    return ((known_documents() if documents is None else Path(documents)) /
            CONFIG_SUFFIX[edition]) if edition in CONFIG_SUFFIX else None


def scan_traces(edition: int, *, documents: Path | None = None,
                max_names: int = 1000) -> TraceInventory:
    """Read-only shallow file catalog. No UI Data Bar tick guesses.

    Actual TF values are loaded exclusively through existing trf_core.read_trf
    after the user selects files or verified Smaart Data Bar mapping is known.
    """
    if not 1 <= max_names <= 10000:
        raise ValueError("INVALID_MAX_NAMES")
    folder = trace_folder(edition, documents)
    if folder is None:
        return TraceInventory(edition, Path(), False, 0, ())
    if not folder.is_dir():
        return TraceInventory(edition, folder, False, 0, ())
    try:
        found: list[tuple[int, str]] = []
        total = 0
        with os.scandir(folder) as it:
            for entry in it:
                if not entry.name.lower().endswith(".trf") or not entry.is_file(follow_symlinks=False):
                    continue
                total += 1
                if len(found) < max_names:
                    try:
                        stamp = entry.stat(follow_symlinks=False).st_mtime_ns
                    except OSError:
                        stamp = 0
                    found.append((stamp, entry.name))
        found.sort(key=lambda item: (-item[0], item[1].casefold()))
        return TraceInventory(edition, folder, True, total,
                              tuple(name for _, name in found),
                              total > max_names)
    except OSError:
        return TraceInventory(edition, folder, False, 0, ())


def _validated_exe(path: Path, edition: int) -> bool:
    if edition not in (8, 9):
        return False
    if path.name.lower() not in ("smaart.exe", "smaart suite.exe"):
        return False
    if not path.is_file():
        return False
    from smaart_api_v3_v4_readonly_v873 import _version_from_windows_file
    return _version_from_windows_file(str(path)) == edition


def installed_versions() -> tuple[SmaartInstallation, ...]:
    """Uninstall registry + known Program Files; never execute located binary."""
    if sys.platform != "win32":
        return ()
    candidates: list[tuple[Path, str]] = []
    try:
        import winreg
        root = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        views = (0, getattr(winreg, "KEY_WOW64_64KEY", 0),
                 getattr(winreg, "KEY_WOW64_32KEY", 0))
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for view in views:
                try:
                    with winreg.OpenKey(hive, root, 0, winreg.KEY_READ | view) as parent:
                        count = winreg.QueryInfoKey(parent)[0]
                        for index in range(count):
                            try:
                                subkey = winreg.EnumKey(parent, index)
                                with winreg.OpenKey(parent, subkey) as entry:
                                    name = str(winreg.QueryValueEx(entry, "DisplayName")[0])
                                    if "smaart" not in name.lower():
                                        continue
                                    try:
                                        base = winreg.QueryValueEx(entry, "InstallLocation")[0]
                                    except OSError:
                                        continue
                                    if not isinstance(base, str) or not base.strip():
                                        continue
                                    for exe in ("Smaart.exe", "Smaart Suite.exe"):
                                        candidates.append((Path(base) / exe, "UNINSTALL_REGISTRY"))
                            except (OSError, ValueError):
                                continue
                except OSError:
                    continue
    except ImportError:
        pass
    for var in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(var)
        if not base:
            continue
        root = Path(base)
        for pattern in ("Smaart*/Smaart.exe", "Smaart*/Smaart Suite.exe",
                        "Rational Acoustics*/Smaart*/Smaart.exe",
                        "Rational Acoustics*/Smaart*/Smaart Suite.exe"):
            try:
                candidates.extend((p, "PROGRAM_FILES") for p in root.glob(pattern))
            except OSError:
                pass
    found = {}
    for path, origin in candidates:
        try:
            resolved = path.resolve()
            for edition in (8, 9):
                if _validated_exe(resolved, edition):
                    found[(edition, str(resolved).lower())] = SmaartInstallation(
                        edition, resolved, origin)
        except (OSError, ValueError):
            continue
    return tuple(sorted(found.values(),
                        key=lambda item: (item.edition, str(item.executable).lower())))


def running_versions() -> tuple[tuple[int, int, float], ...]:
    """(edition, pid, process_creation_time) from verified Smaart processes."""
    try:
        import psutil
        from smaart_api_v3_v4_readonly_v873 import inspect_smaart_pid
        found = []
        for proc in psutil.process_iter(["pid", "name"]):
            if (proc.info.get("name") or "").lower() not in ("smaart.exe", "smaart suite.exe"):
                continue
            identity = inspect_smaart_pid(proc.info["pid"])
            if identity is not None:
                found.append((identity.edition, identity.pid, identity.created_at))
        return tuple(sorted(found))
    except (ImportError, OSError):
        return ()
