"""Minimal frozen launcher; commercial application logic lives in overlay_v7.pyd."""
from __future__ import annotations

import ctypes
import hashlib
import importlib
import importlib.util
import json
import sys
from pathlib import Path


def _reject_tampered_build(error: str = "") -> int:
    if "--cython-selfcheck" in sys.argv:
        try:
            import tempfile
            Path(tempfile.gettempdir(), "RemiXDuo_cython_selfcheck.txt").write_text(
                error or "integrity check failed", encoding="utf-8")
        except Exception:
            pass
        return 29
    message = ("Bản cài RemiX Duo không hợp lệ hoặc bị thay đổi. "
               "Vui lòng cài lại từ nguồn chính thức.")
    try:
        ctypes.windll.user32.MessageBoxW(None, message, "RemiX Duo", 0x10)
    except Exception:
        print(message, file=sys.stderr, flush=True)
    return 31


def _load_protected_core(bundle: Path, manifest: dict) -> dict:
    names = (
        "remix_duo.core.spacing", "remix_duo.core.q_policy",
        "remix_duo.core.peak_shape", "remix_duo.core.peak_rescue",
        "remix_duo.core.filters", "remix_duo.core.autoeq_engine",
        "remix_duo.core.fir_preview", "remix_duo.core.traces",
        "remix_duo.licensing.online", "remix_duo.update.github_release",
    )
    loaded = {}
    for name in names:
        artifact = manifest["artifacts"][name]
        path = bundle / Path(artifact["file"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
            raise RuntimeError("protected module hash mismatch")
        importlib.import_module(name.rpartition(".")[0])
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError("protected module loader unavailable")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        loaded[name] = str(path).lower()
    return loaded


def main() -> int:
    if getattr(sys, "frozen", False):
        try:
            # Load Qt first so SciPy/BLAS DLL discovery cannot shadow Qt DLLs.
            from PyQt6 import QtCore, QtGui, QtWidgets
            bundle = Path(sys._MEIPASS)
            manifest = json.loads(
                (bundle / "CYTHON_PROTECTED_MANIFEST.json").read_text(
                    encoding="utf-8"))
            protected_core = _load_protected_core(bundle, manifest)
            import _remixduo_native as native_app
            native_path = Path(native_app.__file__ or "")
            expected = manifest["artifacts"]["_remixduo_native"]["sha256"]
            actual = hashlib.sha256(native_path.read_bytes()).hexdigest()
            valid = (native_path.suffix.lower() == ".pyd" and actual == expected
                     and len(protected_core) == 10)
        except Exception as exc:
            valid = False
            error = f"{type(exc).__name__}: {exc}"
        if not valid:
            return _reject_tampered_build(locals().get("error", "hash mismatch"))
        if "--cython-selfcheck" in sys.argv:
            return 0
        if "--unicode-r63-selfcheck" in sys.argv:
            # Assert the installed frozen app redirects even an attached
            # cp1252-like terminal, preserving Vietnamese FIR diagnostics.
            try:
                from gui_watchdog_v8118 import configure_unicode_output
                from io import StringIO
                saved=(sys.stdout,sys.stderr)
                capture=StringIO()
                try:
                    configure_unicode_output(capture,redirect=True)
                    if sys.stdout is not capture or sys.stderr is not capture:
                        return 73
                    print("V8124_FIR_OK | Hiệu chỉnh 100%")
                    print("FIR HOLD: coherence≥0.65 chỉ 105/215 bins",
                          file=sys.stderr)
                    body=capture.getvalue()
                    return 0 if ("Hiệu chỉnh" in body and
                                 "coherence≥0.65" in body) else 74
                finally:
                    sys.stdout,sys.stderr=saved
            except Exception:
                return 75
        if "--workarea-r64-selfcheck" in sys.argv:
            # R64 frozen proof: taskbar shortens the native Smaart8 host
            # to 1680x1003 even when physical DISPLAY is 1680x1050.
            # Require native glyph-confirmed geometry, not X scaling.
            try:
                import numpy as np
                from PIL import Image
                from smaart8_plot_profile_v868 import title_template, detect_v8_profile
                pixels=np.full((1003,1680,3),10,dtype=np.uint8)
                for y,role in ((81,"PHASE"),(508,"MAG")):
                    ink=title_template(role)
                    height,width=ink.shape
                    patch=pixels[y+5:y+5+height,228:228+width,:]
                    patch[ink]=255
                profile=detect_v8_profile(Image.fromarray(pixels))
                return (0 if profile==((215,81,1234,405),
                                       (215,508,1234,405)) else 76)
            except Exception:
                return 77
        if "--native1680-r62-selfcheck" in sys.argv:
            # Frozen-only guard: verify exact Smaart8 native plot profile
            # is actually bundled, not just present in development source.
            # Synthetic source-free image contains independently verified
            # native Phase/Magnitude title glyphs; no GUI or audio device.
            try:
                import numpy as np
                from PIL import Image
                from smaart8_plot_profile_v868 import title_template, detect_v8_profile
                pixels=np.full((1050,1680,3),10,dtype=np.uint8)
                for y,role in ((81,"PHASE"),(508,"MAG")):
                    ink=title_template(role)
                    height,width=ink.shape
                    patch=pixels[y+5:y+5+height,228:228+width,:]
                    patch[ink]=255
                profile=detect_v8_profile(Image.fromarray(pixels))
                return 0 if profile==((215,81,1234,405),(215,508,1234,405)) else 67
            except Exception:
                return 68
        if "--sum-r60-selfcheck" in sys.argv:
            # Frozen QA: require the R60 dark-olive mask in the packaged
            # import graph, not merely in the on-disk Python source.
            try:
                import numpy as np
                from PIL import Image
                from smaart_native_mag_fit import trace_color_mask
                pixels = np.zeros((220, 620, 3), dtype=np.uint8)
                pixels[:] = (10, 10, 10)
                pixels[42, :] = (36, 36, 36)  # neutral Smaart grid
                pixels[100, 40:320] = (64, 94, 64)
                pixels[120, 40:320] = (50, 72, 50)
                mask = trace_color_mask(Image.fromarray(pixels), "green")
                return 0 if (int(np.count_nonzero(mask)) >= 500 and
                             not np.any(mask[42]) and not mask[145, 100]) else 65
            except Exception:
                return 66
        if "--screen-r5-selfcheck" in sys.argv:
            try:
                from smaart8_native_sidebar_v870 import v8_sidebar_rects
                from databar_icon_geometry_v8181 import classify_uia_row_gutter
                from full_scan_v7 import _page
                from PIL import Image, ImageDraw
                from types import SimpleNamespace
                dock=v8_sidebar_rects((0,0,1366,768),(0,0,1366,768))
                if (not dock.anchors_valid or dock.panel[2]<145 or
                    dock.panel[1]<415 or dock.panel[1]+dock.panel[3]>575):
                    return 61
                im=Image.new("RGB",(1366,768),(245,245,245))
                d=ImageDraw.Draw(im)
                d.rectangle((19,165,32,182),fill=(15,66,140))
                d.rectangle((19,187,32,204),fill=(171,38,121))
                a=classify_uia_row_gutter(im,163,29)
                b=classify_uia_row_gutter(im,185,29)
                return 0 if a=="on" and b=="on" else 62
            except Exception:
                return 63
        if "--eq-r4-frozen-selfcheck" in sys.argv:
            # Execute on the real frozen EXE. Verify that PyInstaller loaded
            # the R4 GUI module with both strict retry gates; no GUI/audio.
            try:
                import inspect
                from signal_tools_gui_v813 import EQDialog, EQ_EXPORT_R4_FROZEN_BUILD_TAG
                passed = (
                    EQ_EXPORT_R4_FROZEN_BUILD_TAG ==
                    "REMIX_DUO_EQ_EXPORT_R4_NATIVE_PROOF_WAIT_20261121"
                    and "_export_retry_tick_state" in
                        EQDialog._recheck_preconditions.__code__.co_names
                    and "_native_export_ok" in
                        EQDialog._poll_export_recheck.__code__.co_names
                    and "check_sha" in
                        inspect.signature(EQDialog._recheck_preconditions).parameters
                    and "check_sha" in
                        inspect.signature(EQDialog._native_export_ok).parameters
                )
                return 0 if passed else 42
            except Exception:
                return 43
        if "--qt-selfcheck" in sys.argv:
            assets = ("remix_dou_swirl_toolbar32.png", "remix_activation_logo.jpg",
                      "V812_MAG_TITLE_TEMPLATE.png", "V812_PHASE_TITLE_TEMPLATE.png")
            binaries = ("smaart_title_signatures_v03.npz",)
            ok = (bool(QtCore.QT_VERSION_STR) and
                  all(not QtGui.QImage(str(bundle / name)).isNull() for name in assets) and
                  all((bundle / name).is_file() and (bundle / name).stat().st_size > 0
                      for name in binaries))
            return 0 if ok else 24
        if "--autoeq-selfcheck" in sys.argv:
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
            return 0 if plan.status == "PREVIEW_READY" and plan.bands else 27
        if "--fir-safety-selfcheck" in sys.argv:
            import numpy as np
            from remix_duo.core.filters import design_phase_only_fir
            from remix_duo.core.fir_preview import make_source
            from remix_duo.core.fir_quality_gate import evaluate_fir_quality
            hz=np.geomspace(20.,18000.,320)
            h=np.exp(1j*(-2*np.pi*hz*.003
                        +.35*np.sin(np.log(hz)*2.)))
            coh=np.ones_like(hz)
            res=design_phase_only_fir(hz,h,coh,taps=512,
                                       fs=48000,lf=35,hf=188,strict=False)
            pre=make_source(hz,h,coh,res.taps,48000,
                            "selfcheck","immutable",1,35,188,"phase")
            verdict=evaluate_fir_quality(pre,res,35,188)
            return 0 if not verdict.accepted and any(
                "độ phân giải" in r for r in verdict.reasons) else 29
        if "--autofir-selfcheck" in sys.argv:
            import numpy as np
            from remix_duo.core.filters import design_phase_only_fir
            hz = np.geomspace(20.0, 20000.0, 400)
            phase = -2.0*np.pi*hz*0.001 + 0.6*np.sin(np.log(hz)*2.0)
            transfer = 10.0**(2.0*np.sin(np.log(hz)*1.7)/20.0)*np.exp(1j*phase)
            result = design_phase_only_fir(
                hz, transfer, np.full_like(hz, 0.2), taps=1024,
                fs=48000, lf=500, hf=2500, strict=False)
            return 0 if len(result.taps) == 1024 and np.isfinite(result.taps).all() else 28
    else:
        # Dynamic source-only fallback; PyInstaller must not collect overlay_v7.py.
        native_app = importlib.import_module("overlay" + "_v7")

    entrypoint = getattr(native_app, "main", None)
    if not callable(entrypoint):
        return _reject_tampered_build()
    return int(entrypoint(sys.argv[1:]) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
