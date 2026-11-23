"""V8.118: GUI-stall diagnostics for the windowless (pythonw) overlay.

Live 2026-11-11: after the user turned Duo off, SUM/LF-HF overlay windows
stayed painted over Chrome while the process stayed alive. Only refresh_
visibility() hides them and it always hides when Smaart is not foreground,
so the Qt GUI thread must have stopped ticking. pythonw had no log at all.

install(): send stdout/stderr to a rotating per-user log and arm
faulthandler.dump_traceback_later from a Qt heartbeat; if the GUI thread
stalls longer than `stall_s`, every thread's stack is appended to the log.
Diagnostics only: no behaviour change, nothing touches Smaart.
"""
from __future__ import annotations
import faulthandler,os,sys,time,traceback
from pathlib import Path

LOG_DIR=Path(os.environ.get("LOCALAPPDATA",str(Path.home())))/"RemiXDuo"/"logs"


def install_exception_boundary(log):
    """Keep an exception raised by a Qt callback from aborting Qt6/PyQt6.

    PyQt6 forwards an unhandled callback exception to ``sys.excepthook`` and
    then uses ``qFatal`` when the default hook returns.  In a windowed frozen
    build that appears as Qt6Core FAST_FAIL_FATAL_APP_EXIT with no traceback.
    The GUI must survive; the complete exception remains available in the
    per-user diagnostics log for the specific control to recover from.
    """
    def report(exc_type,exc_value,exc_tb):
        try:
            log.write("\nV8154_QT_CALLBACK_EXCEPTION\n")
            traceback.print_exception(exc_type,exc_value,exc_tb,file=log)
            log.flush()
        except Exception:
            pass  # an error reporter must never become the second exception
    sys.excepthook=report
    return report


def log_path(directory=None):
    return Path(directory or LOG_DIR)/"overlay.log"


def _rotate(path,keep_bytes=2_000_000):
    try:
        if path.exists() and path.stat().st_size>keep_bytes:
            old=path.with_suffix(".log.1")
            if old.exists():old.unlink()
            path.rename(old)
    except OSError:
        pass


def configure_unicode_output(log,*,redirect=True):
    """Safe UTF-8 destination for GUI diagnostics, even with attached TTY.

    Never change safety gates, trace data or application locale. In a frozen
    application every print goes to the existing UTF-8 log; in a developer
    terminal, preserve interactive output but force an encodable stream.
    """
    if not redirect:
        return
    if getattr(sys,"frozen",False):
        sys.stdout=log
        sys.stderr=log
        return
    for name in ("stdout","stderr"):
        stream=getattr(sys,name,None)
        if stream is None:
            setattr(sys,name,log)
            continue
        try:
            interactive=bool(stream.isatty())
        except (AttributeError,ValueError,OSError):
            interactive=False
        if not interactive:
            setattr(sys,name,log)
            continue
        try:
            stream.reconfigure(encoding="utf-8",errors="backslashreplace")
        except (AttributeError,ValueError,OSError):
            # Unknown console adapter: never risk a cp1252 callback crash.
            setattr(sys,name,log)


def install(app,*,stall_s=5.0,directory=None,redirect=True):
    from PyQt6.QtCore import QTimer
    path=log_path(directory)
    path.parent.mkdir(parents=True,exist_ok=True)
    _rotate(path)
    log=open(path,"a",encoding="utf-8",buffering=1)
    log.write(f"\n=== RemiX Duo overlay start {time.strftime('%Y-%m-%d %H:%M:%S')} pid={os.getpid()}\n")
    install_exception_boundary(log)
    # R63: In a frozen --windowed EXE, an attached pseudo-terminal can
    # report isatty()=True while its Python text stream still uses cp1252.
    # Logging a Vietnamese FIR warning then raises UnicodeEncodeError from
    # a Qt callback, concealing the original safety-gate failure. Frozen
    # GUI logs ALWAYS use this already-open UTF-8 stream.
    configure_unicode_output(log,redirect=redirect)
    faulthandler.enable(file=log,all_threads=True)
    def beat():
        faulthandler.dump_traceback_later(stall_s,repeat=False,file=log,exit=False)
    timer=QTimer(app)
    timer.setInterval(1000)
    timer.timeout.connect(beat)
    timer.start()
    beat()
    app.aboutToQuit.connect(faulthandler.cancel_dump_traceback_later)
    return log,timer
