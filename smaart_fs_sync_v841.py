"""Read-only Smaart *saved configuration* sample-rate resolver.

No soundcard opening, no Smaart file changes and no sample-rate guessing from
TRF frequency bins. Smaart UI changes that have not been saved remain HOLD.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

CONFIG=Path.home()/"Documents/Smaart Suite/Config/SmaartConfig.xml"
SUPPORTED=frozenset((44100,48000,88200,96000,192000))


@dataclass(frozen=True)
class SavedSmaartFs:
    hz:int
    modified_ns:int
    size:int
    source:str="SmaartConfig.xml (saved)"


def read_saved_smaart_fs(path=None):
    if path is None:
        from smaart_runtime_paths_v868 import running_major,saved_config
        version=running_major()
        if version not in (8,9):return None
        config=saved_config(version)
        if config is None:return None
    else:
        config=Path(path)
    try:
        first=config.stat()
        root=ET.parse(config).getroot()
        # A global SampleRate is the Smaart session's saved setting.
        global_node=root.find("./Smaart-Config/Global/SampleRate")
        if global_node is None or global_node.text is None:return None
        rate=int(global_node.text.strip())
        if rate not in SUPPORTED:return None
        # Require all saved active source/destination rates to agree.
        # A disagreement is treated as unsafe rather than guessed away.
        for branch,entry in (("Sources","Source"),("Dests","Dest")):
            parent=root.find(f"./Smaart-Config/{branch}")
            if parent is None:return None
            rows=[n for n in parent if n.tag.startswith(entry)]
            if not rows:return None
            for row in rows:
                child=row.find("SampleRate")
                if child is None or child.text is None or int(child.text)!=rate:
                    return None
        last=config.stat()
        if (first.st_mtime_ns,first.st_size)!=(last.st_mtime_ns,last.st_size):
            return None
        return SavedSmaartFs(rate,last.st_mtime_ns,last.st_size,str(config.resolve()))
    except (OSError,ValueError,ET.ParseError):
        return None


class AsyncSavedFsCache:
    """Non-blocking saved-Fs snapshot for the Qt thread."""
    def __init__(self):
        self._pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix="remix_fs")
        self._future=None;self._signature=None;self._value=None
        self._future_signature=None;self._value_signature=None
    def get(self,path):
        path=Path(path) if path is not None else None
        if self._future is not None and self._future.done():
            try:
                value=self._future.result()
                if self._future_signature==self._signature:
                    self._value=value;self._value_signature=self._signature
            except Exception:self._value=None
            self._future=None;self._future_signature=None
        if path is None:
            self._signature=None
            self._value=None
            self._value_signature=None
            return None
        try:
            st=path.stat();signature=(str(path.resolve()),st.st_mtime_ns,st.st_size)
        except (OSError,TypeError):
            return None
        if signature!=self._signature:
            self._signature=signature;self._value=None
            self._value_signature=None
        if self._future is None and self._value_signature!=signature:
            self._future=self._pool.submit(read_saved_smaart_fs,path)
            self._future_signature=signature
        return self._value if self._value_signature==signature else None
    def close(self):
        from worker_lifecycle_v8142 import bounded_shutdown
        bounded_shutdown(self._pool)
