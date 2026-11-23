# -*- coding: utf-8 -*-
"""Port only RemiX EQ/MagEq/export into responsive V8.18 QA, preserving AutoPhase."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
src=ROOT/"signal_tools_gui_v813.py"
s=src.read_text(encoding="utf-8-sig")
v09=(ROOT.parent/"integration_v817_mageq_export_v09"/"signal_tools_gui_v813.py").read_text(encoding="utf-8")
block=v09[v09.index("class EQFinished(QObject):"):v09.index("\nclass FIRDialog(TFDialog):")]
a=s.index("class EQDialog(TFDialog):");b=s.index("\nclass FIRDialog(TFDialog):",a)
s=s[:a]+block+s[b:]
def swap(a,b):
 global s
 if a not in s:raise RuntimeError("V818 template mismatch: "+a[:80])
 s=s.replace(a,b,1)
swap("import math\nfrom pathlib import Path","import math,concurrent.futures\nfrom pathlib import Path")
swap("from PyQt6.QtCore import Qt,QTimer,QEvent,QPoint","from PyQt6.QtCore import Qt,QTimer,QEvent,QPoint,QObject,pyqtSignal")
swap("QTextEdit,QFileDialog,QMessageBox,QFrame,QStackedWidget,QScrollArea,QMenu)",
     "QTextEdit,QFileDialog,QMessageBox,QFrame,QStackedWidget,QScrollArea,QMenu,QCheckBox,QSizePolicy)")
swap("from signal_tools_core_v813 import (source_arrays,auto_peq,",
     "from signal_tools_core_v813 import (source_arrays,")
swap("    design_linear_phase_fir,save_peq_text,save_fir_txt,save_fir_wav_float)",
     "    design_linear_phase_fir,save_fir_txt,save_fir_wav_float)")
swap("from win_databar_v7 import locate_smaart",
     "from remix_autoeq_v05_adapter import design_remix_eq\n"
     "from native_eq_mag_v06 import NativeAutoEQMag\n"
     "from autoeq_export_dialog_v08 import EQExportSnapshot,EQExportDialog\n"
     "from win_databar_v7 import locate_smaart")
swap('self.page_heights={"phase":400,"eq":478,"fir":475}',
     'self.page_heights={"phase":400,"eq":555,"fir":475}')
swap('self.setWindowTitle("RemiX Signal V8.18")',
     'self.setWindowTitle("RemiX Signal V8.18 + MagEq V10 QA")')
swap('''        self.pages=self.dock.pages
        self.buttons={}''',
     '''        self.pages=self.dock.pages
        self.native_eq=NativeAutoEQMag(self)
        self.eq.native_ready.connect(self.native_eq.set_data)
        self.eq.native_clear.connect(self.native_eq.clear)
        self.eq.native_enabled.connect(self.native_eq.set_enabled)
        self.buttons={}''')
swap('''        for mode,label in (("phase","Auto Phase"),
                           ("eq","Auto EQ"),
                           ("fir","FIR")):''',
     '''        for mode,label in (("phase","Auto Phase"),
                           ("eq","Auto EQ"),
                           ("export","Xuất EQ"),
                           ("fir","FIR")):''')
swap('''            button.setToolTip(f"RemiX Signal · {label}")
            button.clicked.connect(lambda _,m=mode:self.select(m))
            main.addWidget(button,3 if mode=="phase" else 2 if mode=="eq" else 1)
            self.buttons[mode]=button''',
     '''            button.setToolTip(f"RemiX Signal · {label}")
            button.setMinimumWidth(0)
            button.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
            if mode=="export":
                button.clicked.connect(self.open_export_from_bar)
            else:
                button.clicked.connect(lambda _,m=mode:self.select(m))
            main.addWidget(button,3 if mode=="phase" else 2 if mode in ("eq","export") else 1)
            self.buttons[mode]=button''')
swap('''        for mode,text in (("phase","Auto Phase"),("eq","Auto EQ"),("fir","FIR")):''',
     '''        for mode,text in (("phase","Auto Phase"),("eq","Auto EQ"),
                          ("export","Xuất EQ"),("fir","FIR")):''')
swap('''            action.triggered.connect(lambda _,m=mode:self.select(m))''',
     '''            if mode=="export":
                action.triggered.connect(self.open_export_from_bar)
            else:
                action.triggered.connect(lambda _,m=mode:self.select(m))''')
swap('''        self.menu_button.hide()
        self.setContextMenuPolicy''',
     '''        self.menu_button.hide()
        self.buttons["export"].setEnabled(False)
        self.eq.export_ready.connect(self.buttons["export"].setEnabled)
        self.setContextMenuPolicy''')
swap('''            "full":("Auto Phase","Auto EQ","FIR"),
            "compact":("A.Phase","A.EQ","FIR"),
            "mini":("AP","EQ","FIR")''',
     '''            "full":("Auto Phase","Auto EQ","Xuất EQ","FIR"),
            "compact":("A.Phase","A.EQ","Xuất","FIR"),
            "mini":("AP","EQ","X","FIR")''')
swap('''        for name,button in self.buttons.items():
            button.setStyleSheet(
                "font:bold 9px 'Segoe UI';min-width:0px;min-height:22px;"''',
     '''        for name,button in self.buttons.items():
            if name=="export":
                button.setStyleSheet(
                  "font:bold 8px 'Segoe UI';min-width:0px;min-height:22px;"
                  "background:#17533F;color:#D7FFE7;border-radius:4px;")
                continue
            button.setStyleSheet(
                "font:bold 8px 'Segoe UI';min-width:0px;min-height:22px;"''')
swap('''    def select(self,mode):
        if mode not in self.pages:raise ValueError("Unknown tool")''',
     '''    def open_export_from_bar(self):
        self.select("eq")
        self.eq.export_eq()

    def select(self,mode):
        if mode not in self.pages:raise ValueError("Unknown tool")''')
swap('''        self.active=mode
        self.engine.ui_tool_enabled=(mode=="phase")''',
     '''        self.active=mode
        if mode!="eq":self.native_eq.hide()
        self.engine.ui_tool_enabled=(mode=="phase")
        # SUM and MagEq are exclusive preview modes: do not superimpose
        # two model curves of the same lime color in the Smaart Mag plot.
        self.engine.refresh_visibility()''')
swap('''        if not active:
            self.hide()
            self.dock.hide()''',
     '''        if not active:
            self.native_eq.hide()
            self.hide()
            self.dock.hide()''')
swap('''        self.timer.stop()
        self._anchor_pool.shutdown(wait=False,cancel_futures=True)''',
     '''        self.timer.stop()
        self.native_eq.stop()
        self.eq._serial+=1
        self.eq._pool.shutdown(wait=False,cancel_futures=True)
        self._anchor_pool.shutdown(wait=False,cancel_futures=True)''')
assert s.count("class EQDialog(TFDialog):")==1
assert 'self.plot.set_curves(r.hz,r.before_db,r.after_db)' not in s
assert 'self.native_eq=NativeAutoEQMag(self)' in s
assert 'self._toolbar_mode="full"' in s
src.write_text(s,encoding="utf-8")

# IMPORTANT: Modify the QA COPY of the SUM overlay. Leave original untouched.
# Hide SUM only when the new QA hub is in EQ or FIR mode. Existing SUM code
# in Auto Phase mode (its DSP, model, screen axes, Y-pan) stays identical.
p=ROOT/"overlay_v7.py"
s=p.read_text(encoding="utf-8-sig")
a='''        has=self.current_sum is not None and self.overlay_positioned'''
b='''        has=(self.current_sum is not None and self.overlay_positioned and
             (not self.managed_mode or self.ui_tool_enabled))'''
if a not in s:raise RuntimeError("SUM visibility template changed")
s=s.replace(a,b,1)
p.write_text(s,encoding="utf-8")
print("V10_INTEGRATED_ON_RESPONSIVE_V818_COPY_ONLY")
