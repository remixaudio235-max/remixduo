"""Read-only native Mac probe. No GUI, audio, click/scroll or license changes."""
import _remix_bootstrap
import argparse
from dataclasses import asdict
from collections import Counter
import json
from pathlib import Path
import sys
import time

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--capture',action='store_true')
    args=parser.parse_args()
    if sys.platform!='darwin':raise RuntimeError('Native Mac probe requires macOS')
    from remix_duo.platforms.macos.permissions import status
    from remix_duo.platforms.macos.discovery import list_windows
    from remix_duo.platforms.macos.accessibility import tree_snapshot,read_selection
    report={'permissions':status(),'windows':[asdict(w) for w in list_windows()]}
    windows=[w for w in list_windows() if w.on_screen and w.foreground]
    args.output.mkdir(parents=True,exist_ok=True)
    if len(windows)!=1:
        report['status']='HOLD: cần duy nhất cửa sổ chính Smaart ở trước'
    else:
        w=windows[0]
        try:
            snapshot=tree_snapshot(w)
            (args.output/'ax_snapshot.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf-8')
            roles=Counter()
            def walk(node):
                if node is None:return
                roles[node.get('AXRole','')]+=1
                for child in node.get('children',[]):walk(child)
            walk(snapshot['root'])
            report.update(ax_roles=dict(roles),ax_complete=snapshot['complete'],ax_elapsed=snapshot['elapsed'])
            selection=read_selection(w)
            report['selection']=asdict(selection)
        except Exception as exc:report['ax_error']=str(exc)
        if args.capture:
            from remix_duo.platforms.macos.capture import capture_window
            try:
                frame=capture_window(w)
                (args.output/'smaart.png').write_bytes(frame.png)
                report['capture']={'width':frame.width,'height':frame.height,
                                   'age':time.monotonic()-frame.captured_at,'bytes':len(frame.png)}
            except Exception as exc:report['capture_error']=str(exc)
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))
    return 0

if __name__=='__main__':raise SystemExit(main())
