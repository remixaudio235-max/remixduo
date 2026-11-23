"""Portable test runner. Never starts Smaart/audio/native UI observers."""
from pathlib import Path
import os
import subprocess
import sys
if __name__=='__main__':
    root=Path(__file__).resolve().parent
    env={**os.environ,'QT_QPA_PLATFORM':'offscreen','PYTHONPATH':str(root/'src')}
    raise SystemExit(subprocess.call([sys.executable,'-m','pytest','-q','tests/shared','tests/contracts','--tb=short'],cwd=root,env=env))
