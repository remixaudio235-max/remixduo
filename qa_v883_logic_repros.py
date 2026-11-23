"""Offline audit probes. Exit 1 means confirmed defects, not a test-run crash.

No Smaart, UIA, soundcard, license or hardware operations. Native reads used by
the observer are mocked. Qt uses the offscreen platform. No product code edits.
"""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import time
import numpy as np
from scipy.signal import freqz


def probes():
    from signal_tools_core_v813 import design_linear_phase_fir
    f=np.geomspace(20,20000,1400)
    flat=design_linear_phase_fir(f,np.ones_like(f,dtype=complex),np.ones_like(f))
    q=np.array([1000.,10000.,16000.])
    _,response=freqz(flat.taps,worN=q,fs=48000)
    db=20*np.log10(abs(response))
    yield dict(id='FIR_FLAT_UNITY',defect=bool(np.max(abs(db))>.25),
               expected='0dB within 0.25dB on flat input',
               measured=dict(zip(q.tolist(),db.tolist())))

    import smaart_fs_sync_v841 as fs
    import smaart_runtime_paths_v868 as paths
    import xml.etree.ElementTree as ET
    def config(file,rate):
        root=ET.Element('Root'); s=ET.SubElement(root,'Smaart-Config')
        g=ET.SubElement(s,'Global'); ET.SubElement(g,'SampleRate').text=str(rate)
        for group,row in [('Sources','Source1'),('Dests','Dest1')]:
            p=ET.SubElement(s,group); n=ET.SubElement(p,row)
            ET.SubElement(n,'SampleRate').text=str(rate)
        ET.ElementTree(root).write(file,encoding='utf-8')
    with TemporaryDirectory() as td:
        real=Path(td)/'redirected.xml'; stale=Path(td)/'old.xml'
        config(real,96000); config(stale,48000)
        with patch.object(paths,'running_major',return_value=9), \
             patch.object(paths,'saved_config',return_value=real), \
             patch.object(fs,'CONFIG',stale):
            actual=fs.read_saved_smaart_fs()
            yield dict(id='REDIRECTED_SUITE9_FS',defect=actual is None or actual.hz!=96000,
                       expected=96000,measured=actual.hz if actual else None)

    import live_sync_v7 as live
    import smaart8_api3_readonly_v868 as api
    with TemporaryDirectory() as td:
        folder=Path(td); a=folder/'a.trf'; b=folder/'b.trf'
        # Observer token only needs stat metadata; no TRF parser is called.
        a.write_bytes(b'a'); b.write_bytes(b'b')
        obs=live.LiveDataBarV7(folder)
        obs.ready=True; obs.hwnd=123; obs.order=[a,b]
        obs.states={0:'on',1:'off'}; obs.layout=(1000,800)
        obs.last_scan=time.perf_counter()-1000
        bar=SimpleNamespace(iface_range_value=SimpleNamespace(CurrentValue=0))
        obs.header=(bar,0,0,800,0); obs.last_filecheck=time.perf_counter()
        with patch.object(api,'process_smaart_major',return_value=9), \
             patch.object(live.win32gui,'GetWindowRect',return_value=(0,0,1000,800)), \
             patch.object(live,'printwindow_image',return_value=None), \
             patch.object(live,'_page',return_value={1:'off'}):
            for _ in range(3):obs.poll(123)
            yield dict(id='UNSEEN_SELECTED_ROW_REAUTHORIZED',
                       defect=obs.current_single() is not None,
                       expected='No fresh authorization without observing selected row',
                       measured=dict(authorized=obs.current_single() is not None,
                                     selected_row=0,only_observed_row=1))

    from trf_core import synthetic,matched
    a=synthetic('a',np.array([100.,105.,110.]))
    b=synthetic('b',np.array([100.,110.]),delay_ms=20.)
    _,_,hb,_=matched(a,b)
    error_db=float(20*np.log10(abs(hb[1])))
    yield dict(id='PURE_DELAY_INTERPOLATION',defect=abs(error_db)>.25,
               expected='Unit amplitude for unit-amplitude pure delay',
               measured=dict(at_hz=105,magnitude=float(abs(hb[1])),error_db=error_db))

    from PyQt6.QtWidgets import QApplication
    from signal_tools_gui_v813 import FIRDialog
    from remix_layout_v856 import style_fir
    app=QApplication.instance() or QApplication([])
    fir=FIRDialog(object())
    try:
        style_fir(fir,fir._action_row); fir.show(); app.processEvents()
        overlap=fir.details.geometry().intersects(fir.dsp_profile.geometry())
        yield dict(id='FIR_LAYOUT_OVERLAP',defect=overlap,
                   expected='No details/profile overlap',
                   measured=dict(overlap=overlap,height=fir.height(),
                                 layout_minimum=fir.main.minimumSize().height()))
    finally:
        fir._really_close=True; fir.close()


if __name__=='__main__':
    results=list(probes())
    print(json.dumps(results,ensure_ascii=True,indent=2),flush=True)
    print('CONFIRMED_DEFECTS',sum(r['defect'] for r in results),flush=True)
    raise SystemExit(1 if any(r['defect'] for r in results) else 0)
