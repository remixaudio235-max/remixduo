"""V8.114: Smaart per-trace dB offset must change the physical SUM.

Live 2026-11-11: user moved 'sup bien 2-1' by +7 dB / -2 dB in Smaart; SUM
stayed still because it was computed from the unchanged .trf.
"""
from pathlib import Path
import numpy as np
import pytest
from remix_duo.core.traces import TFTrace, compute_sum, with_gain_db


def trace(name, h, f):
    return TFTrace(name, Path(name + ".trf"), f, h, np.full(len(f), .95), "Legacy", 1)


F = np.geomspace(20, 20000, 400)


def test_gain_is_linear_and_preserves_phase_and_coherence():
    t = trace("a", np.exp(-2j * np.pi * F * 1e-3), F)
    g = with_gain_db(t, 7.0)
    assert np.allclose(np.abs(g.h), 10 ** (7 / 20))
    assert np.allclose(np.angle(g.h), np.angle(t.h))
    assert g.coherence is t.coherence and g.hz is t.hz
    assert with_gain_db(t, 0.0) is t


def test_sum_moves_with_trace_gain_complex_physics():
    a = trace("a", np.ones(len(F), complex), F)
    b = trace("b", np.ones(len(F), complex), F)
    base = compute_sum(a, b).mag_db
    up = compute_sum(with_gain_db(a, 7.0), b).mag_db
    # |10^(7/20)+1| vs |1+1|: in-phase sum rises 20log10((2.2387+1)/2)=4.19 dB
    assert np.nanmedian(up - base) == pytest.approx(20 * np.log10((10 ** .35 + 1) / 2), abs=1e-6)
    # SUM never below the louder in-phase trace
    assert np.nanmin(up) >= 7.0 - 1e-9


@pytest.mark.parametrize("bad", [np.nan, np.inf, 40.5, -41])
def test_gain_rejects_out_of_range(bad):
    with pytest.raises(ValueError):
        with_gain_db(trace("a", np.ones(len(F), complex), F), bad)
