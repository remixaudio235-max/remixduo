from pathlib import Path

import pytest

from remix_duo.core.traces import read_trf


SESSION = Path.home() / "Documents/Smaart Suite/Data/Transfer Function/Session Data"


def test_tunninggg_3_auto_limits_recovers_from_fixed_default_failure():
    from remix_duo.core.autoeq import design_remix_eq, design_remix_eq_auto_limits

    path = SESSION / "TUNNINNGGG-3-1.trf"
    if not path.is_file():
        pytest.skip("Live regression TRF is not installed")
    trace = read_trf(path)

    with pytest.raises(ValueError, match="target regression"):
        design_remix_eq(
            trace.hz, trace.h, trace.coherence, fs=48_000, target="Flat",
            filters=8, lf=60, hf=8000, boost=2, cut=-6, source=path.stem,
        )

    result = design_remix_eq_auto_limits(
        trace.hz, trace.h, trace.coherence, fs=48_000, target="Flat",
        filters=8, lf=60, hf=8000, source=path.stem,
    )

    assert result.status == "PREVIEW_READY"
    assert result.peqs
    assert result.limits_auto
    assert 0 <= result.boost_limit_db <= 6
    assert -12 <= result.cut_limit_db <= -0.1
    assert result.boost_limit_db == 1
    assert result.cut_limit_db == -12

