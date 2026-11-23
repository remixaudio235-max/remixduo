"""V8.114: recover Smaart per-trace dB offsets from a synthetic native frame."""
from pathlib import Path
import numpy as np
import pytest
from PIL import Image, ImageDraw
from remix_duo.core.traces import TFTrace
from trace_offset_native_v8114 import measure_trace_offsets

WIN = (0, 0, 1920, 1032)
PLOT = (252, 549, 1442, 394)
YMIN, YMAX = -18.0, 18.0
F = np.geomspace(20, 20000, 463)


def trf(name, db):
    return TFTrace(name, Path(name), F, 10 ** (db / 20) + 0j, np.full(len(F), .95), "Legacy", 1)


def shape(seed):
    r = np.random.default_rng(seed)
    base = 6 * np.sin(np.log(F) * (1.3 + seed * .4)) + 3 * np.cos(np.log(F) * 3.1 + seed)
    return base + r.normal(0, .15, len(F))


def draw(img, db, offset, rgb):
    x, y, w, h = PLOT
    xs = x + w * np.log(F / 20) / np.log(1000)
    ys = y + (YMAX - (db + offset)) / (YMAX - YMIN) * h
    d = ImageDraw.Draw(img)
    d.line(list(zip(xs, ys)), fill=rgb, width=2)


def frame(curves):
    img = Image.new("RGB", (WIN[2], WIN[3]), (8, 8, 10))
    for db, off, rgb in curves:
        draw(img, db, off, rgb)
    return img


TEAL, RED = (27, 224, 166), (225, 45, 40)


def test_two_traces_offsets_recovered():
    a, b = shape(1), shape(2)
    img = frame([(a, 7.0, RED), (b, 0.0, TEAL)])
    res = measure_trace_offsets(img, PLOT, WIN, (trf("a", a), trf("b", b)), YMIN, YMAX)
    assert res[0].offset_db == pytest.approx(7.0, abs=.35), res
    assert res[1].offset_db == pytest.approx(0.0, abs=.35), res
    img = frame([(a, -2.0, RED), (b, 0.0, TEAL)])
    res = measure_trace_offsets(img, PLOT, WIN, (trf("a", a), trf("b", b)), YMIN, YMAX)
    assert res[0].offset_db == pytest.approx(-2.0, abs=.35), res


def test_missing_trace_fails_closed():
    a, b = shape(1), shape(2)
    img = frame([(b, 0.0, TEAL)])
    res = measure_trace_offsets(img, PLOT, WIN, (trf("a", a), trf("b", b)), YMIN, YMAX)
    assert res[0].offset_db is None


def test_wrong_axis_scale_fails_closed():
    a, b = shape(1), shape(2)
    img = frame([(a, 3.0, RED), (b, 0.0, TEAL)])
    res = measure_trace_offsets(img, PLOT, WIN, (trf("a", a), trf("b", b)), -36.0, 36.0)
    assert all(r.offset_db is None for r in res)


def test_unverified_axis_fails_closed():
    a = shape(1)
    res = measure_trace_offsets(frame([(a, 0, RED)]), PLOT, WIN, (trf("a", a),), 5.0, 5.0)
    assert res[0].offset_db is None
