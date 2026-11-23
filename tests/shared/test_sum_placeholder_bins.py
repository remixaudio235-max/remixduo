"""V8.115: Smaart 'no data' bins must not create a fake SUM comb.

Live 2026-11-11: Smaart stores bins it could not measure (band-limited
measurement) as H = 1+0j with coherence 0 (89-263 of 463 bins per TRF, exact
signature, never seen on real data). With a 4.80 ms alignment delay the two
placeholders summed to 1 + e^{-jwt}: exact cancellations every 208 Hz,
down to -281 dB, while both traces looked flat on Smaart.
If only one trace is missing, its contribution is treated as 0+0j and the
display falls back to the measured trace.  If both are missing, SUM remains
undefined and is not drawn.
"""
from pathlib import Path
import numpy as np
from remix_duo.core.traces import TFTrace, compute_sum

F = np.geomspace(20, 20000, 463)


def trace(name, h, coh):
    return TFTrace(name, Path(name + ".trf"), F, h, coh, "Legacy", 1)


def band_limited(seed, cutoff):
    r = np.random.default_rng(seed)
    h = (1 + .2 * r.random(len(F))) * np.exp(1j * r.uniform(-.3, .3, len(F)))
    coh = np.full(len(F), .9)
    hi = F > cutoff
    h[hi] = 1 + 0j
    coh[hi] = 0.0
    return trace(f"t{seed}", h, coh), hi


def test_single_trace_placeholder_falls_back_to_measured_trace():
    a, hi_a = band_limited(1, 4000)
    b, hi_b = band_limited(2, 6000)
    s = compute_sum(a, b, delay_ms=4.80)
    only_a = hi_b & ~hi_a
    only_b = hi_a & ~hi_b
    expected_a = 20 * np.log10(np.abs(a.h[only_a]))
    expected_b = 20 * np.log10(np.abs(b.h[only_b]))
    assert np.allclose(s.mag_db[only_a], expected_a)
    assert np.allclose(s.mag_db[only_b], expected_b)
    assert not np.any(s.valid[only_a | only_b])  # fallback, not a 2-trace proof
    both = hi_a & hi_b
    assert np.all(np.isnan(s.mag_db[both]))
    finite = s.mag_db[np.isfinite(s.mag_db)]
    assert finite.min() > -60, finite.min()        # no -280 dB fake notches


def test_placeholder_bins_ignored_by_smoothing():
    a, hi_a = band_limited(1, 4000)
    b, _ = band_limited(2, 4000)
    s = compute_sum(a, b, delay_ms=4.80, mag_oct=1 / 6)
    measured = ~hi_a
    near = measured & (F > 2500)
    assert np.nanmin(s.mag_db[near]) > -20       # edge not dragged by notches


def test_both_placeholders_remain_hidden():
    a, hi = band_limited(1, 4000)
    b, _ = band_limited(2, 4000)
    s = compute_sum(a, b, delay_ms=8.1, invert_trace2=True)
    assert np.all(np.isnan(s.mag_db[hi]))
    assert np.all(np.isnan(s.phase_deg[hi]))


def test_real_low_coherence_bins_still_computed():
    a, _ = band_limited(1, 30000)
    b, _ = band_limited(2, 30000)
    a = trace("lowcoh", a.h, np.full(len(F), .3))
    s = compute_sum(a, b)
    assert np.all(np.isfinite(s.mag_db))
