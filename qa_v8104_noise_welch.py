"""Realistic dual-channel Welch simulation: estimated H1 + estimated MSC from nd averages.

Output-noise model (mic noise: wind/fan/crowd), reference electrical = clean.
Shows: coherence estimate bias at low nd, gate pass of bad bins, delay & mag errors,
and an alternative inverse-variance weighting with bias-corrected coherence.
"""
import sys, numpy as np
sys.path.insert(0, r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA\src")
from remix_duo.core import traces as T
from pathlib import Path

rng = np.random.default_rng(11)
f = np.geomspace(20, 20000, 1600)
DELAY = 3.7

def true_g2(kind):
    g = np.full(len(f), 0.98)
    if kind == "wind":
        g = 1 / (1 + 6.0 * (100 / f) ** 2)
    if kind == "fan":
        g = np.full(len(f), 0.55)
        for c in (100, 120, 200, 240):
            g[np.abs(np.log2(f / c)) < 0.04] = 0.15
    if kind == "crowd":
        g = np.where((f > 200) & (f < 4000), 0.35, 0.95)
    return np.clip(g, 1e-3, 0.999)

def welch(h, g2, nd):
    snr = g2 / (1 - g2)
    X = (rng.standard_normal((nd, len(f))) + 1j * rng.standard_normal((nd, len(f)))) / np.sqrt(2)
    N = (rng.standard_normal((nd, len(f))) + 1j * rng.standard_normal((nd, len(f)))) / np.sqrt(2)
    Y = h * X + N * np.abs(h) / np.sqrt(snr)
    Gxx = (np.abs(X) ** 2).sum(0); Gyy = (np.abs(Y) ** 2).sum(0); Gxy = (np.conj(X) * Y).sum(0)
    return Gxy / Gxx, np.abs(Gxy) ** 2 / (Gxx * Gyy)

def tr(n, h, c): return T.TFTrace(n, Path(n), f, h, np.clip(c, 0, 1), "tf", 0)

def align_variant(a, b, lf, hf, mode, nd):
    fq, h1, h2, coh = T.matched(a, b)
    roi = (fq >= lf) & (fq <= hf) & (coh >= .60)
    if roi.sum() < 12: return None
    fq, h1, h2, coh = fq[roi], h1[roi], h2[roi], coh[roi]
    if mode == "old":
        w = coh ** 2
    else:
        c = np.clip((coh * nd - 1) / max(nd - 1, 1), 1e-3, .995)
        w = c / (1 - c)
    norm = np.maximum(np.abs(h1) + np.abs(h2), 1e-15)
    d = np.arange(-20, 20.01, .1)
    sh = h2[None] * np.exp(-2j * np.pi * np.outer(d / 1000, fq))
    r = np.maximum(np.abs(h1[None] + sh) / norm[None], 1e-5)
    per = 20 * np.log10(r)
    if mode != "old": per = np.maximum(per, -20.)
    s = per @ w / w.sum()
    return d[int(np.argmax(s))], int(roi.sum())

for kind in ("clean", "fan", "wind", "crowd"):
    g = true_g2(kind)
    for nd in (1, 2, 4, 16, 64):
        eo, en, passbad, cbias, magerr, roin = [], [], [], [], [], []
        for _ in range(40):
            h1, c1 = welch(np.ones(len(f)), g, nd)
            h2, c2 = welch(np.exp(2j*np.pi*f*DELAY/1000), g, nd)
            a, b = tr("A", h1, c1), tr("B", h2, c2)
            o = align_variant(a, b, 60, 200, "old", nd)
            n = align_variant(a, b, 60, 200, "ivw", nd)
            eo.append(abs(o[0] - DELAY) if o else np.nan); en.append(abs(n[0] - DELAY) if n else np.nan)
            roin.append(o[1] if o else 0)
            bad = g < .6
            passbad.append(np.mean(c1[bad] >= .6) if bad.any() else 0)
            cbias.append(np.mean(c1 - g))
            ok = c1 >= .6
            magerr.append(np.sqrt(np.mean((20*np.log10(np.abs(h1[ok])))**2)) if ok.any() else np.nan)
        def st(x):
            x = np.array(x, float); good = np.isfinite(x)
            return (f"p95={np.nanpercentile(x,95):5.2f} wrong={np.mean(~good | (x>0.3)):4.0%}" if good.any() else "no-result")
        print(f"{kind:5s} nd={nd:2d} cohBias={np.mean(cbias):+.2f} badBinsPassGate={np.mean(passbad):4.0%} "
              f"magRMS(gated)={np.nanmean(magerr):4.2f}dB roiBins={np.mean(roin):4.0f} | OLD {st(eo)} | IVW {st(en)}")
