import time
import threading
from pathlib import Path
import numpy as np
import pytest

def trace(name='input',delay=0):
    from remix_duo.core.traces import synthetic
    return synthetic(name,np.geomspace(20,20000,600),delay_ms=delay)

def test_offline_request_snapshots_input_and_requires_explicit_fs():
    from remix_duo.application.design import DesignRequest, calculate
    a=trace()
    with pytest.raises(ValueError,match='Fs'): DesignRequest.create('fir',a,fs=None)
    req=DesignRequest.create('fir',a,fs=48000)
    a.h[:]=2
    assert np.all(req.trace.h==1) and not req.trace.h.flags.writeable
    result=calculate(req)
    assert result.source=='input' and result.fs==48000

def test_shared_phase_uses_same_pair_and_no_native_claim():
    from remix_duo.application.design import DesignRequest, calculate
    r=calculate(DesignRequest.create('phase',trace('a'),trace('b',2),fs=48000))
    assert abs(r[0].delay_ms+2)<.11

def test_workspace_is_responsive_and_discards_result_after_input_change(monkeypatch):
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer
    from remix_duo.ui import workspace
    from remix_duo.application.design import DesignRequest
    app=QApplication.instance() or QApplication([])
    start=threading.Event(); release=threading.Event()
    def slow(request): start.set();release.wait(3);return object()
    monkeypatch.setattr(workspace,'calculate',slow)
    widget=workspace.Workspace()
    beats=[]
    timer=QTimer();timer.timeout.connect(lambda:beats.append(1));timer.start(5)
    widget.submit_request(DesignRequest.create('fir',trace(),fs=48000))
    assert start.wait(1)
    end=time.monotonic()+.1
    while time.monotonic()<end: app.processEvents();time.sleep(.002)
    assert len(beats)>3
    widget.invalidate()
    release.set()
    end=time.monotonic()+.2
    while time.monotonic()<end: app.processEvents();time.sleep(.002)
    assert widget.result is None
    assert not widget.export_button.isEnabled()
    widget.close();timer.stop()

def test_common_widget_reused_in_windows_gui():
    import sys
    if sys.platform!='win32': pytest.skip('Windows integration identity only')
    from remix_duo.ui.widgets import MiniPlot,show_notice
    import signal_tools_gui_v813 as windows
    assert windows.MiniPlot is MiniPlot and windows.show_notice is show_notice

def test_single_trace_tool_does_not_validate_unused_trace2(monkeypatch):
    from PyQt6.QtWidgets import QApplication
    from remix_duo.ui.workspace import Workspace
    from remix_duo.core.traces import synthetic
    app=QApplication.instance() or QApplication([])
    widget=Workspace()
    widget.traces=[trace(),synthetic('96k',np.geomspace(20,40000,600))]
    widget.fs.setCurrentIndex(widget.fs.findData(48000))
    widget.tool.setCurrentIndex(widget.tool.findData('fir'))
    submitted=[]
    monkeypatch.setattr(widget,'submit_request',submitted.append)
    widget.run_design()
    assert len(submitted)==1
    assert submitted[0].reference is None
    from remix_duo.application.design import DesignRequest
    assert DesignRequest.create('eq',*widget.traces,fs=48000).reference is None
    widget.close()

def test_fir_plot_shows_original_times_filter_not_filter_alone():
    from dataclasses import replace
    from scipy.signal import freqz
    from PyQt6.QtWidgets import QApplication
    from remix_duo.ui.workspace import Workspace
    from remix_duo.application.design import DesignRequest,calculate
    app=QApplication.instance() or QApplication([])
    t=trace();t=replace(t,h=t.h*10**(6/20))
    req=DesignRequest.create('fir',t,fs=48000)
    widget=Workspace();widget.request=req
    result=calculate(req)
    widget._finished(widget._generation,result,None)
    assert widget.plot.freq.shape==t.hz.shape
    assert np.allclose(widget.plot.freq,t.hz)
    assert np.allclose(widget.plot.before,6)
    _,response=freqz(result.taps,worN=t.hz,fs=48000)
    assert np.allclose(widget.plot.after,6+20*np.log10(np.maximum(abs(response),1e-12)))
    widget.close()
