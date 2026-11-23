"""V8.105 FIR Phase: resolvable LF + alias-free bulk-delay removal (shared core).

Root causes (QA_V8104_NOISE_ROBUSTNESS_AUDIT_20261104.md section 5e):
* default GUI range 30-16000 Hz always HOLD: the design rotated phase from
  30 Hz although a taps-long FIR cannot resolve it -> LF magnitude droop >1.5 dB;
* np.unwrap on Smaart's sparse MTW grid aliases any bulk delay (7.3 ms fitted
  as 2.16 ms), turning the excess-phase target into clipped garbage.
"""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.signal import freqz

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))

from remix_duo.core import traces as T
from remix_duo.core.filters import (design_phase_only_fir,
                                    PHASE_RESOLVE_CYCLES,
                                    FIR_PHASE_WORSE_TOL_DEG)
from remix_duo.core.fir_preview import phase_excess_rms
from remix_duo.core.phase_tools import remove_bulk_delay

FS = 48000
TRF = (Path.home() / 'Documents' / 'Smaart Suite' / 'Data' / 'Transfer Function'
       / 'Session Data')


def _mtw_like_grid():
    # Smaart Suite MTW TRF: 463 points, ~1.465 Hz at 100 Hz, ~11.7 Hz at 1 kHz,
    # far coarser at HF -> adjacent-bin phase steps exceed pi for a few ms.
    p = TRF / 'TUNNINNGGG-4.trf'
    if p.is_file():
        return T.read_trf(p).hz
    lo = np.arange(1.46, 200, 1.465)
    return np.unique(np.r_[lo, np.geomspace(200, 23000, 300)])


def _allpass(f, fc, q):
    s = 2j * np.pi * f
    w0 = 2 * np.pi * fc
    return (s * s - w0 / q * s + w0 * w0) / (s * s + w0 / q * s + w0 * w0)


@pytest.mark.parametrize('delay_ms', [7.3, 40., -3.])
def test_bulk_delay_is_recovered_without_unwrap_aliasing(delay_ms):
    f = _mtw_like_grid()
    sel = (f >= 30) & (f <= 16000)
    h = np.exp(-2j * np.pi * f * delay_ms / 1000)
    excess, tau = remove_bulk_delay(f[sel], h[sel], np.ones(sel.sum()))
    assert abs(tau * 1000 - delay_ms) < .02
    assert np.max(np.abs(np.rad2deg(excess))) < 1.


def test_pure_delay_trace_gets_transparent_fir_not_garbage():
    f = _mtw_like_grid()
    h = np.exp(-2j * np.pi * f * .0073)
    r = design_phase_only_fir(f, h, np.ones_like(f), taps=1024, fs=FS, lf=30, hf=16000)
    band = (r.hz >= 30) & (r.hz <= 16000)
    assert np.max(np.abs(r.actual_db[band])) < .1
    # Excess phase of a pure delay is zero: kernel must be a pure delay too.
    _, resp = freqz(r.taps, worN=r.hz[band][::50], fs=FS)
    dev = np.angle(resp * np.exp(2j * np.pi * r.hz[band][::50] * (1023 / (2 * FS))))
    assert np.max(np.abs(np.rad2deg(dev))) < 2.


@pytest.mark.parametrize('taps', [512, 1024, 2048])
def test_default_gui_range_with_crossover_allpass_is_not_held(taps):
    f = _mtw_like_grid()
    h = np.exp(-2j * np.pi * f * .040) * _allpass(f, 1000, .7)
    r = design_phase_only_fir(f, h, np.ones_like(f), taps=taps, fs=FS, lf=30, hf=16000)
    band = (r.hz >= 30) & (r.hz <= 16000)
    assert np.max(np.abs(r.actual_db[band])) <= 1.5
    assert r.phase_lf_hz == pytest.approx(max(30., PHASE_RESOLVE_CYCLES * FS / taps))
    before, after, gain, _ = phase_excess_rms(f, h, np.ones_like(f), r.taps, FS, 30, 16000)
    assert after < before, 'correction must reduce excess phase'


def test_resolvable_band_constant_is_documented():
    assert PHASE_RESOLVE_CYCLES == 12


@pytest.mark.parametrize('name', ['TUNNINNGGG-8', '4,8 ms delay-1', 'TUNNINNGGG-12'])
def test_phase_fir_never_exported_when_it_worsens_excess_phase(name):
    p = TRF / f'{name}.trf'
    if not p.is_file():
        pytest.skip('Reference TRF not on this machine')
    tr = T.read_trf(p)
    try:
        r = design_phase_only_fir(tr.hz, tr.h, tr.coherence, taps=1024, fs=FS, lf=30, hf=16000)
    except ValueError as exc:
        assert 'HOLD' in str(exc)
        return
    # Judge where the FIR actually acts; uncorrected LF bins would dilute it.
    before, after, _, _ = phase_excess_rms(tr.hz, tr.h, tr.coherence, r.taps, FS,
                                           r.phase_lf_hz, 16000)
    assert after <= before + FIR_PHASE_WORSE_TOL_DEG, (name, before, after)


@pytest.mark.parametrize('name', ['TUNNINNGGG-4', 'TUNNINNGGG-12', '0 delay-1'])
def test_real_trf_default_range_1024_taps_no_longer_held(name):
    p = TRF / f'{name}.trf'
    if not p.is_file():
        pytest.skip('Reference TRF not on this machine')
    tr = T.read_trf(p)
    r = design_phase_only_fir(tr.hz, tr.h, tr.coherence, taps=1024, fs=FS,
                              lf=30, hf=16000, strict=False)
    band = (r.hz >= 30) & (r.hz <= 16000)
    ripple=float(np.max(np.abs(r.actual_db[band])))
    assert len(r.taps)==1024 and np.isfinite(r.taps).all()
    if ripple>1.5:
        assert any("biên độ lệch" in warning for warning in r.warnings)
    assert np.all(np.isfinite(r.taps))


# V8.110: the never-worse gate must not turn floating-point noise into HOLD.
# On native Mac arm64 a pure-delay trace measured before=1.68e-12 deg,
# after=2.30e-12 deg and was refused as "0.0 -> 0.0 deg worse".
def _fake_excess(monkeypatch, before, after):
    from remix_duo.core import fir_preview
    monkeypatch.setattr(fir_preview, 'phase_excess_rms',
                        lambda *a, **k: (before, after, 0., 400))


def test_never_worse_gate_ignores_float_noise(monkeypatch):
    _fake_excess(monkeypatch, 1.6759859116043981e-12, 2.2979311588313756e-12)
    f = _mtw_like_grid()
    h = np.exp(-2j * np.pi * f * .0073)
    r = design_phase_only_fir(f, h, np.ones_like(f), taps=1024, fs=FS, lf=30, hf=16000)
    assert np.all(np.isfinite(r.taps))


@pytest.mark.parametrize('before,after', [(5., 8.), (0., .2), (10., 10.1)])
def test_never_worse_gate_still_holds_real_worsening(monkeypatch, before, after):
    _fake_excess(monkeypatch, before, after)
    f = _mtw_like_grid()
    h = np.exp(-2j * np.pi * f * .0073)
    with pytest.raises(ValueError, match='Excess Phase'):
        design_phase_only_fir(f, h, np.ones_like(f), taps=1024, fs=FS, lf=30, hf=16000)
