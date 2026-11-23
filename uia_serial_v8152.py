"""Process-wide serialization for Windows UI Automation access.

pywinauto's UIA wrappers ultimately share native COM/UIAutomation state.
RemiX has several independent readers (Data Bar, plot roles, dock anchors and
smoothing); allowing those readers to traverse the same Smaart HWND at once
has produced native access violations.  Keep the lock outside the readers so
nested calls remain safe and every worker observes the same exclusion rule.
"""
from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
import threading


class UIABusyError(TimeoutError):
    """The previous read did not release UIA within the bounded wait."""


_UIA_LOCK = threading.RLock()


@contextmanager
def uia_serial_section(timeout: float = 8.0):
    acquired = _UIA_LOCK.acquire(timeout=max(0.0, float(timeout)))
    if not acquired:
        raise UIABusyError("UI Automation reader busy")
    try:
        yield
    finally:
        _UIA_LOCK.release()


def serialized_uia(function=None, *, timeout: float = 8.0):
    """Decorator for a complete native UIA transaction (re-entrant)."""
    def decorate(callback):
        @wraps(callback)
        def guarded(*args, **kwargs):
            with uia_serial_section(timeout):
                return callback(*args, **kwargs)
        return guarded
    return decorate(function) if function is not None else decorate
