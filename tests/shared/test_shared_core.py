import ast
import importlib
from pathlib import Path
import sys
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))

def test_canonical_modules_exist_and_legacy_aliases_share_globals():
    for old, new in [('trf_core','traces'), ('signal_tools_core_v813','filters'),
                     ('tf_display_smoothing','smoothing'),
                     ('remix_autoeq_v05_adapter','autoeq'),
                     ('fir_dsp_export_v872','fir_export')]:
        canonical = importlib.import_module('remix_duo.core.'+new)
        legacy = importlib.import_module(old)
        assert canonical is legacy
        canonical._qa_identity = object()
        assert legacy._qa_identity is canonical._qa_identity
        del canonical._qa_identity

def test_shared_core_imports_without_any_native_modules():
    import subprocess
    code = '''import sys, importlib.abc
class DenyNative(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, *args):
  if fullname.split('.')[0] in {'win32gui','win32api','win32process','winreg','ctypes','pywinauto','AppKit','Quartz','ScreenCaptureKit','PyQt6'}:
   raise AssertionError('native import: '+fullname)
sys.meta_path.insert(0,DenyNative())
import remix_duo.core.traces, remix_duo.core.filters, remix_duo.core.autoeq, remix_duo.core.fir_export, remix_duo.core.fir_preview
'''
    # NumPy itself uses ctypes. Block direct project dependencies through AST;
    # allow the installed numeric libraries to initialise before strict probe.
    code = 'import numpy, scipy.signal, scipy.optimize\n' + code
    import os
    result = subprocess.run([sys.executable,'-c',code], env={**os.environ,'PYTHONPATH':str(ROOT/'src')},capture_output=True,text=True)
    assert result.returncode == 0, result.stderr
    for p in (ROOT/'src/remix_duo/core').glob('*.py'):
        for node in ast.walk(ast.parse(p.read_text('utf-8'))):
            if isinstance(node,ast.Import): names=[x.name for x in node.names]
            elif isinstance(node,ast.ImportFrom): names=[node.module or '']
            else: continue
            assert not any(n.split('.')[0] in {'ctypes','winreg','win32gui','PyQt6','AppKit','Quartz'} for n in names), p

@pytest.mark.parametrize('fs',[44100,48000,96000])
@pytest.mark.parametrize('taps',[512,1024,4096])
def test_shared_fir_retains_flat_high_frequency_response(fs,taps):
    from remix_duo.core.filters import design_linear_phase_fir
    f=np.geomspace(20,20000,1000)
    result=design_linear_phase_fir(f,np.ones(f.size,complex),np.ones(f.size),taps=taps,fs=fs,source='flat',lf=30,hf=16000)
    from scipy.signal import freqz
    _, h = freqz(result.taps,worN=[16000],fs=fs)
    assert abs(20*np.log10(abs(h[0]))) < .02
