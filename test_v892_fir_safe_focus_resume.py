"""V8.92: FIR preview resumes only after fresh one-tick + immutable proof.

Offscreen UI regression; no generator, DSP write, or Smaart UI manipulation.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from test_v845_fir_one_trace import init, wait_fir
from test_v16_independent_one_tick import tick


def _ready():
    app, obs, engine, hub, fir = init()
    hub.native_fir.timer.stop()
    # Identity-recovery scenarios require a valid MAG FIR, independent of
    # the new default FIR PHA and its physical ripple safeguards.
    fir.fir_mag_button.click()
    fir.compute()
    wait_fir(app, fir)
    assert fir.result is not None and fir._proof_current()
    assert fir.export_txt.isEnabled() and fir.export_wav.isEnabled()
    assert hub.native_fir.source is not None
    return app, obs, engine, hub, fir


def _close(app, hub):
    hub.close()
    app.processEvents()


def test_focus_timeout_hides_export_and_resumes_only_after_3_verified_ticks():
    app, obs, engine, hub, fir = _ready()
    try:
        previous_result = fir.result
        previous_source = hub.native_fir.source
        previous_digest = fir._approved[1]
        obs.invalidate_single()
        assert obs.current_single() is None
        fir.refresh_sources()
        assert fir.result is previous_result  # cached only, never authorized
        assert fir._approved is not None
        assert fir._fir_token is None
        assert not fir._proof_current()
        assert not fir.export_txt.isEnabled()
        assert not fir.export_wav.isEnabled()
        assert "HOLD" in fir.summary.text()
        assert hub.native_fir.source is previous_source
        # 1/3 and 2/3 MUST NOT re-enable export or paint.
        for _ in range(2):
            tick(obs, {0})
            fir.refresh_sources()
            assert not fir.export_txt.isEnabled()
            assert not fir._proof_current()
        tick(obs, {0})
        fir.refresh_sources()
        assert fir._proof_current()
        assert fir.export_txt.isEnabled() and fir.export_wav.isEnabled()
        assert fir.result is previous_result
        assert fir._approved[1] == previous_digest
        assert hub.native_fir.source is previous_source
    finally:
        _close(app, hub)


def test_two_ticks_mean_explicit_selection_change_and_clear_stale_fir():
    app, obs, engine, hub, fir = _ready()
    try:
        tick(obs, {0, 1})
        fir.refresh_sources()
        assert fir.result is None and fir._approved is None
        assert hub.native_fir.source is None
        assert not fir.export_txt.isEnabled()
    finally:
        _close(app, hub)


def test_same_file_metadata_but_changed_bytes_never_restores(monkeypatch):
    app, obs, engine, hub, fir = _ready()
    try:
        obs.invalidate_single()
        fir.refresh_sources()
        monkeypatch.setattr(fir, "_source_hash", lambda path: "CHANGED-BYTES")
        for _ in range(3):
            tick(obs, {0})
        fir.refresh_sources()
        assert fir.result is None
        assert fir._approved is None
        assert hub.native_fir.source is None
        assert not fir.export_wav.isEnabled()
    finally:
        _close(app, hub)


def test_window_identity_change_blocks_rebinding():
    app, obs, engine, hub, fir = _ready()
    try:
        # The prior fixture has no HWND: emulate a bound real Smaart window.
        fir._approved_window = 2500
        obs.hwnd = 9001
        obs.invalidate_single()
        fir.refresh_sources()
        for _ in range(3):
            tick(obs, {0})
        fir.refresh_sources()
        assert fir.result is None and fir._approved is None
        assert hub.native_fir.source is None
    finally:
        _close(app, hub)


def test_band_change_while_held_prevents_old_preview_reuse():
    app, obs, engine, hub, fir = _ready()
    try:
        obs.invalidate_single()
        fir.refresh_sources()
        fir.fir_lf.setValue(fir.fir_lf.value()+10)
        assert fir.result is None and fir._approved is None
        for _ in range(3):
            tick(obs, {0})
        fir.refresh_sources()
        assert not fir._proof_current()
        assert not fir.export_wav.isEnabled()
    finally:
        _close(app, hub)
