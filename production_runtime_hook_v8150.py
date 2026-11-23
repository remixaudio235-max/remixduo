"""Production-only frozen self-check dispatch.

This hook deliberately sets no QA/signed-build override and provides no
license bypass. Normal startup remains on the commercial Cloudflare gate in
``overlay_v7.py``.
"""
import os
import sys


if False and "--qt-selfcheck" in sys.argv:
    code = 24
    try:
        from pathlib import Path
        from PyQt6 import QtCore, QtGui, QtWidgets
        bundle = Path(sys._MEIPASS)
        assets = (
            "remix_dou_swirl_toolbar32.png",
            "remix_activation_logo.jpg",
            "V812_MAG_TITLE_TEMPLATE.png",
            "V812_PHASE_TITLE_TEMPLATE.png",
        )
        binary_assets = ("smaart_title_signatures_v03.npz",)
        if (QtCore.QT_VERSION_STR and QtWidgets and
                all(not QtGui.QImage(str(bundle / name)).isNull()
                    for name in assets) and
                all((bundle / name).is_file() and (bundle / name).stat().st_size > 0
                    for name in binary_assets)):
            code = 0
    except Exception:
        pass
    os._exit(code)

if "--online-license-selfcheck" in sys.argv:
    code = 25
    try:
        from remix_duo.licensing.online import configured
        code = 0 if configured() else 25
    except Exception:
        pass
    os._exit(code)

if "--updater-selfcheck" in sys.argv:
    code = 26
    try:
        from remix_duo.update.github_release import configured
        code = 0 if configured() else 26
    except Exception:
        pass
    os._exit(code)

if False and "--autoeq-selfcheck" in sys.argv:
    code = 27
    try:
        import numpy as np
        from remix_duo.core.autoeq_engine import (
            AutoEQInput, AutoEQProfile, design_unified_autoeq)
        hz = np.geomspace(60.0, 12000.0, 320)
        mag_db = (5.0*np.exp(-0.5*(np.log2(hz/180.0)/0.22)**2)
                  - 3.0*np.exp(-0.5*(np.log2(hz/900.0)/0.35)**2))
        inp = AutoEQInput(hz, 10.0**(mag_db/20.0).astype(complex),
                          np.ones_like(hz), "coherence", 48000.0,
                          "stored_tf", np.array([60.0, 12000.0]),
                          np.array([0.0, 0.0]), 6.0)
        profile = AutoEQProfile(f_min_hz=60.0, f_max_hz=12000.0,
                                max_filters=8, max_peq=8,
                                max_boost_db=6.0, max_cut_db=-12.0)
        plan = design_unified_autoeq(inp, profile)
        if plan.status == "PREVIEW_READY" and len(plan.bands) > 0:
            code = 0
    except Exception:
        pass
    os._exit(code)

if False and "--autofir-selfcheck" in sys.argv:
    code = 28
    try:
        import numpy as np
        from remix_duo.core.filters import design_phase_only_fir
        hz = np.geomspace(20.0, 20000.0, 400)
        phase = -2.0*np.pi*hz*0.001 + 0.6*np.sin(np.log(hz)*2.0)
        transfer = 10.0**(2.0*np.sin(np.log(hz)*1.7)/20.0)*np.exp(1j*phase)
        result = design_phase_only_fir(
            hz, transfer, np.full_like(hz, 0.2), taps=1024,
            fs=48000, lf=500, hf=2500, strict=False)
        if len(result.taps) == 1024 and np.isfinite(result.taps).all():
            code = 0
    except Exception:
        pass
    os._exit(code)
