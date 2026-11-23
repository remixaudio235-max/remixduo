"""Read-only TCC preflight. Never requests/grants permission implicitly."""
def status():
    try:
        import ApplicationServices as AX
        import Quartz
        import ScreenCaptureKit
        return dict(frameworks=True,accessibility=bool(AX.AXIsProcessTrusted()),
                    screen_capture=bool(Quartz.CGPreflightScreenCaptureAccess()))
    except ImportError:
        return dict(frameworks=False,accessibility=False,screen_capture=False)
