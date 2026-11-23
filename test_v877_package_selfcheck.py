"""V8.77 package self-check must not contend with the live overlay mutex."""
from pathlib import Path
import os
import subprocess
import sys


SOURCE = Path(__file__).with_name("overlay_v7.py")


def test_package_selfcheck_is_dispatched_before_single_instance_lock():
    text = SOURCE.read_text(encoding="utf-8")
    assert text.index('if "--package-selfcheck" in argv:') < text.index(
        "_single_instance=acquire_instance()"
    )


def test_source_package_selfcheck_runs_without_qapplication_or_mutex():
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, str(SOURCE), "--package-selfcheck"],
        cwd=SOURCE.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0
    assert "REMIX_DUO_PACKAGE_SELF_CHECK" in completed.stdout
    assert "ONLINE_CONFIGURED" in completed.stdout
    assert "V823_ALREADY_RUNNING" not in completed.stdout
