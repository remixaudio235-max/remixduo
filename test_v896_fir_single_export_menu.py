"""V8.96: one visible FIR export button, TXT or vendor submenu.

Uses the established native mock tick and real FIR coefficients. No hardware
DSP write and no audio I/O. Save dialogs are patched to temporary QA files.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path

from PyQt6.QtWidgets import QFileDialog
from fir_dsp_export_v872 import PROFILES
from test_v845_fir_one_trace import init,wait_fir
from test_v16_independent_one_tick import tick


def test_one_export_control_and_txt_vendor_menu_write_real_coefficients(tmp_path,monkeypatch):
    app,obs,engine,hub,fir=init()
    hub.native_fir.timer.stop()
    try:
        hub.select("fir")
        app.processEvents()
        assert fir.export_fir.text()=="XUẤT FIR"
        assert not fir.export_fir.isEnabled()
        assert fir.export_txt.isHidden() and fir.export_wav.isHidden()
        assert fir.export_dsp.isHidden() and fir.dsp_profile.isHidden()
        assert [a.text() for a in fir.export_menu.actions()]==[
            "TXT chung (.txt)","Theo hãng DSP / Crossover"]
        assert len(fir.export_vendor_actions)>=15
        assert "miniDSP TXT" in fir.export_vendor_actions
        assert not fir.phase_plus.isChecked()
        assert fir.fir_mode.currentData()=="phase"
        # This test validates a MAG-1024 coefficient export, so choose MAG.
        fir.fir_mag_button.click()
        fir.taps.setCurrentIndex(fir.taps.findData(1024))
        assert fir.phase_plus.isHidden()
        fir.compute()
        wait_fir(app,fir)
        assert fir.result is not None
        assert fir.export_fir.isEnabled()
        fir.show_export_fir_menu()
        assert fir.export_txt_action.isEnabled()
        assert fir.export_vendor_actions["miniDSP TXT"].isEnabled()
        fir.export_menu.hide()
        txt=tmp_path/"plain.txt"
        vendor=tmp_path/"vendor.txt"
        dest=[txt,vendor]
        monkeypatch.setattr(
            QFileDialog,"getSaveFileName",
            lambda *args,**kwargs:(str(dest.pop(0)),""))
        fir.export_txt_action.trigger()
        fir.export_vendor_actions["miniDSP TXT"].trigger()
        assert not dest
        assert txt.is_file() and vendor.is_file()
        # Generic TXT has two RemiX metadata comment lines; profiles export
        # exactly the requested number of raw coefficient lines.
        assert len([ln for ln in txt.read_text(encoding="utf8").splitlines()
                    if not ln.startswith("#")])==1024
        assert len(vendor.read_text(encoding="utf8").splitlines())==1024
    finally:
        hub.close()
        app.processEvents()


def test_vendor_limit_disabled_for_phaseplus_without_silent_truncation():
    p=(Path.home()/"Documents"/"Smaart Suite"/"Data"/
       "Transfer Function"/"Session Data"/"TUNNINNGGG-4.trf")
    if not p.is_file():
        import pytest
        pytest.skip("Real reference TRF not available on this PC")
    app,obs,engine,hub,fir=init()
    hub.native_fir.timer.stop()
    try:
        idx=next(i for i,x in enumerate(obs.order)
                 if x.name.lower()==p.name.lower())
        for _ in range(3):
            tick(obs,{idx})
        fir.refresh_sources()
        fir.fir_mode.setCurrentIndex(1)
        fir.fir_lf.setValue(114)
        fir.fir_hf.setValue(379)
        assert not fir.phase_plus.isChecked()
        fir.taps.setCurrentIndex(fir.taps.findData(4096))
        fir.phase_plus.setChecked(True)
        assert fir.taps.currentData()==4096
        assert fir.taps.isEnabled()
        fir.compute()
        wait_fir(app,fir,timeout=25)
        assert fir.export_fir.isEnabled()
        fir.show_export_fir_menu()
        limited=fir.export_vendor_actions["Bose ControlSpace 512"]
        supported=fir.export_vendor_actions["miniDSP TXT"]
        assert not limited.isEnabled()
        assert "Tap count" in limited.toolTip()
        assert supported.isEnabled()
        fir.export_menu.hide()
        fir.fir_hf.setValue(800)
        assert not fir.export_fir.isEnabled()
        assert fir.result is None
    finally:
        hub.close()
        app.processEvents()
