"""V8.36 regression: signed Phase/Mag pan from an unchanged V8.35 Smaart frame.

This uses the existing saved screenshot, never operates Smaart or audio I/O.
"""
from pathlib import Path
import pytest
from PIL import Image, ImageDraw
from native_fast_pan_v81 import colored_profiles, infer_pan

SCREENSHOT = Path(__file__).with_name("V835_CROSSOVER_LIVE_QA.png")
PLOTS = {"phase": (252, 84, 1442, 412), "mag": (252, 539, 1442, 412)}


@pytest.mark.parametrize("kind,dy", [
    ("phase", -65), ("phase", -30), ("phase", 0),
    ("phase", 10), ("phase", 35), ("phase", 65),
    ("mag", -65), ("mag", -30), ("mag", 0),
    ("mag", 10), ("mag", 35), ("mag", 65),
])
def test_signed_y_pan_recovers_native_source(kind, dy):
    x, y, w, h = PLOTS[kind]
    x += max(65, int(w * .105))
    with Image.open(SCREENSHOT) as shot:
        before = shot.convert("RGB").crop((x, y, x + 440, y + h))
    moved = Image.new("RGB", before.size)
    moved.paste(before, (0, dy))
    result = infer_pan(colored_profiles(before)[0], colored_profiles(moved)[0])
    assert result.valid, (kind, dy, result.reason)
    assert abs(result.delta_px - dy) <= 1, (kind, dy, result)
    assert result.confidence >= .85, (kind, dy, result.confidence)


def test_green_sum_alone_never_proves_native_y_motion():
    before = Image.new("RGB", (440, 412))
    draw = ImageDraw.Draw(before)
    draw.line([(10, 75), (100, 205), (220, 110), (420, 260)],
              fill=(12, 250, 24), width=3)
    after = Image.new("RGB", before.size)
    after.paste(before, (0, -40))
    assert colored_profiles(before)[1] == 0
    result = infer_pan(colored_profiles(before)[0], colored_profiles(after)[0])
    assert not result.valid
