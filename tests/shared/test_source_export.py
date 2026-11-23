from pathlib import Path
import importlib.util
import zipfile
import pytest

ROOT=Path(__file__).resolve().parents[2]
def exporter():
    spec=importlib.util.spec_from_file_location('source_export',ROOT/'packaging/export_source.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def test_source_export_contains_build_sources_but_never_env_cache_or_license(tmp_path):
    m=exporter();archive=tmp_path/'source.zip'
    m.export(ROOT,archive)
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        assert 'src/remix_duo/core/filters.py' in names
        assert 'packaging/macos/build.py' in names
        assert 'src/remix_duo/resources/remix_activation_logo.jpg' in names
        assert 'MANIFEST.sha256.json' in names
        assert not any('__pycache__' in n or n.endswith(('.lic','.env','.key','.pem','.pyc')) or '.dev.vars' in n for n in names)
        assert not any(n.startswith(('dist/','build/','cloudflare_')) for n in names)
