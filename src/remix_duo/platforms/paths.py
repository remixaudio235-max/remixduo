from dataclasses import dataclass
import os
from pathlib import Path
import sys

@dataclass(frozen=True)
class AppPaths:
    data: Path
    resources: Path

    @property
    def license(self):
        return self.data / 'license.lic'

    def resource(self, name: str) -> Path:
        if not name or '/' in name or '\\' in name or name in ('.','..'):
            raise ValueError('Resource must be a single filename')
        return self.resources / name

def app_paths(platform=None, *, environ=None, home=None):
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    if platform == 'win32':
        base = environ.get('LOCALAPPDATA')
        if not base:
            raise RuntimeError('LOCALAPPDATA_UNAVAILABLE')
        data = Path(base) / 'RemiXAudio' / 'Duo'
    elif platform == 'darwin':
        data = home / 'Library' / 'Application Support' / 'RemiXAudio' / 'Duo'
    else:
        raise RuntimeError('UNSUPPORTED_PLATFORM')
    return AppPaths(data, Path(__file__).resolve().parents[1] / 'resources')
