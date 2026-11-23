import numpy as np

from remix_duo.core.filters import design_linear_phase_fir, design_phase_only_fir
from remix_duo.core.fir_preview import make_source


def _measurement():
    freq = np.geomspace(20.0, 20_000.0, 600)
    phase = -2 * np.pi * freq * 0.001 + np.deg2rad(30) * np.sin(np.log2(freq))
    magnitude = np.power(10.0, 3.0 * np.sin(np.log(freq) * 2.0) / 20.0)
    return freq, magnitude * np.exp(1j * phase)


def test_fir_design_is_identical_when_only_coherence_changes():
    freq, transfer = _measurement()
    high = np.ones_like(freq)
    low = np.zeros_like(freq)

    for design in (design_linear_phase_fir, design_phase_only_fir):
        trusted = design(freq, transfer, high, taps=1024, lf=600, hf=5000)
        reference_only = design(freq, transfer, low, taps=1024, lf=600, hf=5000)

        assert np.array_equal(reference_only.taps, trusted.taps)
        assert any("Coherence" in warning for warning in reference_only.warnings)


def test_phase_preview_and_quality_do_not_disappear_at_zero_coherence():
    freq, transfer = _measurement()
    kernel = design_phase_only_fir(
        freq, transfer, np.ones_like(freq), taps=1024, lf=600, hf=5000
    ).taps

    trusted = make_source(
        freq, transfer, np.ones_like(freq), kernel, 48_000, "trace", "id", 1,
        600, 5000, "phase"
    )
    reference_only = make_source(
        freq, transfer, np.zeros_like(freq), kernel, 48_000, "trace", "id", 1,
        600, 5000, "phase"
    )

    assert np.array_equal(reference_only.phase_valid, trusted.phase_valid)
    assert reference_only.phase_quality_bins == trusted.phase_quality_bins
    assert reference_only.phase_rms_before == trusted.phase_rms_before
    assert reference_only.phase_rms_after == trusted.phase_rms_after

