"""Shared offline entry. Windows native overlay retains its existing entrypoint."""
import argparse
import json
import sys
from . import __version__

def main(argv=None):
    parser=argparse.ArgumentParser(description='RemiX Duo Smaart Overlay')
    parser.add_argument('--selfcheck',action='store_true',help='Read-only dependency/resource check; no GUI, native capture or license mutation')
    parser.add_argument('--workspace',action='store_true',help='Mở công cụ TRF thủ công thay cho overlay')
    args=parser.parse_args(argv)
    from .platforms.paths import app_paths
    from .platforms.factory import services
    backend=services();paths=app_paths()
    if args.selfcheck:
        import numpy,scipy
        from PyQt6.QtCore import QT_VERSION_STR
        assets=['remix_activation_logo.jpg','remix_dou_swirl_toolbar32.png','remixduo_app.ico']
        missing=[name for name in assets if not paths.resource(name).is_file()]
        print(json.dumps({'version':__version__,'platform':backend.platform,'qt':QT_VERSION_STR,
                          'numpy':numpy.__version__,'scipy':scipy.__version__,
                          'missing_assets':missing,'native':backend.native_capability().reason,
                          'mode':'manual_workspace' if args.workspace else 'smaart_overlay'},ensure_ascii=True))
        return 2 if missing else 0
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
    app=QApplication(sys.argv)
    app.setApplicationName('RemiX Duo Smaart Overlay')
    app.setWindowIcon(QIcon(str(paths.resource('remixduo_app.ico'))))
    # Manual TRF workspace has no native observer and must not compete with the
    # Smaart overlay singleton. Keep one offline workspace instance separately.
    lock_name = ('RemiXDuoOfflineWorkspaceV887' if args.workspace or backend.platform != 'MAC'
                 else 'RemiXSignalSmaartDataBarV823')
    lease=backend.acquire_lock(lock_name,paths.data)
    if lease is None:return 21
    try:
        from .licensing.gate import activation_gate
        if not activation_gate():return 22
        if backend.platform=='MAC' and not args.workspace:
            from .ui.overlay import OverlayController
            app.setQuitOnLastWindowClosed(False)
            if hasattr(backend,'prepare_overlay_app'):backend.prepare_overlay_app()
            view=OverlayController(backend)
            app.aboutToQuit.connect(view.close)
        else:
            from .ui.workspace import Workspace
            view=Workspace(backend);view.show()
        return app.exec()
    finally:lease.close()
