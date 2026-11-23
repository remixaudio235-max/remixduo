import os,json,struct
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import numpy as np
import pytest
from scipy.io import wavfile
from signal_tools_core_v813 import FIRResult
from fir_dsp_export_v872 import PROFILES,get_profile,validate,write_export

def example(taps=1024):
    coeff=np.zeros(taps);coeff[taps//2]=.5
    return FIRResult(coeff,48000,np.array([100.,1000.]),
                     np.array([0.,0.]),np.array([0.,0.]),10.6,"QA")

def test_all_profiles_have_explicit_formats_and_tap_rules():
    assert len(PROFILES)>=30
    for p in PROFILES:
        assert p["format"] in ("txt","csv","json","xml","wav","bin")
        assert p["extension"].startswith(".")
        assert p["max_taps"] is None or p["max_taps"]>=512

def test_six_interchange_format_roundtrip(tmp_path):
    expected={"Generic TXT":"txt","Generic CSV":"csv","Generic JSON":"json",
              "Generic XML":"xml","Generic WAV Float32":"wav",
              "Generic BIN Float32":"bin"}
    original=example()
    for name,fmt in expected.items():
        ext=get_profile(name)["extension"]
        path=tmp_path/(fmt+ext)
        report=write_export(original,name,path)
        assert report["device_native_verified"] is False
        assert path.exists()
        if fmt=="wav":
            rate,coeff=wavfile.read(path)
            assert rate==48000 and np.allclose(coeff,original.taps)
        elif fmt=="bin":
            assert np.allclose(np.fromfile(path,dtype="<f4"),original.taps)
        elif fmt=="json":
            obj=json.loads(path.read_text(encoding="utf8"))
            assert obj["taps"]==1024 and obj["sample_rate"]==48000
        elif fmt=="xml":
            from xml.etree import ElementTree
            root=ElementTree.parse(path).getroot()
            assert len(root.findall("Coeff"))==1024
        else:
            assert len(path.read_text(encoding="utf8").splitlines())==1024

def test_vendor_profiles_never_silently_truncate(tmp_path):
    sample=example(2048)
    name="Bose ControlSpace 512"
    path=tmp_path/"bose.txt"
    assert validate(sample,get_profile(name))
    with pytest.raises(ValueError,match="Tap count"):
        write_export(sample,name,path)
    assert not path.exists()
    assert write_export(example(512),name,path)["taps"]==512

def test_invalid_coefficients_and_filename_hold(tmp_path):
    sample=example()
    sample.taps[2]=np.nan
    with pytest.raises(ValueError,match="Invalid"):
        write_export(sample,"Generic BIN Float32",tmp_path/"invalid.bin")
    assert not (tmp_path/"invalid.bin").exists()
    with pytest.raises(ValueError,match="extension"):
        write_export(example(),"Generic WAV Float32",tmp_path/"wrong.txt")

def test_gui_profile_selector_offscreen():
    from PyQt6.QtWidgets import QApplication
    from signal_tools_gui_v813 import FIRDialog
    app=QApplication.instance() or QApplication([])
    fir=FIRDialog(object())
    try:
        assert fir.dsp_profile.count()==len(PROFILES)
        assert not fir.export_dsp.isEnabled()
        assert fir.export_dsp.text()=="Xuất DSP / Crossover"
    finally:
        fir._really_close=True;fir.close()
