"""Build separate native offline-alpha .app/.dmg on each Mac architecture.

This is deliberately not a production signer or a Windows cross compiler.
"""
import argparse
from pathlib import Path
import platform
import subprocess
import sys
import hashlib
import json
import os
import plistlib
import tomllib

ROOT=Path(__file__).resolve().parents[2]

def project_version():
    data=tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))
    version=str(data['project']['version'])
    parts=version.split('.')
    if len(parts)!=3 or not all(part.isdigit() for part in parts):
        raise RuntimeError('pyproject project.version must be numeric MAJOR.MINOR.PATCH')
    return version

def preflight(arch, *, host=None, machine=None, version=None, translated=None):
    host=sys.platform if host is None else host
    if host!='darwin': raise RuntimeError('Build requires native macOS; Windows cannot cross-compile this app')
    machine=platform.machine() if machine is None else machine
    if arch not in ('x86_64','arm64') or arch!=machine:
        raise RuntimeError('Python/host architecture must match requested native architecture')
    if translated is None:
        r=subprocess.run(['/usr/sbin/sysctl','-in','sysctl.proc_translated'],capture_output=True,text=True)
        translated=r.returncode==0 and r.stdout.strip()=='1'
    if translated: raise RuntimeError('Rosetta build rejected; use native Python on target hardware')
    version=platform.mac_ver()[0] if version is None else version
    if not version or int(version.split('.')[0])<13:
        raise RuntimeError('macOS 13+ required')

