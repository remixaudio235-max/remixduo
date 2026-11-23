"""Monte Carlo: AutoPhase delay accuracy under noise (read-only, no product change).

Model per Bendat&Piersol: an H1 estimate with MSC g2 and n_d averages has
relative complex error variance ~ (1-g2)/(2*n_d*g2) per real/imag component.
Smaart coherence assumed to be MSC (gamma^2) -- to be verified.
"""
import sys, numpy as np
sys.path.insert(0, r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA\src")
from remix_duo.core import traces as T
from pathlib import Path

rng = np.random.default_rng(7)
f = np.geomspace(20, 20000, 2400)
TRUE_DELAY = 3.7

def make(h, g2, nd):
    sig = np.sqrt((1 - g2) / (2 * nd * np.maximum(g2, 1e-3)))
    n = (rng.standard_normal(len(h)) + 1j * rng.standard_normal(len(h))) * sig * np.abs(h)
    return h + n

def trace(name, h, g2):
    return T.TFTrace(name, Path(name + ".trf"), f, h, g2, "tf", 0)

def scenario(kind):
    g2 = np.full(len(f), 0.97)
    if kind == "fan":
        g2[:] = 0.75 + 0.2 * rng.random(len(f))
        for c in (100, 120, 200, 240):
            g2[np.abs(np.log2(f / c)) < 0.05] = 0.62
    if kind == "wind":
        lf = f < 200
        g2[lf] = 0.60 + 0.35 * rng.random(lf.sum())
    return g2

def run(kind, nd, trials=60):
    h1t = np.ones(len(f), complex)
    errs = {}
    for sign in (+1, -1):
        h2t = np.exp(sign * 2j * np.pi * f * TRUE_DELAY / 1000)
        a = trace("A", h1t, np.ones(len(f)))
        b = trace("B", h2t, np.ones(len(f)))
        r = T.auto_align(a, b, lf=60, hf=200, max_delay_ms=20)[0]
        errs[sign] = r.delay_ms
    target = errs[+1]  # clean reference answer for this sign convention
    e = []
    for _ in range(trials):
        g2a, g2b = scenario(kind), scenario(kind)
        a = trace("A", make(h1t, g2a, nd), g2a)
        b = trace("B", make(np.exp(2j*np.pi*f*TRUE_DELAY/1000), g2b, nd), g2b)
        res = T.auto_align(a, b, lf=60, hf=200, max_delay_ms=20)
        best = res[0] if res else None
        e.append(abs(best.delay_ms - target) if best and not best.invert_trace2 else np.inf)
    e = np.array(e)
    return target, np.median(e), np.percentile(e, 95), float(np.mean(e > 0.3))

if __name__ == "__main__":
    for kind in ("clean", "fan", "wind"):
        for nd in (32, 8, 2):
            tgt, med, p95, fail = run(kind, nd)
            print(f"{kind:5s} nd={nd:2d} target={tgt:+.1f}  median_err={med:.2f}ms  p95={p95:.2f}ms  wrong(>0.3ms or polarity)={fail:.0%}")
