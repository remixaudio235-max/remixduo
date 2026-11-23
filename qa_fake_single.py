"""Minimal snapshot fixture for old export/mageq QA after V16 one-tick refactor.

Not used by runtime. Real V16 scanner tests exercise stable 3/3 separately.
"""
from pathlib import Path
class FakeSingle:
    def __init__(self,path=None):
        self.selected=None
        self.hwnd=0
        self.folder=None
        self.set_path(path)
    def set_path(self,path):
        if path is None:
            self.selected=None
        else:
            file=Path(path)
            self.folder=file.parent
            stat=file.stat()
            self.selected=(str(file),stat.st_mtime_ns,stat.st_size,1)
    def current_single(self):
        return self.selected
