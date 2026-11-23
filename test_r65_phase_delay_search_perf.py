import time

import numpy as np

from remix_duo.core.phase_tools import remove_bulk_delay


def test_two_stage_bulk_delay_keeps_full_range_and_50us_accuracy():
    freq = np.geomspace(20.0, 20_000.0, 1200)
    weights = np.ones_like(freq)
    residual = 0.5 * np.sin(np.log(freq) * 3.0)
    for delay in (-0.299, -0.18123, -0.00203, 0.0, 0.00731, 0.17991, 0.299):
        transfer = np.exp(1j * (residual - 2 * np.pi * freq * delay))
        excess, measured = remove_bulk_delay(freq, transfer, weights)
        assert abs(measured - delay) <= 26e-6
        assert np.isfinite(excess).all()


def test_bulk_delay_search_performance_budget():
    freq = np.geomspace(20.0, 20_000.0, 1200)
    transfer = np.exp(-2j * np.pi * freq * 0.04219)
    started = time.perf_counter()
    remove_bulk_delay(freq, transfer, np.ones_like(freq))
    # Baseline full sweep was 0.54-0.82 s on the R65 QA host.
    assert time.perf_counter() - started < 0.30
