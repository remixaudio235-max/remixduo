"""FIR MAG/PHASE isolation and actual preview semantics on Qt/offline workers."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import numpy as np
from scipy.signal import freqz
from PyQt6.QtWidgets import QApplication
from signal_tools_gui_v813 import FIRDialog,_fir_design_and_preview
from remix_layout_v856 import style_fir

def sample():
    f=np.geomspace(20,20000,1300)
    ph=np.deg2rad(35)*np.exp(-.5*(np.log2(f/1000)/.8)**2)
    h=10**(3*np.exp(-.5*(np.log2(f/300)/.4)**2)/20)*np.exp(1j*(ph-2*np.pi*f*.003))
    return f,h,np.ones_like(f)

def test_both_modes_have_correct_native_preview_and_delays():
    f,h,c=sample()
    for mode in ("mag","phase"):
        result,src=_fir_design_and_preview(f,h,c,1024,48000,"QA","hash",7,200,6000,mode)
        assert result.mode==mode and src.mode==mode
        assert len(result.taps)==1024
        assert abs(result.latency_ms-src.delay_ms)<1e-6
        _,resp=freqz(result.taps,worN=f,fs=48000)
        original=src.original_phase
        physical=np.rad2deg(np.angle(np.exp(1j*np.deg2rad(original))*resp))
        comp=resp*np.exp(2j*np.pi*f*result.latency_ms/1000)
        display=np.rad2deg(np.angle(np.exp(1j*np.deg2rad(original))*comp))
        assert np.max(np.abs(np.angle(np.exp(1j*np.deg2rad(src.after_phase-physical)))))<1e-7
        assert np.max(np.abs(np.angle(np.exp(1j*np.deg2rad(src.display_phase-display)))))<1e-7

def test_mode_changed_invalidates_fir():
    app=QApplication.instance() or QApplication([])
    dlg=FIRDialog(object())
    try:
        style_fir(dlg,dlg._action_row)
        assert dlg.fir_mode.currentData()=="phase"
        seq=dlg._serial
        dlg.fir_mode.setCurrentIndex(0)
        assert dlg.fir_mode.currentData()=="mag"
        assert dlg._serial>seq
        assert dlg._approved is None
        assert not dlg.export_wav.isEnabled() and not dlg.export_txt.isEnabled()
        assert dlg.height()>=dlg.main.minimumSize().height()
    finally:
        dlg._really_close=True
        dlg.close()
