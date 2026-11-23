"""Regression coverage for visible license state after activation."""

from pathlib import Path

from remix_duo_license_v874 import LicenseState, license_display


ROOT = Path(__file__).resolve().parent


def test_active_license_has_visible_badge_without_exposing_a_key():
    state = LicenseState(
        True,
        "ACTIVE",
        "DUO-ADMIN-QA",
        "RemiX Audio QA",
        0,
    )

    badge, tooltip = license_display(state)

    assert badge == "RemiX Duo · ACTIVE"
    assert "DUO-ADMIN-QA" in tooltip
    assert "RemiX Audio QA" in tooltip
    assert "LIC1." not in tooltip and "RDX-" not in tooltip


def test_inactive_license_does_not_claim_active():
    badge, tooltip = license_display(LicenseState(False, "NOT_ACTIVATED"))

    assert badge == "RemiX Duo"
    assert tooltip == "License: NOT_ACTIVATED"


def test_main_passes_verified_license_display_into_tool_hub():
    overlay = (ROOT / "overlay_v7.py").read_text(encoding="utf-8")
    gui = (ROOT / "signal_tools_gui_v813.py").read_text(encoding="utf-8")

    assert "license_display(license_state)" in overlay
    assert "ToolHub(view, license_badge, license_tooltip)" in overlay
    assert "def __init__(self,engine,license_badge=\"RemiX Duo\"," in gui
    assert "self.brand_text=QLabel(license_badge" in gui


def test_shared_native_overlay_keeps_full_remix_brand():
    overlay = (ROOT / "src/remix_duo/ui/overlay.py").read_text(encoding="utf-8")

    assert "QLabel('RemiX Duo · ACTIVE')" in overlay
