import os
from pathlib import Path
import subprocess
import sys

def test_canonical_pytest_does_not_load_legacy_windows_gui():
    root=Path(__file__).resolve().parents[2]
    code='''import importlib.abc,sys
class Deny(importlib.abc.MetaPathFinder):
 def find_spec(self,name,*args):
  if name=='signal_tools_gui_v813': raise AssertionError('legacy Windows GUI imported by portable tests')
sys.meta_path.insert(0,Deny())
import pytest
raise SystemExit(pytest.main(['-q','tests/contracts/test_mac_native.py::test_ax_does_not_mistake_selected_highlight_for_enabled_trace','--tb=short']))
'''
    r=subprocess.run([sys.executable,'-c',code],cwd=root,capture_output=True,text=True,
        env={**os.environ,'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','QT_QPA_PLATFORM':'offscreen'})
    assert r.returncode==0,r.stdout+r.stderr
