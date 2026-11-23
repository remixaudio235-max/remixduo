"""Compatibility alias; canonical implementation lives in remix_duo.core."""
import _remix_bootstrap
import sys
from remix_duo.core import q_policy as _canonical
sys.modules[__name__] = _canonical