def source_digest():
    digest=hashlib.sha256()
    for path in sorted((ROOT/'src').rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            digest.update(path.relative_to(ROOT).as_posix().encode());digest.update(path.read_bytes())
    return digest.hexdigest()

def release_gate(receipts=(),identity='',notary_profile='',digest=''):
    if len(receipts)!=2:raise RuntimeError('Release HOLD: native acceptance receipts required for Intel + Apple Silicon')
    if not identity.startswith('Developer ID Application:') or not notary_profile:
        raise RuntimeError('Release HOLD: Developer ID Application and Keychain notary profile required')
    architectures=set()
    for filename in receipts:
        receipt=json.loads(Path(filename).read_text('utf-8'))
        if receipt.get('source_sha256')!=digest:raise RuntimeError('Release HOLD: receipt source mismatch')
        architectures.add(receipt.get('architecture'))
        if not all(receipt.get(k) is True for k in ('shared_tests','frozen_selfcheck','native_smaart','clean_install')):
            raise RuntimeError('Release HOLD: native acceptance incomplete')
    if architectures!={'arm64','x86_64'}:raise RuntimeError('Release HOLD: native acceptance needs both CPU architectures')

def audit_architecture(app,arch):
    records=[]
    for path in sorted(app.rglob('*')):
        if not path.is_file() or path.is_symlink():continue
        with path.open('rb') as stream:magic=stream.read(4)
        if magic not in (b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe\xca',b'\xca\xfe\xba\xbf',b'\xbf\xba\xfe\xca'):
            continue
        slices=subprocess.check_output(['/usr/bin/lipo','-archs',str(path)],text=True).split()
        if arch not in slices:raise RuntimeError('Wrong native architecture: '+str(path))
        records.append({'file':str(path.relative_to(app)),'architectures':slices})
    if not records:raise RuntimeError('No native binaries found')
    return records

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arch',choices=['x86_64','arm64'],required=True)
    parser.add_argument('--check',action='store_true',help='Preflight only')
    parser.add_argument('--release',action='store_true')
    parser.add_argument('--receipt',type=Path,action='append',default=[])
    parser.add_argument('--identity',default=os.environ.get('DUO_DEVELOPER_IDENTITY',''))
    parser.add_argument('--notary-profile',default=os.environ.get('DUO_NOTARY_PROFILE',''))
    args=parser.parse_args(argv)
    preflight(args.arch)
    version=project_version()
    digest=source_digest()
    if args.release:release_gate(args.receipt,args.identity,args.notary_profile,digest)
    if sys.version_info[:2]!=(3,11):raise RuntimeError('Use native Python 3.11')
    if args.check:
        print('Native build preflight PASS; runtime/Smaart acceptance still HOLD')
        return 0
    subprocess.run([sys.executable,str(ROOT/'run_shared_tests.py')],cwd=ROOT,check=True)
    name='RemiXDuo' if args.release else 'RemiXDuo_Overlay_QA'
    destination=ROOT/'dist'/('macos-'+args.arch)
    build=ROOT/'build'/('macos-'+args.arch)
    build.mkdir(parents=True,exist_ok=True)
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir',
        '--name',name,'--target-arch',args.arch,'--osx-bundle-identifier','com.remixaudio.duo.alpha',
        '--paths',str(ROOT/'src'),'--collect-data','remix_duo',
        '--add-data',str(ROOT/'src/remix_duo/resources')+':remix_duo/resources',
        '--distpath',str(destination),'--workpath',str(build/'work'),'--specpath',str(build),
        str(ROOT/'run_remix_duo.py')]
    if args.release:
        command[command.index('com.remixaudio.duo.alpha')]='com.remixaudio.duo'
        command.extend(['--codesign-identity',args.identity])
    subprocess.run(command,cwd=ROOT,check=True,env={**os.environ,'MACOSX_DEPLOYMENT_TARGET':'13.0'})
    app=destination/(name+'.app')
    plist=app/'Contents/Info.plist'
    info=plistlib.loads(plist.read_bytes())
    info.update(LSMinimumSystemVersion='13.0',CFBundleShortVersionString=version,
                CFBundleVersion=version,NSHighResolutionCapable=True)
    plist.write_bytes(plistlib.dumps(info))
    # Re-seal the outer bundle after Info.plist metadata changes. Nested binaries
    # have already been signed by PyInstaller; do not deep-sign dependencies.
    sign=['/usr/bin/codesign','--force','--sign',args.identity if args.release else '-']
    if args.release:sign+=['--options','runtime','--timestamp']
    subprocess.run(sign+[str(app)],check=True)
    subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app)],check=True)
    architecture=audit_architecture(app,args.arch)
    # Frozen read-only check: no GUI/audio/license write.
    subprocess.run([str(app/'Contents/MacOS'/name),'--selfcheck'],cwd=build,check=True)
    channel='release' if args.release else 'overlay-qa'
    dmg=destination/f'RemiXDuo-{version}-{channel}-{args.arch}.dmg'
    subprocess.run(['/usr/bin/hdiutil','create','-ov','-volname','RemiX Duo Offline Alpha',
                    '-srcfolder',str(app),'-format','UDZO',str(dmg)],check=True)
    if args.release:
        subprocess.run(['/usr/bin/codesign','--sign',args.identity,'--timestamp',str(dmg)],check=True)
        result=subprocess.check_output(['/usr/bin/xcrun','notarytool','submit',str(dmg),
            '--keychain-profile',args.notary_profile,'--wait','--output-format','json'],text=True)
        if json.loads(result).get('status')!='Accepted':raise RuntimeError('Notarization rejected; no public release')
        subprocess.run(['/usr/bin/xcrun','stapler','staple',str(dmg)],check=True)
        subprocess.run(['/usr/bin/xcrun','stapler','validate',str(dmg)],check=True)
    record={'architecture':args.arch,'source_sha256':digest,'shared_tests':True,'frozen_selfcheck':True,
            'native_smaart':False,'clean_install':False,'signed_public_release':args.release,
            'dmg_sha256':hashlib.sha256(dmg.read_bytes()).hexdigest(),'native_binaries':architecture}
    (destination/'build-evidence.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(str(dmg))
    print('SIGNED/NOTARIZED RELEASE' if args.release else 'LOCAL OFFLINE ALPHA ONLY. Native Smaart acceptance: HOLD.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
