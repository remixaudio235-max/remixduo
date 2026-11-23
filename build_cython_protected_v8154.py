"""Compile release-only native modules without modifying shared source."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
from pathlib import Path

from Cython.Build import cythonize
from setuptools import Extension, setup

ROOT = Path(__file__).resolve().parent
PROTECTED_MODULES = (
    "_remixduo_native",
    "uia_serial_v8152",
    "autoeq_core", "autoeq_peak_rescue_v849", "autoeq_peak_shape_v859",
    "autoeq_q_policy_v852", "autoeq_spacing_v850", "fir_dsp_export_v872",
    "mageq_trace_v07", "remix_autoeq_v05_adapter",
    "remix_duo.core.align_confidence", "remix_duo.core.autoeq_engine",
    "remix_duo.core.autoeq", "remix_duo.core.filters",
    "remix_duo.core.fir_export", "remix_duo.core.fir_preview",
    "remix_duo.core.fir_quality_gate",
    "remix_duo.core.peak_rescue", "remix_duo.core.peak_shape",
    "remix_duo.core.phase_tools", "remix_duo.core.q_policy",
    "remix_duo.core.smoothing", "remix_duo.core.spacing",
    "remix_duo.core.traces", "remix_duo.licensing.gate",
    "remix_duo.licensing.online", "remix_duo.update.github_release",
)


def source_for(module: str) -> Path:
    if module == "_remixduo_native":
        return ROOT / "overlay_v7.py"
    relative = Path(*module.split(".")).with_suffix(".py")
    package = ROOT / "src" / relative
    return package if package.is_file() else ROOT / relative


def build(output: Path, temp: Path) -> dict:
    for path in (output, temp):
        resolved = path.resolve()
        if ROOT not in resolved.parents or resolved == ROOT:
            raise ValueError(f"Unsafe Cython build path: {resolved}")
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)

    extensions, sources = [], {}
    stage = temp / "src"
    stage.mkdir(parents=True, exist_ok=True)
    for module in PROTECTED_MODULES:
        source = source_for(module)
        if not source.is_file():
            raise FileNotFoundError(f"Missing protected source: {source}")
        sources[module] = hashlib.sha256(source.read_bytes()).hexdigest()
        staged_name = "overlay_v7.py" if module == "_remixduo_native" else None
        staged = stage / (staged_name or Path(*module.split(".")).with_suffix(".py"))
        staged.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, staged)
        extensions.append(Extension(module, [str(staged.relative_to(ROOT))]))

    os.chdir(ROOT)
    compiled = cythonize(
        extensions, build_dir=str(temp / "c"),
        compiler_directives={"language_level": 3, "binding": True,
                             "embedsignature": False,
                             "emit_code_comments": False},
        annotate=False, force=True, nthreads=0, quiet=True)
    setup(name="remixduo-protected-core", version="8.181.0",
          ext_modules=compiled,
          script_args=["build_ext", "--build-lib", str(output),
                       "--build-temp", str(temp / "obj")])

    artifacts = {}
    for module in PROTECTED_MODULES:
        module_path = Path(*module.split("."))
        candidates = list((output / module_path.parent).glob(
            f"{module_path.name}.*.pyd"))
        if len(candidates) != 1:
            raise RuntimeError(f"Expected one PYD for {module}, got {candidates}")
        artifacts[module] = {
            "file": candidates[0].relative_to(output).as_posix(),
            "sha256": hashlib.sha256(candidates[0].read_bytes()).hexdigest()}
    tree = ast.parse((ROOT / "overlay_v7.py").read_text(encoding="utf-8"))
    hidden_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            hidden_imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            hidden_imports.add(node.module)
    hidden_imports.difference_update({"__future__", "overlay_v7", "_remixduo_native"})
    hidden_imports = sorted(hidden_imports)
    (output / "CYTHON_HIDDEN_IMPORTS.txt").write_text(
        "\n".join(hidden_imports) + "\n", encoding="utf-8")
    manifest = {"cython": "3.1.5", "sources": sources,
                "artifacts": artifacts, "hidden_imports": hidden_imports}
    (output / "CYTHON_PROTECTED_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=ROOT / "build" / "cython_lib")
    parser.add_argument("--temp", type=Path,
                        default=ROOT / "build" / "cython_temp")
    args = parser.parse_args()
    result = build(args.output, args.temp)
    print(f"CYTHON_PROTECTED_MODULES={len(result['artifacts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
