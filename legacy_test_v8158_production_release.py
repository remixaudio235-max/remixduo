from pathlib import Path

ROOT=Path(__file__).resolve().parent


def test_release_version_is_consistent():
    assert 'version = "8.158.0"' in (ROOT/'pyproject.toml').read_text('utf-8')
    assert '__version__ = "8.158"' in (
        ROOT/'src/remix_duo/__init__.py').read_text('utf-8')
    installer=(ROOT/'remix_duo_production_v8158.iss').read_text('utf-8')
    assert '#define MyAppVersion "8.158"' in installer
    assert 'VersionInfoVersion=8.158.0.0' in installer
    assert 'RemiXDuo_Setup_V8.158' in installer
    assert '"psutil>=5.9; sys_platform == \'win32\'"' in (
        ROOT/'pyproject.toml').read_text('utf-8')


def test_production_build_has_no_qa_license_override():
    build=(ROOT/'build_remix_duo_production_v8158.ps1').read_text('utf-8')
    hook=(ROOT/'production_runtime_hook_v8150.py').read_text('utf-8')
    assert 'qa_runtime_hook' not in build
    assert '_remix_duo_qa_signed_build' not in hook
    assert 'PRODUCTION_ONLINE_LICENSE_NOT_CONFIGURED' in build
    assert 'remix_duo_cloud_license_v876' not in build
    assert 'remix_duo.licensing.online' in build
    assert '--online-license-selfcheck' in build
    assert 'SIGNING_REQUIRED_BEFORE_RELEASE' in build


def test_production_installer_has_no_qa_branding():
    text=(ROOT/'remix_duo_production_v8158.iss').read_text('utf-8')
    assert 'RemiX Duo QA' not in text
    assert 'RemiXDuo_QA' not in text
    assert 'PrivilegesRequired=lowest' in text
    assert 'SetupIconFile=remixduo_app.ico' in text
    assert 'UninstallDisplayIcon={app}\\RemiXDuo.exe' in text


def test_production_build_embeds_release_icons():
    build=(ROOT/'build_remix_duo_production_v8158.ps1').read_text('utf-8')
    assert build.count("'--icon',\"$source\\remixduo_app.ico\"") == 3
    assert (ROOT/'icon.ico').is_file()
    assert (ROOT/'logo.ico').is_file()
    assert (ROOT/'src/remix_duo/resources/logo.ico').is_file()
    assert (ROOT/'remixduo_app.ico').is_file()
    assert (ROOT/'src/remix_duo/resources/remixduo_app.ico').is_file()


def test_signing_is_fail_closed_and_emits_artifact_manifest():
    text=(ROOT/'sign_release_v8158.ps1').read_text('utf-8')
    assert 'CODE_SIGNING_PRIVATE_KEY_MISSING' in text
    assert 'SIGNATURE_VERIFY_FAILED' in text
    assert 'RELEASE_ARTIFACTS_V8.158.sha256' in text
    assert '/fd SHA256' in text and '/td SHA256' in text


def test_production_frozen_gate_uses_shared_v3_v4_client():
    overlay=(ROOT/'overlay_v7.py').read_text('utf-8')
    hook=(ROOT/'production_runtime_hook_v8150.py').read_text('utf-8')
    assert 'from remix_duo.licensing.gate import activation_gate' in overlay
    assert 'from remix_duo.licensing.online import configured' in hook
    assert 'from remix_duo_cloud_license_v876 import activation_gate' not in overlay


def test_production_build_requires_frozen_updater_selfcheck():
    build=(ROOT/'build_remix_duo_production_v8158.ps1').read_text('utf-8')
    hook=(ROOT/'production_runtime_hook_v8150.py').read_text('utf-8')
    assert '--updater-selfcheck' in build
    assert '--updater-selfcheck' in hook
    assert 'remix_duo.update.github_release' in hook


def test_production_build_runs_frozen_autoeq_smoke_before_installer():
    build=(ROOT/'build_remix_duo_production_v8158.ps1').read_text('utf-8')
    launcher=(ROOT/'main.py').read_text('utf-8')
    assert '--autoeq-selfcheck' in build
    assert 'if "--autoeq-selfcheck" in sys.argv:' in launcher
    assert 'design_unified_autoeq' in launcher
    assert build.index('--autoeq-selfcheck') < build.index('& $inno')


def test_production_build_runs_frozen_autofir_smoke_before_installer():
    build=(ROOT/'build_remix_duo_production_v8158.ps1').read_text('utf-8')
    launcher=(ROOT/'main.py').read_text('utf-8')
    assert '--autofir-selfcheck' in build
    assert 'if "--autofir-selfcheck" in sys.argv:' in launcher
    assert 'design_phase_only_fir' in launcher
    assert build.index('--autofir-selfcheck') < build.index('& $inno')


def test_production_build_bundles_native_plot_signature():
    build=(ROOT/'build_remix_duo_production_v8158.ps1').read_text('utf-8')
    hook=(ROOT/'production_runtime_hook_v8150.py').read_text('utf-8')
    asset=ROOT/'smaart_title_signatures_v03.npz'
    assert asset.is_file() and asset.stat().st_size>0
    assert 'smaart_title_signatures_v03.npz;.' in build
    assert 'smaart_title_signatures_v03.npz' in hook
