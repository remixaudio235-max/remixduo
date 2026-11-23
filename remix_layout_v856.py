"""V8.56 compact professional Smaart sidebar layout for all three tools.

Presentation-only: no TF, FIR, solver, overlay identity, selection or
hardware callbacks touched. Match the original 205px Smaart side column.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel,QTextEdit,QSizePolicy,QHBoxLayout,QVBoxLayout


# Static high-contrast dark OLED tokens. No continuous blur or animation.
ACCENTS={"phase":"#7DFF7E","eq":"#FFA647","fir":"#65DAFF"}
BASE_STYLE="""
QWidget#rightDock {background:#08121D;border:1px solid #294659;}
QLabel#dockHeading {font:700 10px 'Segoe UI';color:#FFFFFF;padding:3px 6px;}
QLabel#uxSection {color:#A8D2E2;font:700 9px 'Segoe UI';
                    margin-top:4px;padding-left:2px;}
QLabel#title {font:700 13px 'Segoe UI';color:#F5FAFF;}
QLabel#hint {color:#A9C7D6;font:10px 'Segoe UI';}
QLabel#score {color:#B6FFE1;font:700 11px 'Segoe UI';
              background:#0F2930;border:1px solid #2A6168;
              border-radius:6px;padding:5px;}
QLabel#uxLive {color:#91DBF0;font:600 10px 'Segoe UI';
               border:1px solid #30556C;border-radius:5px;
               padding:4px;background:#0F2635;}
QComboBox,QSpinBox,QDoubleSpinBox {background:#142D3F;color:#F0FAFF;
    border:1px solid #365E74;border-radius:5px;min-height:27px;
    padding-left:5px;}
