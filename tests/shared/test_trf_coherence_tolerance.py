"""V8.113: Smaart can store slightly negative coherence (estimator rounding).

Observed live 2026-11-11 (Smaart Suite 9): 'sup bien 2-1.trf' has 13 bins with
coherence -0.0102..-0.0192. read_trf rejected the WHOLE trace ("bad TRF
samples") because the tolerance was -0.01, so Auto Phase silently produced
nothing for any pair containing it. Values are clipped to [0, 1] after
validation, so a small negative rounding error is physically "no coherence".
Clearly corrupt coherence must still be rejected.
"""
import struct
import numpy as np
import pytest
from remix_duo.core.traces import read_trf, TraceError


def legacy_trf(path, coh):
    n = len(coh)
    f = np.geomspace(20, 20000, n).astype("<f4")
    db = np.zeros(n); re = np.ones(n); im = np.zeros(n)
    base = 0x2a8
    ptr = (base, base + 4 * n, base + 12 * n, base + 20 * n, base + 28 * n)
    b = bytearray(base + 36 * n)
    b[:8] = b"JACKREF!"
    struct.pack_into("<5I", b, 0x288, *ptr)
    b[ptr[0]:ptr[0] + 4 * n] = f.tobytes()
    for at, arr in zip(ptr[1:], (db, re, im, np.asarray(coh, "<f8"))):
        b[at:at + 8 * n] = np.asarray(arr, "<f8").tobytes()
    path.write_bytes(bytes(b))
    return path


def test_small_negative_coherence_is_accepted_and_clipped(tmp_path):
    coh = np.full(120, .9); coh[[10, 50, 90]] = [-.0102, -.0192, -.0125]
    t = read_trf(legacy_trf(tmp_path / "sup bien 2-1.trf", coh))
    assert t.coherence.min() == 0.0 and t.coherence.max() <= 1.0
    assert len(t.hz) == 120


@pytest.mark.parametrize("bad", [-0.2, -0.06, 1.2, np.nan])
def test_corrupt_coherence_still_rejected(tmp_path, bad):
    coh = np.full(120, .9); coh[30] = bad
    with pytest.raises(TraceError):
        read_trf(legacy_trf(tmp_path / "bad.trf", coh))
