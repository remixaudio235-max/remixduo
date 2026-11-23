from pathlib import Path

import r65_source_manifest as manifest


def test_manifest_excludes_itself_and_hashes_tracked_source():
    files = manifest.tracked_files()
    assert files
    assert manifest.MANIFEST not in files
    assert all(path.is_file() and path.is_relative_to(manifest.ROOT) for path in files)
    assert all(len(line.split("  ", 1)[0]) == 64 for line in manifest.expected_lines())


def test_r65_version_metadata_is_consistent():
    root = Path(__file__).resolve().parent
    assert '__version__ = "8.181"' in (root / "src/remix_duo/__init__.py").read_text()
    assert 'version = "8.181.0"' in (root / "pyproject.toml").read_text()
    for name in ("main", "watcher", "setup"):
        text = (root / f"version_info_v8181_{name}.txt").read_text()
        assert "8.181.0.0" in text


def test_builder_verifies_manifest_before_restricting_path():
    root = Path(__file__).resolve().parent
    script = (root / "build_r65_full_release_qa.ps1").read_text(encoding="utf-8-sig")
    verify = script.index("r65_source_manifest.py")
    restricted_path = script.index("$env:PATH =")
    assert verify < restricted_path
