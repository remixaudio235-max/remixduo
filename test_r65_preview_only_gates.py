from types import SimpleNamespace as NS

import numpy as np

from native_eq_mag_v06 import build_state
from signal_tools_gui_v813 import FIRDialog, fir_export_hold_vn
from fir_native_v846 import native_trace_hold_reason


def test_preview_only_fir_never_authorizes_export():
    unsafe=NS(result=NS(warnings=("PREVIEW_ONLY: quality evidence missing",)))
    safe=NS(result=NS(warnings=("advisory only",)))
    assert not FIRDialog._quality_export_ok(unsafe)
    assert FIRDialog._quality_export_ok(safe)


def test_missing_result_never_authorizes_export():
    assert not FIRDialog._quality_export_ok(NS(result=None))


def test_fir_hold_toast_guides_lf_hf_for_coherence_and_provenance():
    result=NS(warnings=(
        "PREVIEW_ONLY: FIR Phase LF coherence≥0.65 coverage 20% < 55%",))
    text=fir_export_hold_vn(result,False)
    assert "LF/HF" in text
    assert "coherence ≥0.65" in text
    assert "1 Trace" in text and "3/3" in text


def test_native_trace_hold_explains_viewport_recovery():
    text=native_trace_hold_reason()
    assert "LF/HF" in text
    assert "zoom trục dB" in text
    assert "TẠO FIR lại" in text


def test_dsp_export_rechecks_preview_quality_even_when_provenance_is_current():
    notices=[]
    dialog=NS(
        result=NS(mode="phase",warnings=("PREVIEW_ONLY: quality evidence missing",)),
        engine=NS(graph_mag=None),
        _proof_current=lambda **_kwargs: True,
        _quality_export_ok=lambda: False,
        notice=lambda message,_preferred=None: notices.append(message),
    )
    FIRDialog.save_dsp_profile(dialog,"generic_txt")
    assert notices and "LF/HF" in notices[0]


def test_autoeq_unsafe_status_can_render_original_bypass_preview():
    freq=np.geomspace(20.0,20_000.0,200)
    transfer=np.exp(-2j*np.pi*freq*.001)
    source=build_state(freq,transfer,np.ones_like(freq),(),fs=48_000,
                       source_index=0,source_name="preview",revision=1,
                       allow_bypass=True)
    assert np.allclose(source.after_db,source.original_db)
    assert source.peqs==()
