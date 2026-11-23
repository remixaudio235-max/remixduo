"""Compatibility alias to the shared licensing implementation."""
import _remix_bootstrap
import sys
from remix_duo.licensing import gate as _canonical
sys.modules[__name__] = _canonical
