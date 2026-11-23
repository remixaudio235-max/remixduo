from pathlib import Path
from full_scan_v7 import full_scan
from win_databar_v7 import locate_smaart
from selection_v7 import archive_order,fresh_unindexed_imports
from trf_core import read_trf,phase_match_percent,compute_sum,auto_align
folder=Path(r'C:\Users\Admin\Documents\Smaart Suite\Data\Transfer Function\Session Data')
order=archive_order(folder)
print('ORDER_FIRST4', [p.name for p in order[:4]], 'NEW_IMPORT_COUNT',len(fresh_unindexed_imports(folder)))
assert len(order)==108
assert [p.name for p in order[:2]]==['4,8 ms delay-1.trf','0 delay-1.trf']
win=locate_smaart()
result=full_scan(win.hwnd,folder)
print('SCAN',result.covered,result.total,result.captures,'scroll',result.scroll_start,result.scroll_end)
print('ACTIVE', [Path(n).name for n in result.active])
print('STATE_FIRST8', result.states[:8])
assert result.covered==result.total==108
assert result.states[0]=='on' and result.states[1]=='on', 'Imported trace ticks were not detected'
assert len(result.active)==2, f'Expected exact two imported active rows; got {result.active}'
assert tuple(Path(n).name for n in result.active)==('4,8 ms delay-1.trf','0 delay-1.trf')
a,b=(read_trf(p) for p in result.active)
print('TF_READ',len(a.hz),len(b.hz),'kind',a.kind,b.kind)
summed=compute_sum(a,b,mag_oct=1/6,phase_oct=1/6)
print('SUM_BINS',len(summed.hz))
score,n=phase_match_percent(a,b,lf=60,hf=200)
print('PHASE_MATCH',score,n)
solutions=auto_align(a,b,lf=60,hf=200)
print('TOPK',[(round(x.delay_ms,2),x.invert_trace2,round(x.score_db,3)) for x in solutions])
print('V75_LIVE_FULL_IMPORT_PASS')
