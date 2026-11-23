"""V8.104 AutoPhase confidence under noise (shared core, no native imports).

Evidence source: QA_V8104_NOISE_ROBUSTNESS_AUDIT_20261104.md. The noise model is
a dual-channel Welch H1/MSC estimate with nd averages, output (mic) noise only.
"""
from pathlib import Path
import sys
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))

from remix_duo.core import traces as T
from remix_duo.core.align_confidence import (
    AlignConfidence, assess_alignment, AGREEMENT_OK, SATURATED_FRACTION_HOLD)

F = np.geomspace(20, 20000, 1600)
DELAY = 3.7


def _welch(rng, h, g2, nd):
    snr = g2 / (1 - g2)
    shape = (nd, len(F))
    X = (rng.standard_normal(shape) + 1j * rng.standard_normal(shape)) / np.sqrt(2)
    N = (rng.standard_normal(shape) + 1j * rng.standard_normal(shape)) / np.sqrt(2)
    Y = h * X + N * np.abs(h) / np.sqrt(snr)
    gxx = (np.abs(X) ** 2).sum(0); gyy = (np.abs(Y) ** 2).sum(0)
    gxy = (np.conj(X) * Y).sum(0)
    return gxy / gxx, np.clip(np.abs(gxy) ** 2 / (gxx * gyy), 0, 1)


def _pair(rng, g2, nd):
    a = T.TFTrace('A', Path('A.trf'), F, *_welch(rng, np.ones(len(F)), g2, nd), 'SIM', 0)
    b = T.TFTrace('B', Path('B.trf'), F,
                  *_welch(rng, np.exp(2j * np.pi * F * DELAY / 1000), g2, nd), 'SIM', 0)
    return a, b


def _wind():
    return np.clip(1 / (1 + 6 * (100 / F) ** 2), 1e-3, .999)


def _reference_auto_align(a, b, lf, hf, coh_gate=.6, max_delay_ms=180., step_ms=.1, top_k=4):
    """Frozen copy of the pre-V8.104 solver: refactor must stay bit-identical."""
    f, h1, h2, coh = T.matched(a, b)
    roi = (f >= lf) & (f <= hf) & (coh >= coh_gate) & (np.abs(h1) > 1e-12) & (np.abs(h2) > 1e-12)
    if np.count_nonzero(roi) < 12:
        return []
    f, h1, h2, coh = f[roi], h1[roi], h2[roi], coh[roi]
    weights = coh ** 2
    norm = np.maximum(np.abs(h1) + np.abs(h2), 1e-15)
    delays = np.arange(-max_delay_ms, max_delay_ms + step_ms / 4., step_ms)
    results = []
    for invert in (False, True):
        sign = -1 if invert else 1
        scores = np.empty(len(delays))
        for k in range(0, len(delays), 128):
            d = delays[k:k + 128]
            shifted = h2[None, :] * np.exp(-2j * np.pi * np.outer(d / 1000, f))
            ratio = np.maximum(np.abs(h1[None, :] + sign * shifted) / norm[None, :], 1e-5)
            scores[k:k + 128] = (20 * np.log10(ratio) @ weights) / weights.sum()
        results.extend(T.Candidate(float(d), invert, float(s), len(f)) for d, s in zip(delays, scores))
    out = []
    for item in sorted(results, key=lambda x: x.score_db, reverse=True):
        if all(p.invert_trace2 != item.invert_trace2 or abs(p.delay_ms - item.delay_ms) > .45 for p in out):
            out.append(item)
            if len(out) >= top_k:
                break
    return out


@pytest.mark.parametrize('seed', [0, 1, 2])
def test_auto_align_is_bit_identical_after_shared_penalty_refactor(seed):
    rng = np.random.default_rng(seed)
    a, b = _pair(rng, np.full(len(F), .9), 4)
    assert T.auto_align(a, b, lf=60, hf=400, max_delay_ms=30) == \
        _reference_auto_align(a, b, 60, 400, max_delay_ms=30)


def test_clean_synthetic_pair_is_confident():
    a, b = T.synthetic('a', F), T.synthetic('b', F, delay_ms=2)
    best = T.auto_align(a, b, lf=60, hf=200, max_delay_ms=20)[0]
    c = assess_alignment(a, b, best, lf=60, hf=200, max_delay_ms=20)
    assert isinstance(c, AlignConfidence)
    # Noise-free coherence 1.0 is SATURATED but smooth: an electrical loopback
    # must never be held merely because coherence is perfect.
    assert c.saturated_fraction == 1.0
    assert c.verdict == 'OK' and c.agreement >= .99
    assert c.roi_bins == best.roi_bins


def test_low_average_saturated_noisy_coherence_is_held():
    # nd=1: Smaart MSC estimate is identically 1.0 although the mic is in wind.
    rng = np.random.default_rng(3)
    a, b = _pair(rng, _wind(), 1)
    res = T.auto_align(a, b, lf=60, hf=200, max_delay_ms=20)
    assert res, 'saturated coherence passes the 0.60 gate (the audited defect)'
    c = assess_alignment(a, b, res[0], lf=60, hf=200, max_delay_ms=20)
    assert c.saturated_fraction >= SATURATED_FRACTION_HOLD
    assert c.mag_roughness_db > 2.0
    assert c.verdict == 'HOLD_SATURATED'


def test_every_wrong_wind_result_is_flagged_and_clean_is_not():
    rng = np.random.default_rng(7)
    wrong_flagged, wrong_total, clean_flagged = 0, 0, 0
    for _ in range(12):
        a, b = _pair(rng, _wind(), 2)
        res = T.auto_align(a, b, lf=60, hf=200, max_delay_ms=20)
        if not res:
            continue
        c = assess_alignment(a, b, res[0], lf=60, hf=200, max_delay_ms=20)
        if res[0].invert_trace2 or abs(res[0].delay_ms - DELAY) > .3:
            wrong_total += 1
            wrong_flagged += c.verdict != 'OK'
    for _ in range(6):
        a, b = _pair(rng, np.full(len(F), .98), 16)
        res = T.auto_align(a, b, lf=60, hf=200, max_delay_ms=20)
        c = assess_alignment(a, b, res[0], lf=60, hf=200, max_delay_ms=20)
        clean_flagged += c.verdict != 'OK'
    assert wrong_total >= 3, 'scenario must actually produce wrong solves'
    assert wrong_flagged == wrong_total
    assert clean_flagged == 0


def test_assessment_is_deterministic():
    rng = np.random.default_rng(9)
    a, b = _pair(rng, _wind(), 2)
    res = T.auto_align(a, b, lf=60, hf=200, max_delay_ms=20)
    one = assess_alignment(a, b, res[0], lf=60, hf=200, max_delay_ms=20)
    two = assess_alignment(a, b, res[0], lf=60, hf=200, max_delay_ms=20)
    assert one == two


def test_too_few_bins_is_insufficient_not_ok():
    a, b = T.synthetic('a', F), T.synthetic('b', F)
    best = T.Candidate(0., False, 0., 0)
    c = assess_alignment(a, b, best, lf=100, hf=101, max_delay_ms=5)
    assert c.verdict == 'INSUFFICIENT'


def test_agreement_threshold_is_documented_constant():
    assert AGREEMENT_OK == .80 and SATURATED_FRACTION_HOLD == .60
