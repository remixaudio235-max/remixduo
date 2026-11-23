import errno
import os
import re
from pathlib import Path
from ..contracts import Capability
from .identity import machine_code

class FileLease:
    def __init__(self,fd): self.fd=fd
    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd=None
    def __del__(self): self.close()

class MacServices:
    platform='MAC'
    machine_code=staticmethod(machine_code)

    def acquire_lock(self,name,directory):
        import fcntl
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',name):
            raise ValueError('Invalid lock name')
        directory=Path(directory)
        directory.mkdir(parents=True,exist_ok=True)
        # Never unlink the file: a waiting process must lock the same inode.
        fd=os.open(directory/(name+'.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc:
            os.close(fd)
            if exc.errno in (errno.EACCES,errno.EAGAIN): return None
            raise
        return FileLease(fd)

    def native_capability(self):
        from .permissions import status
        permissions=status()
        missing=[k for k,v in permissions.items() if not v]
        if missing:return Capability(False,'HOLD: '+', '.join(missing))
        return Capability(False,'HOLD: native services available; trace/axis per-frame verification required')

    def list_windows(self):
        import objc
        from .discovery import list_windows
        with objc.autorelease_pool():return list_windows()

    def read_selection(self,window):
        if window is None:raise RuntimeError('HOLD: cần đúng window identity')
        from .discovery import current_window
        from .accessibility import read_selection
        state=current_window(window)
        if state is None:raise RuntimeError('HOLD: cửa sổ Smaart đã đóng/đổi process')
        return read_selection(state)

    def capture(self,window):
        from .capture import capture_window
        return capture_window(window)

    def configure_overlay(self,widget):
        import objc,AppKit,ctypes
        # Qt Cocoa WId is the native NSView; only touch this app's own window.
        view=objc.objc_object(c_void_p=ctypes.c_void_p(int(widget.winId())))
        native=view.window()
        behavior=int(native.collectionBehavior())
        behavior &= ~int(AppKit.NSWindowCollectionBehaviorMoveToActiveSpace)
        behavior &= ~int(AppKit.NSWindowCollectionBehaviorFullScreenPrimary)
        behavior |= int(AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces|AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary)
        native.setCollectionBehavior_(behavior)
        native.setLevel_(AppKit.NSFloatingWindowLevel)
        native.setHidesOnDeactivate_(False)

    def prepare_overlay_app(self):
        import AppKit
        AppKit.NSApplication.sharedApplication().setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
