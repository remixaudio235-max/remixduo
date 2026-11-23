"""V8.98: hide the three user-marked FIR sidebar blocks, not FIR features.

Qt QA only: no Smaart/Generator/Sweep or DSP write. LF/HF drag, single-trace
provenance and Phase+ remain fully operational with invisible data controls.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from test_v845_fir_one_trace import init,wait_fir


def test_fir_red_blocks_removed_and_active_controls_preserved():
    app,obs,engine,hub,fir=init()
    hub.native_fir.timer.stop()
    try:
        hub.select("fir")
        hub.dock.show()
        app.processEvents()
        hidden=(fir.offline_button,fir.offline_clear,
                fir.fir_range_label,fir.fir_lf,fir.fir_hf,
                fir.overlay_status,fir.fs,fir._ux_sections[2],
                fir.summary,fir.details)
        assert all(widget.isHidden() for widget in hidden)
        assert [x.text()[:2] for x in fir._ux_sections]==["01","02","03"]
        assert all(not x.isHidden() for x in fir._ux_sections[:2])
        assert not fir.source.isHidden()
        assert not fir.taps.isHidden()
        assert fir.fir_mode.isHidden()  # legacy mode state remains internal
        assert not fir.fir_mag_button.isHidden()
        assert not fir.fir_phase_button.isHidden()
        assert not fir.taps_label.isHidden()
        assert not fir.calculate.isHidden()
        assert not fir.export_fir.isHidden()
        assert fir.export_txt.isHidden() and fir.export_wav.isHidden()
        # The source and sampling-rate information remain bound for native
        # validation despite hiding their redundant visual indicators.
        assert fir._fir_fs and fir._fir_fs.hz==48000
        assert fir._fir_token is not None
        assert fir.fir_lf.value()==500
        assert fir.fir_hf.value()==2500
        fir.fir_mode.setCurrentIndex(1)
        assert not fir.phase_plus.isHidden()
        assert not fir.phase_plus.isChecked()
        assert fir.taps.isEnabled()
        fir.drag_roi_to("LF",114)
        fir.drag_roi_to("HF",379)
        assert (fir.fir_lf.value(),fir.fir_hf.value())==(114,379)
        assert fir.fir_lf.isHidden() and fir.fir_hf.isHidden()
        # Even with hidden spin controls, a regular 1024-tap phase FIR
        # computes using the real saved trace and user-selected LF/HF.
        fir.taps.setCurrentIndex(fir.taps.findData(1024))
        fir.compute()
        wait_fir(app,fir,timeout=25)
        assert fir.result is not None
        assert any(str(w).startswith("PREVIEW_ONLY:") for w in fir.result.warnings)
        assert "không đủ 0.5 octave" in fir.details.toPlainText()
        # The safety detail remains internal and hidden from the compact UI.
        assert fir.details.toPlainText()
        assert fir.summary.isHidden() and fir.details.isHidden()
        # Provenance may be retained for the visible preview, while the
        # independent PREVIEW_ONLY quality gate keeps every export disabled.
        assert fir._approved is not None
        assert not fir.export_fir.isEnabled()
        fir.phase_plus.setChecked(True)
        assert fir.result is None
        assert not fir.export_fir.isEnabled()
        assert fir.summary.isHidden() and fir.details.isHidden()
        assert all(w.isHidden() for w in hidden)
    finally:
        hub.close()
        app.processEvents()
