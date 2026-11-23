import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_plot_notice_is_compact_instead_of_spanning_the_plot():
    from PyQt6.QtWidgets import QApplication, QWidget
    from remix_duo.ui.widgets import show_notice

    app = QApplication.instance() or QApplication([])
    plot = QWidget()
    plot.resize(1400, 400)
    plot.show()
    show_notice(plot, "FIR: " + "cảnh báo tham khảo; " * 30)
    app.processEvents()

    notice = plot._remix_notice
    assert notice.width() <= 520
    assert notice.height() <= 84
    assert notice.x() >= plot.width() - notice.width() - 16
    assert notice.objectName() == "remixToast"
    assert notice.property("toastTone") == "warning"


def test_fir_warning_path_emits_only_one_toast():
    from pathlib import Path

    source = Path("signal_tools_gui_v813.py").read_text(encoding="utf-8")
    block = source[source.index("        if fir_warnings:"):
                   source.index("        if self._manual_token is None:")]

    assert block.count("show_notice(") == 0
    assert block.count("self.notice(") == 1


def test_toast_semantic_tones_share_one_pro_shell():
    from PyQt6.QtWidgets import QApplication, QWidget
    from remix_duo.ui.widgets import show_notice

    app = QApplication.instance() or QApplication([])
    owner = QWidget(); owner.resize(900, 400); owner.show()
    cases = (
        ("Đang Auto, vui lòng đợi...", "busy"),
        ("Đã tạo FIR thành công", "success"),
        ("Cảnh báo: ripple lớn", "warning"),
        ("Không đọc được file Trace", "error"),
        ("Thông tin tham khảo", "info"),
    )
    label = None
    for message, tone in cases:
        show_notice(owner, message); app.processEvents()
        assert owner._remix_notice.property("toastTone") == tone
        assert owner._remix_notice.objectName() == "remixToast"
        label = label or owner._remix_notice
        assert owner._remix_notice is label


def test_short_busy_toast_fits_content_instead_of_using_full_cap():
    from PyQt6.QtWidgets import QApplication, QWidget
    from remix_duo.ui.widgets import show_notice

    app = QApplication.instance() or QApplication([])
    plot = QWidget(); plot.resize(1400, 400); plot.show()
    show_notice(plot, "Đang Auto, vui lòng đợi..."); app.processEvents()

    assert 200 <= plot._remix_notice.width() <= 280
    assert plot._remix_notice.property("toastTone") == "busy"


def test_hidden_native_plot_toast_is_top_level_not_a_panel_child():
    from PyQt6.QtWidgets import QApplication, QWidget
    from remix_duo.ui.widgets import show_plot_notice

    app = QApplication.instance() or QApplication([])
    plot = QWidget(); plot.setGeometry(200, 100, 1200, 360)
    assert not plot.isVisible()
    show_plot_notice(plot, "Auto EQ cần đúng 1 Trace đã xác minh.")
    app.processEvents()

    notice = plot._remix_notice
    assert notice.isWindow()
    assert notice.parent() is None
    assert notice.width() <= 520

