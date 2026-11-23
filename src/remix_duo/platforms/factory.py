import sys

def services():
    if sys.platform == 'win32':
        from .windows.services import WindowsServices
        return WindowsServices()
    if sys.platform == 'darwin':
        from .macos.services import MacServices
        return MacServices()
    raise RuntimeError('UNSUPPORTED_PLATFORM')