QComboBox:focus,QSpinBox:focus,QDoubleSpinBox:focus {
    border:1px solid #6AD9F2;}
QComboBox:disabled {color:#A9C5D2;background:#102535;}
QPushButton {background:#1C4056;color:#EFFBFF;
    border:1px solid #3A667D;border-radius:6px;
    font:700 10px 'Segoe UI';min-height:28px;}
QPushButton:hover {background:#285670;border-color:#6FA9C0;}
QPushButton:focus {border:1px solid #C4ECFF;}
QPushButton:disabled {color:#69818F;background:#142634;}
QPushButton#firModeSwitch {background:#102838;color:#B9D9E7;
    border:1px solid #355D70;border-radius:5px;min-height:29px;}
QPushButton#firModeSwitch:checked {background:#123F50;color:#72F0FF;
    border:2px solid #45D6EE;}
QPushButton#firModeSwitch:hover {border:1px solid #66DCEF;}
QTextEdit {background:#071924;color:#D2EBF4;
    border:1px solid #294B61;border-radius:6px;
    font:10px 'Consolas';padding:4px;}
QCheckBox {color:#DCEEF4;font:10px 'Segoe UI';spacing:4px;}
QScrollArea {background:#08121D;border:0;}
QScrollBar:vertical {background:#102535;width:7px;margin:0px;}
QScrollBar::handle:vertical {background:#3E718A;min-height:28px;
                            border-radius:3px;}
QScrollBar:horizontal {height:0px;}
"""
PHASE_STYLE="""
QWidget#rootPanel {background:#08121D;}
QFrame#panelCard,QFrame#traceCard {background:#102331;
    border:1px solid #2B4B5D;border-radius:7px;}
QLabel#sectionTitle {color:#B2D7E4;font:700 9px 'Segoe UI';}
QLabel#traceNameLarge {color:#F2FCFF;font:700 11px 'Segoe UI';}
QLabel#traceDelayLarge {color:#A6C7D6;font:10px 'Segoe UI';}
QPushButton#candidateOption {background:#152F40;color:#EFF8FA;
    border:1px solid #375970;border-radius:6px;
    font:600 10px 'Segoe UI';padding:4px;min-height:37px;}
QPushButton#candidateOption:checked {background:#173E32;
    border:2px solid #70F7A0;color:#C6FFE0;}
QPushButton#run {background:#38D876;border:1px solid #6BFF9D;
    color:#082012;font:800 11px 'Segoe UI';border-radius:6px;}
"""


def _insert_section(layout,widget,title):
    if layout.indexOf(widget)<0:
        raise AssertionError("Source widget absent from UI layout")
    heading=QLabel(title)
    heading.setObjectName("uxSection")
    heading.setAccessibleName(title)
    heading.setFixedHeight(17)
    layout.insertWidget(layout.indexOf(widget),heading)
    return heading


def _move_widget_before(layout,widget,before):
    if layout.indexOf(widget)<0 or layout.indexOf(before)<0:
        raise AssertionError("Reorder would discard an existing Qt control")
    layout.removeWidget(widget)
    layout.insertWidget(layout.indexOf(before),widget)


def _move_layout_before(layout,child,before):
    if layout.indexOf(before)<0:
        raise AssertionError("Required result area missing")
    layout.removeItem(child)
    layout.insertLayout(layout.indexOf(before),child)


def _common(panel,mode):
    panel.main.setContentsMargins(6,6,6,6)
    panel.main.setSpacing(5)
    panel.source.setObjectName("uxTrace")
    panel.source.setAccessibleName("Trace ?? x?c minh trong Smaart")
    panel.source.setMinimumHeight(28)
    # Dock header already names active tool: no duplicated AUTO EQ/FIR
    # title taking 25px inside a 205px sidebar.
    title=panel.main.itemAt(0).widget()
    if title is not None and title.objectName()=="title":
        title.hide()
    panel.note.setWordWrap(False)
    panel.note.setMinimumHeight(18)
    panel.note.setMaximumHeight(21)
    panel.summary.setMinimumHeight(27)
    panel.summary.setMaximumHeight(72)
    panel.summary.setAlignment(Qt.AlignmentFlag.AlignLeft |
                               Qt.AlignmentFlag.AlignVCenter)
    panel.details.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
    panel.details.setMinimumHeight(86)
    panel.details.setMaximumHeight(165)
    panel.details.setSizePolicy(QSizePolicy.Policy.Preferred,
                                QSizePolicy.Policy.Expanding)
    accent=ACCENTS[mode]
    panel.setStyleSheet(panel.styleSheet()+BASE_STYLE+
        "QPushButton#run {background:"+accent+";color:#10202A;"
        "border:1px solid "+accent+";font:800 10px 'Segoe UI';}"
        "QPushButton#run:pressed{background:#C7F7FF;}")
    panel._ux_sections=[]


def style_eq(eq,buttons):
    _common(eq,"eq")
    eq.note.setText("Auto EQ \u2022 Preview \u2022 Kh\u00f4ng ghi DSP")
    eq.note.setToolTip("Auto EQ tu 1 Trace duoc xac minh. MagEQ hien tren Smaart. Khong ghi DSP.")
    # The dock heading and action already identify Auto EQ.  Keep the safety
    # meaning in the tooltip, but remove the redundant visible subtitle so the
    # trace selector starts directly below the header.
    eq.note.hide()
    eq.roi_status.setObjectName("uxLive")
    eq.roi_status.setMinimumHeight(27)
    eq.roi_status.setMaximumHeight(36)
    eq.fs.setAccessibleName("Fs tự động đồng bộ từ Smaart (ẩn)")
    # Keep the Fs widget and its verification token/signal chain alive;
    # SmaartConfig.xml still supplies sample rate to the solver.
    eq.fs.hide()
    eq.filter_count.setAccessibleName("Số PEQ tối đa")
    eq.boost.setAccessibleName("Nâng tối đa, dB")
    eq.cut.setAccessibleName("Cắt tối đa, dB")
    # Critical UX: Run/Export ABOVE long diagnostics, never below them.
    _move_layout_before(eq.main,buttons,eq.summary)
    _move_widget_before(eq.main,eq.mageq_toggle,eq.summary)
    _move_widget_before(eq.main,eq.native_state,eq.details)
    # Two full-width gain rows: readable Vietnamese labels within Smaart's
    # 205-px dock. Retain the same boost/cut spinboxes, ranges and signals.
    eq.main.removeWidget(eq.boost)
    eq.main.removeWidget(eq.cut)
    gain_row=QVBoxLayout()
    gain_row.setContentsMargins(0,0,0,0)
    gain_row.setSpacing(4)
    boost_row=QHBoxLayout()
    cut_row=QHBoxLayout()
    for row in (boost_row,cut_row):
        row.setContentsMargins(0,0,0,0)
        row.setSpacing(4)
    boost_label=QLabel("Nâng tối đa")
    cut_label=QLabel("Cắt tối đa")
    for caption in (boost_label,cut_label):
        caption.setObjectName("uxSection")
        caption.setFixedWidth(83)
    eq.boost.setPrefix("+")
    eq.boost.setDecimals(1)
    eq.cut.setPrefix("")
    eq.cut.setDecimals(1)
    boost_row.addWidget(boost_label)
    boost_row.addWidget(eq.boost,1)
    cut_row.addWidget(cut_label)
    cut_row.addWidget(eq.cut,1)
    gain_row.addLayout(boost_row)
    gain_row.addLayout(cut_row)
    eq.main.insertLayout(eq.main.indexOf(eq.filter_count)+1,gain_row)
    eq._ux_gain_row=gain_row
    eq._ux_gain_boost_row=boost_row
    eq._ux_gain_cut_row=cut_row
    eq._ux_gain_labels=(boost_label,cut_label)
    eq.native_state.setObjectName("uxLive")
    eq.native_state.setMaximumHeight(43)
    eq._ux_sections.extend((
        _insert_section(eq.main,eq.source,"01  TRACE \u0110O"),
        _insert_section(eq.main,eq.target,"02  CH\u1eccN CH\u1ebe \u0110\u1ed8"),
    ))
    # V8.64: clean compact Auto EQ panel. These controls still exist so
    # ROI dragging, native verification, HOLD logic and exports are unchanged.
    # Only the two user-marked visual regions are hidden.
    for hidden_control in (eq.roi_status,eq.mageq_toggle,eq.native_state,
                           eq.details):
        hidden_control.hide()
    # The compact result is the user's completion proof.  Keep the verbose
    # diagnostics hidden, but never hide the PEQ/WRMS summary itself.
    eq.summary.show()
    eq.summary.setWordWrap(True)
    eq.summary.setMinimumHeight(34)
    eq.summary.setMaximumHeight(50)
    # MagEq overlay stays enabled by default even without the visible toggle.
    # Other modules may still temporarily setChecked(False) as before.
    eq.setFixedHeight(373)


def fit_fir_content(fir):
    """Size scrollable content from its real layout, including DSP exports."""
    fir.setMinimumHeight(0)
    fir.setMaximumHeight(16777215)
    fir.main.activate()
    # Avoid spreading unused vertical space into the flexible 'Chọn Taps'
    # label. The exact height follows visible control size hints.
    height=max(260,fir.main.minimumSize().height(),fir.main.sizeHint().height(),
               fir.main.totalHeightForWidth(fir.width()))
    fir.setFixedHeight(height)
    return height


def style_fir(fir,export_buttons):
    _common(fir,"fir")
    fir.note.setText("Auto FIR \u2022 Preview \u2022 Kh\u00f4ng ghi DSP")
    fir.note.setToolTip("FIR linear phase; chon 1 Trace. Xuat he so, khong ghi DSP.")
    # Same compact rule as Auto EQ: the heading already names the tool.  Keep
    # the safety explanation available in the tooltip without spending a full
    # visible row in the narrow Smaart sidebar.
    fir.note.hide()
    fir.fs.setObjectName("uxLive")
    fir.overlay_status.setObjectName("uxLive")
    fir.overlay_status.setMaximumHeight(48)
    fir.taps.setAccessibleName("So taps bo loc FIR")
    fir.taps_label.setFixedHeight(16)
    fir.note.setFixedHeight(18)
    fir.fir_mode.setAccessibleName("Trang thai FIR mode (noi bo)")
    fir.fir_mag_button.setAccessibleName("Chon FIR MAG")
    fir.fir_phase_button.setAccessibleName("Chon FIR PHA")
    fir.calculate.setAccessibleName("Tao bo loc FIR")
    # Put action/export next to taps and live overlay status.
    _move_widget_before(fir.main,fir.calculate,fir.summary)
    _move_layout_before(fir.main,export_buttons,fir.summary)
    # Compact visible order, matching the requested Smaart screenshot:
    # Chọn Taps -> taps dropdown -> Phase+ -> MAG/PHA buttons ->
    # TẠO FIR -> XUẤT FIR. Hidden data/diagnostic controls keep their
    # original signals and source-of-truth values.
    for control in (fir.taps_label,fir.taps,fir.phase_plus):
        _move_widget_before(fir.main,control,fir.calculate)
    _move_layout_before(fir.main,fir._fir_mode_row,fir.calculate)
    # Make TẠO FIR and XUẤT FIR share ONE full-width action row, as the
    # supplied reference layout shows. Move the existing QPushButton;
    # don't create a duplicate or reconnect callbacks.
    if export_buttons.indexOf(fir.calculate)<0:
        fir.main.removeWidget(fir.calculate)
        export_buttons.insertWidget(0,fir.calculate,1)
    export_buttons.setStretch(1,1)
    export_buttons.setSpacing(4)
    fir._fir_actions_layout=export_buttons
    fir._ux_sections.extend((
        _insert_section(fir.main,fir.source,"01  TRACE \u0110O"),
        _insert_section(fir.main,fir.taps_label,"02  THI\u1ebeT L\u1eacP FIR"),
        _insert_section(fir.main,fir.summary,"03  K\u1ebeT QU\u1ea2 / XU\u1ea4T H\u1ec6 S\u1ed0"),
    ))
    # V8.103: Chọn Taps + the taps combobox in ONE two-column row.
    # Move the original widgets AFTER inserting the 02 section heading,
    # leaving all FIR mode, Phase+, source validation and taps signals intact.
    fir._taps_row=QHBoxLayout()
    fir._taps_row.setContentsMargins(0,0,0,0)
    fir._taps_row.setSpacing(5)
    fir.taps_label.setFixedWidth(67)
    fir.main.removeWidget(fir.taps_label)
    fir.main.removeWidget(fir.taps)
    fir._taps_row.addWidget(fir.taps_label,0,Qt.AlignmentFlag.AlignVCenter)
    fir._taps_row.addWidget(fir.taps,1)
    fir.main.insertLayout(fir.main.indexOf(fir.phase_plus),fir._taps_row)
    # V8.98: remove three user-marked visual regions while preserving all
    # underlying signal bindings and Smaart plot dragging. In particular,
    # the LF/HF values and saved Fs MUST still drive the FIR worker.
    # Always show the compact result/proof summary.  Hiding it made a
    # completed FIR indistinguishable from an idle panel on real Smaart.
    fir.summary.setMinimumHeight(40)
    fir.summary.setMaximumHeight(78)
    fir.summary.show()
    fir._ux_sections[2].show()
    for widget in (fir.offline_button,fir.offline_clear,
                   fir.fir_range_label,fir.fir_lf,fir.fir_hf,
                   fir.overlay_status,fir.fs,fir.details):
        widget.hide()
    # Full diagnostics stay internal; the finite result and proof state are
    # visible in the compact summary without exposing the old detail block.
    fit_fir_content(fir)


def style_phase(engine):
    engine.setStyleSheet(engine.styleSheet()+PHASE_STYLE)
    engine.setAccessibleName("Auto Phase: can dung hai Trace duoc tick")
    engine.solve.setToolTip("Tinh Top 3 phuong an phase/delay. Preview, khong ghi DSP.")
    for i,btn in enumerate(engine.candidates,1):
        btn.setAccessibleName(f"Phuong an Auto Phase thu {i}")
    engine.trace_card.setFixedHeight(138)
    engine.candidate_card.setFixedHeight(167)


def style_dock(dock,engine,eq,fir,eq_buttons=None,fir_buttons=None):
    # Used after widget construction. The existing solve/calc/export
    # signals, native callbacks, and trace identity gates are untouched.
    if eq_buttons is None or fir_buttons is None:
        raise ValueError("Need pre-existing live Qt button layouts")
    style_phase(engine)
    style_eq(eq,eq_buttons)
    style_fir(fir,fir_buttons)
    dock.setStyleSheet(dock.styleSheet()+BASE_STYLE)
    dock.scroll.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    dock.scroll.setVerticalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    dock.page_heights={"phase":400,"eq":373,"fir":fir.height()}
    dock.heading.setAccessibleName("Che do cong cu hien tai")
    dock._ux_v856=True
    return dock


def style_active_heading(dock,mode):
    accent=ACCENTS[mode]
    dock.heading.setText({"phase":"AUTO PHASE","eq":"AUTO EQ",
                          "fir":"AUTO FIR"}[mode])
    dock.heading.setStyleSheet(
        "background:#122837;color:"+accent+
        ";border-left:3px solid "+accent+
        ";font:700 10px 'Segoe UI';padding:3px 5px;")
    dock.heading.setToolTip(
        {"phase":"Hai Trace duoc tick | Delay / INV / SUM preview",
         "eq":"Mot Trace duoc tick | PEQ / MagEQ | preview only",
         "fir":"Mot Trace duoc tick | FIR Mag / Phase | preview only"}[mode])
