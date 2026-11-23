from pathlib import Path
import tempfile,struct
import numpy as np
from signal_tools_core_v813 import *
from trf_core import read_trf
root=Path.home()/"Documents/Smaart Suite/Data/Transfer Function/Session Data"
a=read_trf(root/"4,8 ms delay-1.trf")
for name in ("4,8 ms delay-1.trf","SUb.trf"):
    trace=read_trf(root/name)
    r=auto_peq(trace.hz,trace.h,trace.coherence,0,8)
    print("EQ",name,"FILTERS",len(r.peqs),"RMS",r.rms_before,r.rms_after,"BINS",r.bins,flush=True)
    assert len(r.peqs)<=8
    assert r.bins>=20
    assert np.isfinite(r.after_db).all()
    assert np.isfinite(r.correction_db).all()
    assert all(-12<=p.gain_db<=6 for p in r.peqs)
    assert r.rms_after<=r.rms_before+1e-6,(r.rms_before,r.rms_after)
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/"eq.txt"
        save_peq_text(path,r)
        assert path.stat().st_size>60
    fir=design_linear_phase_fir(trace.hz,trace.h,trace.coherence,
                                taps=1024,source=name)
    print("FIR",name,"TAPS",len(fir.taps),"GROUP_DELAY_MS",fir.latency_ms,
          "RMS",float(np.sqrt(np.mean(fir.taps**2))),flush=True)
    assert np.isfinite(fir.taps).all()
    assert np.max(np.abs(fir.taps-fir.taps[::-1]))<1e-12
    assert abs(fir.latency_ms-1023/2/48000*1000)<1e-8
    with tempfile.TemporaryDirectory() as d:
        txt=Path(d)/"fir.txt"
        wav=Path(d)/"fir.wav"
        save_fir_txt(txt,fir)
        save_fir_wav_float(wav,fir)
        assert txt.read_text(encoding="utf8").count("\n")>1024
        raw=wav.read_bytes()
        assert raw[:4]==b"RIFF" and raw[8:12]==b"WAVE"
        assert struct.unpack_from("<H",raw,20)[0]==3
        assert struct.unpack_from("<I",raw,24)[0]==48000
        assert len(raw)==44+4*1024
print("V813_OFFLINE_PEQ_FIR_QA_PASS")
