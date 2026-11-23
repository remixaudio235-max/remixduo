"""V8.104: AutoPhase shows/holds results by noise confidence (offscreen Qt)."""
import time
import numpy as np
import pytest
from PyQt6.QtWidgets import QApplication

from trf_core import synthetic, Candidate
from remix_duo.core.align_confidence import AlignConfidence


def _run(monkeypatch, confidence=None, raises=False):
    import overlay_v7 as gui
    app = QApplication.instance() or QApplication([])
    engine = gui.App(demo=True); engine.timer.stop(); engine.drag_timer.stop()
    settle = time.monotonic() + .5  # let the demo pair load finish first
    while time.monotonic() < settle:
        app.processEvents(); time.sleep(.005)
    f = np.geomspace(20, 20000, 200)
    engine.current_traces = (synthetic('a', f), synthetic('b', f, delay_ms=2))
    engine._selection_verified = True
    monkeypatch.setattr(gui, 'auto_align',
                        lambda *a, **k: [Candidate(2., False, -.1, 40), Candidate(-3., True, -.5, 40)])

    def fake_assess(*a, **k):
        if raises:
            raise RuntimeError('boom')
        return confidence
    monkeypatch.setattr(gui, 'assess_alignment', fake_assess)
    engine.align()
    until = time.monotonic() + 3
    while engine._align_future is not None and time.monotonic() < until:
        app.processEvents(); time.sleep(.005)
    app.processEvents()
    return engine, app


def _close(engine, app):
    engine.close(); app.processEvents()


def test_low_confidence_keeps_candidates_and_warns(monkeypatch):
    engine, app = _run(monkeypatch, AlignConfidence('LOW', .56, 40, 0., .3))
    try:
        assert engine.last_solve and engine.candidates[0].isEnabled()
        assert 'ĐỘ TIN CẬY THẤP (56%)' in engine.status.text()
        assert 'Averaging' in engine.status.text()
    finally:
        _close(engine, app)


def test_ok_confidence_reports_agreement(monkeypatch):
    engine, app = _run(monkeypatch, AlignConfidence('OK', .98, 40, 0., .2))
    try:
        assert engine.last_solve and 'Tin cậy #1: 98%' in engine.status.text()
        assert 'THẤP' not in engine.status.text()
    finally:
        _close(engine, app)


def test_saturated_rough_coherence_fails_closed(monkeypatch):
    engine, app = _run(monkeypatch, AlignConfidence('HOLD_SATURATED', .3, 40, .95, 5.8))
    try:
        assert engine.last_solve is None
        assert not any(b.isEnabled() for b in engine.candidates)
        text = engine.status.text()
        assert text.startswith('HOLD') and '95%' in text and 'Averaging' in text
    finally:
        _close(engine, app)


def test_confidence_failure_never_hides_solver_candidates(monkeypatch):
    engine, app = _run(monkeypatch, raises=True)
    try:
        assert engine.last_solve and engine.candidates[0].isEnabled()
        assert engine.last_confidence is None
        assert 'XEM THỬ #1' in engine.status.text()
    finally:
        _close(engine, app)


def test_real_solver_path_returns_confidence_for_clean_pair():
    import overlay_v7 as gui
    f = np.geomspace(20, 20000, 400)
    results, confidence = gui._solve_autophase(
        synthetic('a', f), synthetic('b', f, delay_ms=2), lf=60, hf=400, max_delay_ms=20)
    assert results and confidence is not None and confidence.verdict == 'OK'
