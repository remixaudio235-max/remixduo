import importlib.util
from pathlib import Path
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2]

def builder():
    spec=importlib.util.spec_from_file_location('duo_mac_builder',ROOT/'packaging/macos/build.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def test_mac_build_rejects_windows_crosscompile_and_rosetta():
    b=builder()
    with pytest.raises(RuntimeError,match='native macOS'): b.preflight('arm64',host='win32',machine='AMD64',version='')
    with pytest.raises(RuntimeError,match='architecture'): b.preflight('arm64',host='darwin',machine='x86_64',version='13.0',translated=False)
    with pytest.raises(RuntimeError,match='Rosetta'): b.preflight('x86_64',host='darwin',machine='x86_64',version='13.0',translated=True)
    with pytest.raises(RuntimeError,match='13'): b.preflight('arm64',host='darwin',machine='arm64',version='12.6',translated=False)
    b.preflight('arm64',host='darwin',machine='arm64',version='13.0',translated=False)
    b.preflight('x86_64',host='darwin',machine='x86_64',version='14.0',translated=False)

def test_no_release_bundle_without_native_acceptance():
    b=builder()
    with pytest.raises(RuntimeError,match='native acceptance'): b.release_gate()

def test_mac_artifact_version_matches_project_version():
    assert builder().project_version() == '8.181.0'

def test_selfcheck_from_unrelated_cwd(tmp_path):
    result=subprocess.run([sys.executable,str(ROOT/'run_remix_duo.py'),'--selfcheck'],cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert '"missing_assets": []' in result.stdout
    assert 'HOLD' in result.stdout

def test_windows_packaging_includes_canonical_source_and_assets():
    text=(ROOT/'build_remix_duo_qa_v877.ps1').read_text('utf-8-sig')
    assert '"$source\\src"' in text
    assert "'--collect-data', 'remix_duo'" in text

def test_release_requires_both_architectures_same_source_and_real_developer_id(tmp_path):
    import json
    b=builder();receipts=[]
    for arch in ('arm64','x86_64'):
        p=tmp_path/(arch+'.json')
        p.write_text(json.dumps({'architecture':arch,'source_sha256':'abc',
            'shared_tests':True,'frozen_selfcheck':True,'native_smaart':True,'clean_install':True}))
        receipts.append(p)
    with pytest.raises(RuntimeError,match='Developer ID'):
        b.release_gate(receipts,'Apple Development: QA','notary-profile','abc')
    with pytest.raises(RuntimeError,match='source'):
        b.release_gate(receipts,'Developer ID Application: QA','notary-profile','different')
    b.release_gate(receipts,'Developer ID Application: QA','notary-profile','abc')
    data=json.loads(receipts[0].read_text());data['native_smaart']=False
    receipts[0].write_text(json.dumps(data))
    with pytest.raises(RuntimeError,match='native acceptance'):
        b.release_gate(receipts,'Developer ID Application: QA','notary-profile','abc')
