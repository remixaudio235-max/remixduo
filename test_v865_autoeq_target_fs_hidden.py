"""Auto EQ uses localized display names; algorithms get stable IDs."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from test_v845_fir_one_trace import init

def test_fs_not_visible_but_source_fs_still_live():
    app,obs,engine,hub,_=init()
    try:
        hub.select("eq")
        hub.dock.show()
        app.processEvents()
        eq=hub.eq
        assert eq.fs.isHidden()
        assert not eq.fs.isEnabled()
        assert eq.fs.currentData()==48000
        assert eq._fs_snapshot is not None
        assert hub.dock.heading.text()=="AUTO EQ"
        assert [x.text() for x in eq._ux_sections]==[
            "01  TRACE ĐO","02  CHỌN CHẾ ĐỘ"]
        assert eq.height()==337
        assert hub.dock.page_heights["eq"]==337
        assert eq.target.isVisible()
        assert eq.calculate.isVisible()
        assert eq.export.isVisible()
    finally:
        hub.close()
        app.processEvents()

def test_three_vietnamese_modes_keep_exact_solver_ids():
    app,obs,engine,hub,_=init()
    try:
        hub.select("eq")
        eq=hub.eq
        assert [eq.target.itemText(i) for i in range(eq.target.count())]==[
            "Phẳng","House (Trầm ấm)","Nghiêng"]
        assert [eq.target.itemData(i) for i in range(eq.target.count())]==[
            "Flat","House","Tilt"]
        for i,expected in enumerate(("Flat","House","Tilt")):
            eq.target.setCurrentIndex(i)
            app.processEvents()
            assert eq.target.currentData()==expected
            assert eq._parameters()["target"]==expected
            assert eq.fs.currentData()==48000
        assert eq.target.currentText()=="Nghiêng"
    finally:
        hub.close()
        app.processEvents()
