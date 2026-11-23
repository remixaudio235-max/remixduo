"""Validated, data-preserving Y viewport translation for Smaart SUM overlays.

The source TF H(f), phase and magnitude remain unchanged. A positively
moving native curve (down on screen) must move the overlay by the same
number of pixels. Both Phase and Mag use the same transformation.
"""
from __future__ import annotations

from math import isfinite


def trusted_pan(frame, now, last_frame_time=0.0, *,
                minimum_confidence=0.90, max_age_s=0.50):
    if frame is None or not frame.valid:
        return False
    stamp = float(frame.frame_time)
    dy = float(frame.delta_px)
    age = float(now) - stamp
    return bool(
        isfinite(stamp) and stamp > float(last_frame_time)
        and -0.05 <= age <= max_age_s
        and isfinite(dy) and abs(dy) <= 89.0
        and isfinite(float(frame.confidence))
        and float(frame.confidence) >= minimum_confidence
    )


def translated_y_range(y_min, y_max, plot_height, delta_px):
    lo, hi = float(y_min), float(y_max)
    height, dy = float(plot_height), float(delta_px)
    if not all(isfinite(z) for z in (lo, hi, height, dy)):
        raise ValueError("Nonfinite native pan")
    if height <= 0 or hi <= lo or abs(dy) > 89:
        raise ValueError("Invalid viewport/native pan")
    # Graph rasterizer y = height * (y_max - value) / span.
    # Positive native downshift => larger y_max and y_min.
    offset = dy * (hi - lo) / height
    return lo + offset, hi + offset, offset
