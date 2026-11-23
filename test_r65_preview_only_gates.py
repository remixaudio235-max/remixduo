from types import SimpleNamespace as NS

import numpy as np

from native_eq_mag_v06 import build_state
from signal_tools_gui_v813 import FIRDialog


def test_preview_only_fir_never_authorizes_export():
    unsafe=NS(result=NS(warnings=("PREVIEW_ONLY: quality evidence missing",)))
    safe=NS(result=NS(warnings=("advisory only",)))
    assert not FIRDialog._quality_export_ok(unsafe)
    assert FIRDialog._quality_export_ok(safe)


def test_missing_result_never_authorizes_export():
    assert not FIRDialog._quality_export_ok(NS(result=None))


def test_autoeq_unsafe_status_can_render_original_bypass_preview():
    freq=np.geomspace(20.0,20_000.0,200)
    transfer=np.exp(-2j*np.pi*freq*.001)
    source=build_state(freq,transfer,np.ones_like(freq),(),fs=48_000,
                       source_index=0,source_name="preview",revision=1,
                       allow_bypass=True)
    assert np.allclose(source.after_db,source.original_db)
    assert source.peqs==()
