import numpy as np
from types import SimpleNamespace

from tf_display_smoothing import SMOOTH_OPTIONS
from trf_core import synthetic, compute_sum
from native_eq_mag_v06 import build_state, _display_db
from signal_tools_gui_v813 import _fir_design_and_preview
from fir_native_v846 import fir_phase_points


SMOOTHING=(1/3,1/6,1/12,1/24,1/48)


def _measurement():
    f=np.geomspace(20.,20_000.,480)
    phase=-2*np.pi*f*.0012+.5*np.sin(np.log(f)*3)
    mag=10**(2*np.sin(np.log(f)*2)/20)
    return f,mag*np.exp(1j*phase),np.ones_like(f)


def test_all_requested_smoothing_values_are_public_options():
    values={float(v) for _,v in SMOOTH_OPTIONS}
    assert set(SMOOTHING)<=values


def test_auto_phase_sum_renders_at_every_smaart_smoothing():
    f=np.geomspace(20.,20_000.,480)
    a=synthetic("A",f,db=0.,delay_ms=0.)
    b=synthetic("B",f,db=-3.,delay_ms=.8)
    for width in SMOOTHING:
        result=compute_sum(a,b,mag_oct=width,phase_oct=width,coh_gate=0.)
        assert np.isfinite(result.mag_db).all()
        assert np.isfinite(result.phase_deg).all()


def test_auto_eq_preview_tracks_every_smaart_mag_smoothing():
    f,h,coh=_measurement()
    rendered=[]
    for width in SMOOTHING:
        source=build_state(f,h,coh,(),fs=48_000,source_index=0,
                           source_name="trace",revision=1,
                           allow_bypass=True,display_smooth_oct=width)
        curve=_display_db(source,source.after_db)
        assert curve.shape==f.shape and np.isfinite(curve).all()
        rendered.append(curve)
    assert not np.allclose(rendered[0],rendered[-1])


def test_auto_fir_preview_rerenders_at_every_smaart_phase_smoothing():
    f,h,coh=_measurement()
    _,source=_fir_design_and_preview(
        f,h,coh,512,48_000,"trace","digest",1,
        500,2500,"phase",False,1/6)
    assert source.original_complex is not None
    assert source.compensated_response is not None
    curves=[]
    for width in SMOOTHING:
        frame=SimpleNamespace(
            phase_verified=True,phase=(0,0,1200,400),
            phase_top=180.,phase_span=360.,phase_smooth_oct=width)
        points,valid=fir_phase_points(source,frame)
        assert points.shape==(len(f),2) and valid.any()
        curves.append(points[:,1])
    assert not np.allclose(curves[0],curves[-1],equal_nan=True)
