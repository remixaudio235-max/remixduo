import os
from pathlib import Path
from xml.etree import ElementTree as ET
from selection_v7 import archive_order
from full_scan_v7 import _uia
from trf_core import read_trf
from win_databar_v7 import locate_smaart
root=Path(r'C:\Users\Admin\Documents\Smaart Suite\Data\Transfer Function')
folder=root/'Session Data'
files=list(folder.glob('*.trf'))
idx=[(q.attrib.get('adhocIndex'),q.text) for q in ET.parse(root/'index.xml').getroot().findall('.//path') if str(q.text).lower().endswith('.trf')]
print('TRF_COUNT',len(files),'INDEX_PATHS',len(idx))
print('LATEST_FILES',[(q.name,q.stat().st_size) for q in sorted(files,key=lambda q:q.stat().st_mtime,reverse=True)[:4]])
print('INDEX_FIRST5',idx[:5])
print('INDEX_IMPORT',[(name,any(name.casefold() in str(z[1]).casefold() for z in idx)) for name in ('4,8 ms delay-1.trf','0 delay-1.trf')])
try:
    order=archive_order(folder)
    print('ARCHIVE_OK',len(order))
except Exception as exc:
    print('ARCHIVE_ERROR',repr(exc))
window=locate_smaart()
print('WINDOW',window)
root_u,bar,rows=_uia(window.hwnd)
print('UIA_COUNT',len(rows),'ROW_FIRST',[(i,rows[i].element_info.name,rows[i].rectangle().top) for i in range(min(3,len(rows)))])
for name in ('4,8 ms delay-1.trf','0 delay-1.trf'):
    try:
        t=read_trf(folder/name)
        print('NEW_TRF',name,'GOOD',len(t.hz),t.kind,t.hz[0],t.hz[-1])
    except Exception as exc:
        print('NEW_TRF_ERROR',name,repr(exc))
