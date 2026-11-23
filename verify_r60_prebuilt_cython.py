"""Check freshly compiled R60 protected artifact hashes before reusing."""
import hashlib,json,sys
from pathlib import Path
from build_cython_protected_v8154 import PROTECTED_MODULES,source_for
root=Path(__file__).resolve().parent
lib=root/"build"/"cython_lib"
try:
 m=json.loads((lib/"CYTHON_PROTECTED_MANIFEST.json").read_text(encoding="utf8"))
 assert set(m["artifacts"])==set(m["sources"])==set(PROTECTED_MODULES)
 assert (lib/"CYTHON_HIDDEN_IMPORTS.txt").stat().st_size>100
 for module in PROTECTED_MODULES:
  actual=hashlib.sha256(source_for(module).read_bytes()).hexdigest()
  assert m["sources"][module]==actual, ("SOURCE_CHANGED",module)
  artifact=m["artifacts"][module]
  file=(lib/artifact["file"]).resolve()
  assert lib.resolve() in file.parents
  assert file.is_file() and file.suffix.lower()==".pyd"
  assert hashlib.sha256(file.read_bytes()).hexdigest()==artifact["sha256"],module
 print("R60_REUSE_VERIFIED",len(PROTECTED_MODULES),flush=True)
except Exception as e:
 print("R60_REUSE_DENIED",repr(e),flush=True)
 sys.exit(2)
