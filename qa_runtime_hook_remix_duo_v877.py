"""PyInstaller runtime hook FOR QA TEST INSTALLER ONLY.
Commercial builds must NEVER include this hook. The commercial frozen
application is gated exclusively by Cloudflare License V8.76.
"""
import os
import sys

sys._remix_duo_qa_signed_build = True

QT_RUNTIME_SELF_CHECK_FAILED = 24
ONLINE_LICENSE_SELF_CHECK_FAILED = 25

# Import Qt headlessly before overlay_v7 so the build can prove that the
# bundled PyQt extension and VC runtime DLLs are ABI-compatible.
if "--qt-selfcheck" in sys.argv:
    try:
        from PyQt6 import QtCore, QtGui, QtWidgets
        code = 0 if QtCore.QT_VERSION_STR and QtGui and QtWidgets else 24
        from pathlib import Path
        bundle = Path(sys._MEIPASS)
        for asset in ('remix_dou_swirl_toolbar32.png',
                      'remix_activation_logo.jpg',
                      'V812_MAG_TITLE_TEMPLATE.png',
                      'V812_PHASE_TITLE_TEMPLATE.png'):
            if QtGui.QImage(str(bundle / asset)).isNull():
                code = QT_RUNTIME_SELF_CHECK_FAILED
    except Exception:
        code = QT_RUNTIME_SELF_CHECK_FAILED
    os._exit(code)

if "--online-license-selfcheck" in sys.argv:
    try:
        from remix_duo_online_license_v878 import (
            LICENSE_SERVER_URL, activate_online_and_save, verify_online_token,
        )
        code = 0 if (
            LICENSE_SERVER_URL.startswith("https://") and
            callable(activate_online_and_save) and callable(verify_online_token)
        ) else ONLINE_LICENSE_SELF_CHECK_FAILED
    except Exception:
        code = ONLINE_LICENSE_SELF_CHECK_FAILED
    os._exit(code)

# A frozen windowed executable can load heavyweight GUI/scientific hooks before
# overlay_v7 reaches its main block. Dispatch the QA package probe here so the
# build gate is bounded, headless and independent of the live overlay mutex.
if "--package-selfcheck" in sys.argv:
    try:
        from remix_duo_license_v874 import load_installed_license
        status = load_installed_license().code
        code = 0 if status == "ACTIVE" else 22
    except Exception:
        code = 23
    os._exit(code)
