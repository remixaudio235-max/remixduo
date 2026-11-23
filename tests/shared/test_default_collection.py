from pathlib import Path
import os,subprocess,sys

def test_default_pytest_discovers_shared_tests_without_legacy_gui_scripts(tmp_path):
    root=Path(__file__).resolve().parents[2]
    (tmp_path/'pyproject.toml').write_bytes((root/'pyproject.toml').read_bytes())
    folder=tmp_path/'tests/shared';folder.mkdir(parents=True)
    (folder/'test_safe.py').write_text('def test_safe(): assert True\n')
    (tmp_path/'test_legacy_gui.py').write_text('raise AssertionError("legacy GUI script imported during portable collection")\n')
    r=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=tmp_path,capture_output=True,text=True,
        env={**os.environ,'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'})
    assert r.returncode==0,r.stdout+r.stderr
