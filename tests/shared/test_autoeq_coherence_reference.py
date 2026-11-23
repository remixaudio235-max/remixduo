import numpy as np

from remix_duo.core.autoeq import design_remix_eq


def _measurement():
    freq = np.geomspace(20.0, 20_000.0, 463)
    mag_db = (
        5.0 * np.exp(-0.5 * (np.log2(freq / 1000.0) / 0.35) ** 2)
        - 4.0 * np.exp(-0.5 * (np.log2(freq / 250.0) / 0.45) ** 2)
    )
    return freq, np.power(10.0, mag_db / 20.0).astype(complex)


def test_autoeq_coherence_is_reference_only():
    freq, transfer = _measurement()

    trusted = design_remix_eq(freq, transfer, np.ones_like(freq), fs=48_000)
    untrusted = design_remix_eq(freq, transfer, np.zeros_like(freq), fs=48_000)

    assert untrusted.status == "PREVIEW_READY"
    assert untrusted.peqs == trusted.peqs
    assert np.array_equal(untrusted.after_db, trusted.after_db)
    assert any("Coherence" in warning for warning in untrusted.warnings)

