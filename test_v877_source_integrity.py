"""Source-level release guards that do not create Qt applications."""
from pathlib import Path


ROOT = Path(__file__).parent


def test_fir_vietnamese_labels_are_utf8_not_question_mark_damage():
    text = (ROOT / "signal_tools_gui_v813.py").read_text(encoding="utf-8")
    expected = (
        "FIR: chỉ dùng 1 Trace tick",
        "Fs Smaart chưa xác minh — FIR HOLD",
        "TẠO FIR",
        "Xuất TXT",
        "Đang thiết kế FIR trên worker…",
        "Xuất FIR taps, không nạp DSP/Smaart.",
    )
    for label in expected:
        assert label in text
    for damaged in ("ch?", "??", "THI?T", "Xu?t", "kh?ng"):
        assert damaged not in text


def test_installer_build_cannot_repackage_stale_outputs_silently():
    text = (ROOT / "build_remix_duo_qa_v877.ps1").read_text(encoding="utf-8")
    assert "SkipBuild" not in text
    assert text.count("'--clean'") == 3
    assert "--package-selfcheck" in text
    assert "PACKAGE_SELF_CHECK_FAILED" in text
    assert "Start-Process" in text
    assert ".ExitCode" in text
    assert "WaitForExit(30000)" in text
    assert "PACKAGE_SELF_CHECK_TIMEOUT" in text


def test_frozen_qa_selfcheck_dispatches_from_runtime_hook():
    text = (ROOT / "qa_runtime_hook_remix_duo_v877.py").read_text(
        encoding="utf-8"
    )
    assert '"--package-selfcheck" in sys.argv' in text
    assert "load_installed_license" in text
    assert "os._exit" in text


def test_uninstall_hook_is_idempotent_in_inno_setup():
    text = (ROOT / "remix_duo_qa_v877_installer.iss").read_text(
        encoding="utf-8"
    )
    uninstall = text.split("[UninstallRun]", 1)[1]
    assert 'RunOnceId: "DisableSmaartCompanion"' in uninstall
