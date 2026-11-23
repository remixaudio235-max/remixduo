"""Create or verify the immutable tracked-source manifest used by R65 builds."""
from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "RELEASE_SOURCE_MANIFEST_R65.sha256"
EXCLUDED = {MANIFEST.name}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True)
    names = [part.decode("utf-8") for part in result.stdout.split(b"\0") if part]
    return [ROOT / name for name in sorted(names) if name not in EXCLUDED]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def expected_lines() -> list[str]:
    return [f"{digest(path)}  {path.relative_to(ROOT).as_posix()}"
            for path in tracked_files()]


def verify() -> bool:
    if not MANIFEST.is_file():
        return False
    actual = MANIFEST.read_text(encoding="utf-8").splitlines()
    return actual == expected_lines()


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.write:
        MANIFEST.write_text("\n".join(expected_lines()) + "\n", encoding="utf-8")
        print(f"R65_SOURCE_MANIFEST_WRITTEN {MANIFEST}")
        return 0
    ok = verify()
    print("R65_SOURCE_MANIFEST_PASS" if ok else "R65_SOURCE_MANIFEST_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
