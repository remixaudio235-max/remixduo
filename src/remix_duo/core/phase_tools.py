"""V8.105 alias-free bulk-delay removal for sparse Smaart TF grids (shared core).

Smaart Suite MTW TRFs store ~463 log-spaced points. At HF the bin spacing is
hundreds of Hz, so a bulk delay of a few ms rotates phase by more than pi
between adjacent bins and `np.unwrap` silently aliases (7.3 ms fitted as
2.16 ms). Estimate the delay coherently on the densely sampled band first,
de-rotate, and only then unwrap the small residual for the linear fit.
"""
from __future__ import annotations

import numpy as np

COARSE_MAX_HZ = 1000.
SEARCH_RANGE_S = .300
SEARCH_STEP_S = 5e-5
COARSE_SEARCH_STEP_S = 5e-4
_CHUNK = 512


def remove_bulk_delay(f, h, weights):
    """Return (excess_phase_rad, bulk_delay_s) for H(f)=|H|e^{-j2*pi*f*tau}*excess.

    Excess has the best weighted linear phase (delay + constant) removed,
    exactly like the previous polyfit contract, but without unwrap aliasing.
    """
    f = np.asarray(f, float)
    h = np.asarray(h, complex)
    w = np.asarray(weights, float)
    unit = h / np.maximum(np.abs(h), 1e-300)
    dense = f <= COARSE_MAX_HZ
    if np.count_nonzero(dense) < 8:
        dense = np.ones_like(f, dtype=bool)
    wd, ud, fd = w[dense], unit[dense], f[dense]
    def strongest(taus):
        best_score, best_tau = -1., 0.
        for k in range(0, len(taus), _CHUNK):
            chunk = taus[k:k + _CHUNK]
            score = np.abs((wd * ud) @ np.exp(2j * np.pi * np.outer(fd, chunk)))
            i = int(np.argmax(score))
            if score[i] > best_score:
                best_score, best_tau = float(score[i]), float(chunk[i])
        return best_tau

    # A full 50 us sweep creates ~12k complex columns every time this safety
    # metric runs (up to six times per Phase FIR). Locate the broadband peak
    # at 0.5 ms first, then retain the original 50 us resolution locally.
    coarse_grid = np.arange(-SEARCH_RANGE_S,
                            SEARCH_RANGE_S + COARSE_SEARCH_STEP_S / 2,
                            COARSE_SEARCH_STEP_S)
    coarse = strongest(coarse_grid)
    lo = max(-SEARCH_RANGE_S, coarse - COARSE_SEARCH_STEP_S)
    hi = min(SEARCH_RANGE_S, coarse + COARSE_SEARCH_STEP_S)
    fine_grid = np.arange(lo, hi + SEARCH_STEP_S / 2, SEARCH_STEP_S)
    coarse = strongest(fine_grid)
    residual = np.unwrap(np.angle(h * np.exp(2j * np.pi * f * coarse)))
    line = np.polyfit(f, residual, 1, w=np.sqrt(w))
    excess = residual - np.polyval(line, f)
    return excess, coarse - float(line[0]) / (2 * np.pi)
