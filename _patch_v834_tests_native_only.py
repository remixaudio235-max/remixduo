"""Adjust V8.34 tests: native-confirmed delta, never speculative mouse delta."""
from pathlib import Path
p=Path(__file__).with_name('test_v834_large_y_fast_lane.py')
s=p.read_text(encoding='utf-8')
def one(a,b):
 global s
 if s.count(a)!=1:raise RuntimeError('Test block not unique '+a[:70])
 s=s.replace(a,b)
one('    assert graph.y_max==pytest.approx(\n'
    '        base[1]+change*(base[1]-base[0])/rect[3])\n'
    '    assert graph.y_max>previous_max\n',
    '    assert graph.y_max==pytest.approx(base[1]), "Mouse-only motion is not native pan"\n'
    '    # Four genuine 40/45px native Y movements fit the 89px tracker cap.\n'
    '    def send_native(dy):\n'
    '        good=PanFrame(float(dy),.99,True,"native confirmed",1.,time.monotonic())\n'
    '        weak=PanFrame(0.,0.,False,"other axis",1.,time.monotonic())\n'
    '        currentkey=(41,e.plot_layout.phase,e.plot_layout.mag,\n'
    '                    e.current_pair,e._reference_index(),e._viewport_epoch)\n'
    '        pack=DualPanResult(good,weak) if kind=="phase" else DualPanResult(weak,good)\n'
    '        e.on_native_dual_pan((currentkey,pack))\n'
    '    for _ in range(4):send_native(change/4.)\n'
    '    assert graph.y_max==pytest.approx(\n'
    '        base[1]+change*(base[1]-base[0])/rect[3])\n'
    '    assert graph.y_max>previous_max\n')
one('    cursor[1]-=change\n'
    '    check(target)\n'
    '    assert graph.y_min==pytest.approx(base[0])\n',
    '    cursor[1]-=change\n'
    '    check(target)\n'
    '    assert graph.y_max>base[1], "Pointer return without native movement must not snap"\n'
    '    for _ in range(4):send_native(-change/4.)\n'
    '    assert graph.y_min==pytest.approx(base[0])\n')
one('    cursor[1]+=160\n'
    '    e._check_mag_axis_drag(target)\n'
    '    assert e.graph_phase.y_max==180.\n'
    '    assert e.graph_mag.y_max>30.\n',
    '    cursor[1]+=160\n'
    '    e._check_mag_axis_drag(target)\n'
    '    assert e.graph_phase.y_max==180.\n'
    '    assert e.graph_mag.y_max==20., "Mag must not follow pointer without native trace"\n'
    '    key=(41,e.plot_layout.phase,e.plot_layout.mag,e.current_pair,\n'
    '         e._reference_index(),e._viewport_epoch)\n'
    '    for _ in range(4):\n'
    '        stamp=time.monotonic()\n'
    '        good=PanFrame(40.,.99,True,"verified source",1.,stamp)\n'
    '        none=PanFrame(0.,0.,False,"not moved",1.,stamp)\n'
    '        e.on_native_dual_pan((key,DualPanResult(none,good)))\n'
    '    assert e.graph_phase.y_max==180.\n'
    '    assert e.graph_mag.y_max>30.\n')
p.write_text(s,encoding='utf-8')
print('NATIVE_ONLY_TESTS_READY')
