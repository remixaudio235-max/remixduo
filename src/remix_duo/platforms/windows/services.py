import ctypes
import re
from ..contracts import Capability
from .identity import machine_code

class MutexLease:
    def __init__(self, api, handle):
        self.api, self.handle = api, handle
    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None
    def __del__(self):
        self.close()

class WindowsServices:
    platform='WIN'
    machine_code=staticmethod(machine_code)

    def acquire_lock(self, name, directory):
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',name):
            raise ValueError('Invalid mutex name')
        api=ctypes.WinDLL('kernel32',use_last_error=True)
        api.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_wchar_p]
        api.CreateMutexW.restype=ctypes.c_void_p
        api.CloseHandle.argtypes=[ctypes.c_void_p]
        api.CloseHandle.restype=ctypes.c_int
        handle=api.CreateMutexW(None,0,'Local\\'+name)
        error=ctypes.get_last_error()
        if not handle: raise ctypes.WinError(error)
        if error==183:
            api.CloseHandle(handle)
            return None
        return MutexLease(api,handle)

    def native_capability(self):
        return Capability(False,'HOLD: use existing Windows overlay backend with its per-frame verification')

    def read_selection(self, window):
        raise RuntimeError('HOLD: native observer evidence required; shared workspace is offline')
