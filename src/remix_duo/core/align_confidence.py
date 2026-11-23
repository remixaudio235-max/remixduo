"""V8.104 AutoPhase confidence for noisy measurements (shared core).

The app does not estimate the TF; Smaart does. With few Smaart averages the
coherence (MSC) estimate is biased high, so noisy bins pass the 0.60 gate and
AutoPhase can return a wrong delay with no warning. This module does NOT alter
the solver result; it only judges how much the evidence supports it:

* agreement  - bin bootstrap: fraction of resampled ROIs whose best route
               (polarity + delay within tol) equals the reported best route.
               Measures actual bin-to-bin consistency without trusting coherence.
* saturation - fraction of ROI bins with coherence >= 0.995 combined with the
               magnitude roughness of each trace. Perfect coherence on a smooth
               response is a clean loopback (OK); perfect coherence on a rough
               response is the nd=1 estimator artefact (HOLD).

Evidence: QA_V8104_NOISE_ROBUSTNESS_AUDIT_20261104.md (Welch simulation and
113 real Smaart Suite TRFs: real max roughness 0.24 dB at saturation >= 0.6,
nd=1 wind/fan >= 5 dB).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from .traces import (ALIGN_CHUNK, ALIGN_MIN_BINS, alignment_delays,
                     alignment_penalty_db, alignment_roi)

Verdict = Literal['OK', 'LOW', 'HOLD_SATURATED', 'INSUFFICIENT']

AGREEMENT_OK = .80
SATURATED_COH = .995
SATURATED_FRACTION_HOLD = .60
ROUGHNESS_HOLD_DB = 2.0
BOOTSTRAP_REPLICAS = 64
BOOTSTRAP_SEED = 0x8104
ROUTE_TOLERANCE_MS = .3


@dataclass(frozen=True)
class AlignConfidence:
    verdict: Verdict
    agreement: float
    roi_bins: int
    saturated_fraction: float
    mag_roughness_db: float


def magnitude_roughness_db(trace, lf: float, hf: float) -> float:
    """Median |2nd difference| of dB magnitude in LF..HF (delay-insensitive)."""
    f = np.asarray(trace.hz, float)
    sel = (f >= lf) & (f <= hf)
    if np.count_nonzero(sel) < 3:
        return 0.
    db = 20 * np.log10(np.maximum(np.abs(np.asarray(trace.h)[sel]), 1e-15))
    return float(np.median(np.abs(db[1:-1] - .5 * (db[:-2] + db[2:]))))


def _bootstrap_agreement(f, h1, h2, weights, delays, best_invert, best_delay,
                         replicas, seed, tol_ms):
    n = len(f)
    rng = np.random.default_rng(seed)
    counts = rng.multinomial(n, np.full(n, 1. / n), size=replicas).T  # n x B
    w = counts * weights[:, None]
    denom = w.sum(0)
    best_score = np.full(replicas, -np.inf)
    best_inv = np.zeros(replicas, dtype=bool)
    best_d = np.zeros(replicas)
    for invert in (False, True):
        for k in range(0, len(delays), ALIGN_CHUNK):
            d = delays[k:k + ALIGN_CHUNK]
            s = (alignment_penalty_db(f, h1, h2, d, invert) @ w) / denom  # chunk x B
            idx = np.argmax(s, axis=0)
            top = s[idx, np.arange(replicas)]
            better = top > best_score
            best_score = np.where(better, top, best_score)
            best_inv = np.where(better, invert, best_inv)
            best_d = np.where(better, d[idx], best_d)
    same = (best_inv == bool(best_invert)) & (np.abs(best_d - float(best_delay)) <= tol_ms)
    return float(np.mean(same))


def assess_alignment(a, b, best, *, lf, hf, coh_gate=.60, max_delay_ms=180.,
                     step_ms=.1, replicas=BOOTSTRAP_REPLICAS,
                     seed=BOOTSTRAP_SEED, tol_ms=ROUTE_TOLERANCE_MS) -> AlignConfidence:
    """Judge an AutoPhase best Candidate; deterministic for identical input."""
    f, h1, h2, coh = alignment_roi(a, b, lf, hf, coh_gate)
    n = len(f)
    saturated = float(np.mean(coh >= SATURATED_COH)) if n else 0.
    rough = max(magnitude_roughness_db(a, lf, hf), magnitude_roughness_db(b, lf, hf))
    if n < ALIGN_MIN_BINS:
        return AlignConfidence('INSUFFICIENT', 0., n, saturated, rough)
    agreement = _bootstrap_agreement(
        f, h1, h2, coh ** 2, alignment_delays(max_delay_ms, step_ms),
        best.invert_trace2, best.delay_ms, int(replicas), seed, tol_ms)
    if saturated >= SATURATED_FRACTION_HOLD and rough > ROUGHNESS_HOLD_DB:
        verdict: Verdict = 'HOLD_SATURATED'
    elif agreement < AGREEMENT_OK:
        verdict = 'LOW'
    else:
        verdict = 'OK'
    return AlignConfidence(verdict, agreement, n, saturated, rough)
