"""V8.104 read-only end-to-end run of AutoPhase / AutoEQ / FIR on real Smaart Suite TRFs.

No Smaart control, no DSP write, no file export. Prints one line per case.
"""
import _remix_bootstrap  # noqa: F401
import glob, os, time, collections, numpy as np
from remix_duo.core import traces as T
from remix_duo.core.align_confidence import assess_alignment
from remix_duo.core.filters import design_linear_phase_fir, design_phase_only_fir
import autoeq_core as AE

FOLDER = os.path.expanduser(r"~\Documents\Smaart Suite\Data\Transfer Function\Session Data")
files = sorted(glob.glob(os.path.join(FOLDER, "*.trf")), key=os.path.getmtime)[-12:]
tally = collections.Counter()
traces = []
for p in files:
    try: traces.append((p, T.read_trf(p)))
    except Exception as e: print("READ_FAIL", os.path.basename(p), e); tally["read_fail"] += 1

print("== AUTO PHASE (consecutive pairs, ROI 60-200)")
for (pa, a), (pb, b) in zip(traces[:-1], traces[1:]):
    t = time.time(); r = T.auto_align(a, b, lf=60, hf=200, max_delay_ms=180)
    c = assess_alignment(a, b, r[0], lf=60, hf=200) if r else None
    tally["phase_" + (c.verdict if c else "NO_RESULT")] += 1
    print(f"  {a.name[:16]:16s}|{b.name[:16]:16s} {r[0].delay_ms:+7.2f}ms {'INV' if r[0].invert_trace2 else 'NOR'} "
          f"{c.verdict} {c.agreement:.0%} {time.time()-t:.2f}s" if r else "  no result")

print("== AUTO EQ (Flat, 60-12000 Hz, 48 kHz, 12 bands)")
for p, tr in traces:
    t = time.time()
    try:
        res = AE.design(p, AE.EQConfig())
        tally["eq_" + res.status] += 1
        gains = [round(b.gain_db, 1) for b in res.bands]
        ok = all(AE.EQConfig().max_cut_db - 1e-4 <= g <= AE.EQConfig().max_boost_db + 1e-4 for g in gains)
        print(f"  {tr.name[:20]:20s} {res.status:16s} bands={len(res.bands):2d} wRMS {res.before_wrms_db:5.2f}->{res.after_wrms_db:5.2f} dB "
              f"gainsWithinLimits={ok} warn={len(res.warnings)} {time.time()-t:.2f}s")
        if not ok: tally["eq_LIMIT_VIOLATION"] += 1
    except Exception as e:
        tally["eq_exception"] += 1; print(f"  {tr.name[:20]:20s} EXC {type(e).__name__}: {str(e)[:90]}")

print("== FIR (1024 taps, 48 kHz, 30-16000 Hz) mag + phase")
for p, tr in traces:
    for mode in ("mag", "phase"):
        t = time.time()
        try:
            fn = design_linear_phase_fir if mode == "mag" else design_phase_only_fir
            r = fn(tr.hz, tr.h, tr.coherence, taps=1024, fs=48000, lf=30, hf=16000, source=tr.name) if mode == "mag" \
                else fn(tr.hz, tr.h, tr.coherence, taps=1024, fs=48000, lf=30, hf=16000, source=tr.name)
            finite = bool(np.all(np.isfinite(r.taps)))
            band = (r.hz >= 100) & (r.hz <= 10000)
            err = float(np.max(np.abs(r.actual_db[band] - r.target_db[band]))) if band.any() else float("nan")
            peak = float(np.max(np.abs(r.taps)))
            tally[f"fir_{mode}_{'ok' if finite else 'NONFINITE'}"] += 1
            print(f"  {tr.name[:20]:20s} {mode:5s} taps={len(r.taps)} finite={finite} maxErr100-10k={err:5.2f}dB "
                  f"peak={peak:.3f} latency={r.latency_ms:.2f}ms {time.time()-t:.2f}s")
        except Exception as e:
            tally[f"fir_{mode}_exception"] += 1; print(f"  {tr.name[:20]:20s} {mode} EXC {type(e).__name__}: {str(e)[:90]}")
print("== SUMMARY", dict(tally))
