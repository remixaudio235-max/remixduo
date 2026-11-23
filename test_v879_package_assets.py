from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = ('remix_dou_swirl_toolbar32.png', 'remix_activation_logo.jpg', 'V812_MAG_TITLE_TEMPLATE.png',
          'V812_PHASE_TITLE_TEMPLATE.png')


def test_build_collects_gui_assets():
    build = (ROOT / 'build_remix_duo_qa_v877.ps1').read_text(encoding='utf-8')
    for name in ASSETS:
        assert (ROOT / name).is_file()
        assert f"--add-data', \"$source\\{name};.\"" in build, name


def test_frozen_assets_are_present_and_readable():
    from PyQt6.QtGui import QImage
    packaged = ROOT / 'dist' / 'RemiXDuo_QA' / '_internal'
    if not packaged.is_dir():
        import pytest
        pytest.skip('HOLD: this isolated source QA has no frozen Windows build yet')
    for name in ASSETS:
        assert (packaged / name).is_file(), name
        assert not QImage(str(packaged / name)).isNull(), name
