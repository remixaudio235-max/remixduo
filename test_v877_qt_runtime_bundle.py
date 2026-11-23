"""Regression tests for the frozen PyQt6/VC runtime bundle."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist" / "RemiXDuo_QA" / "_internal"


def test_bundle_does_not_ship_foreign_icu_from_build_path():
    bundled = DIST / "icuuc.dll"
    system = Path(r"C:\Windows\System32\icuuc.dll")

    if bundled.exists():
        assert bundled.read_bytes() == system.read_bytes()


def test_build_sanitizes_path_before_pyinstaller_and_checks_qt():
    script = (ROOT / "build_remix_duo_qa_v877.ps1").read_text(encoding="utf-8")

    sanitize = script.index("QA_BUILD_PATH_SANITIZED")
    pyinstaller = script.index("Run-PyInstaller @(")
    package_check = script.index("--package-selfcheck")
    assert sanitize < pyinstaller < package_check
    assert "$env:SystemRoot\\System32" in script
    assert "--qt-selfcheck" in script


def test_runtime_hook_has_headless_qt_import_probe():
    hook = (ROOT / "qa_runtime_hook_remix_duo_v877.py").read_text(
        encoding="utf-8"
    )

    assert 'if "--qt-selfcheck" in sys.argv:' in hook
    assert "from PyQt6 import QtCore" in hook
    assert "QT_RUNTIME_SELF_CHECK_FAILED" in hook
