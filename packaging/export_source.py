"""Reproducible source-only transfer to native build hosts; no secrets/artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

def export(root,destination):
    root=Path(root).resolve();destination=Path(destination)
    paths=list(root.glob('*.py'))+list(root.glob('*.ps1'))+list(root.glob('*.iss'))
    paths += [root/'pyproject.toml']
    for name in ('src','tests/shared','tests/contracts','packaging','engines'):
        folder=root/name
        paths += [p for p in folder.rglob('*') if p.is_file() and
                  p.suffix.lower() in ('.py','.md','.jpg','.png','.icns','.plist','.sh','.json','.txt') and
                  not any(x in p.parts for x in ('__pycache__','dist','build','.pytest_cache'))]
    files={}
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Source path escapes source root')
        name=path.relative_to(root).as_posix()
        if any(x in name for x in ('.env','.dev.vars','.lic','.key','.pem')):continue
        files[name]=path.read_bytes()
    hashes={name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())}
    files['MANIFEST.sha256.json']=json.dumps(hashes,sort_keys=True,indent=2).encode()
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,(2026,11,3,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            archive.writestr(info,data)
    return hashes

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    files=export(Path(__file__).resolve().parents[1],args.destination)
    print(json.dumps({'files':len(files),'bytes':args.destination.stat().st_size,
                      'sha256':hashlib.sha256(args.destination.read_bytes()).hexdigest()}))
