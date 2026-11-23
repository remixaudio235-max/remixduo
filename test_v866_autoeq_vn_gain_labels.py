"""V8.66 localized Auto EQ labels, regression of controls and 205px UI."""
from test_v845_fir_one_trace import init

def test_vietnamese_peq_boost_cut_labels_and_layout():
    app,obs,engine,hub,fir=init()
    try:
        hub.select("eq")
        hub.dock.apply_rect((580,140,205,560))
        hub.dock.show()
        app.processEvents()
        eq=hub.eq
        assert eq.filter_count.prefix()=="Số PEQ tối đa "
        assert eq.filter_count.accessibleName()=="Số PEQ tối đa"
        assert [label.text() for label in eq._ux_gain_labels]==[
            "Nâng tối đa","Cắt tối đa"]
        assert eq.boost.accessibleName()=="Nâng tối đa, dB"
        assert eq.cut.accessibleName()=="Cắt tối đa, dB"
        assert eq._ux_gain_row.count()==2
        assert eq._ux_gain_boost_row.indexOf(eq.boost)>=0
        assert eq._ux_gain_cut_row.indexOf(eq.cut)>=0
        assert eq._ux_gain_labels[0].isVisible()
        assert eq._ux_gain_labels[1].isVisible()
        assert eq.filter_count.isVisible()
        assert eq.boost.isVisible() and eq.cut.isVisible()
        assert eq.calculate.isVisible()
        assert eq.export.isVisible()
        assert eq.height()==337 and hub.dock.width()==205
        assert eq.filter_count.value()==0
        assert eq.filter_count.specialValueText()=="AUTO"
        assert eq.boost.value()==0 and eq.cut.value()==-12
        assert eq.boost.specialValueText()=="AUTO"
        assert eq.cut.specialValueText()=="AUTO"
        assert eq.boost.isEnabled() and eq.cut.isEnabled()
        assert eq.boost.maximum()==6 and eq.cut.minimum()==-12
        assert eq.filter_count.maximum()==12
        assert eq.boost.width()>=72 and eq.cut.width()>=72
        assert eq._ux_gain_labels[0].width()>=80
        assert eq._ux_gain_boost_row.itemAt(0).widget().x() < eq.boost.x()
        eq.filter_count.setValue(10)
        assert eq.filter_count.value()==10
        assert eq.result is None
    finally:
        hub.close()
        app.processEvents()
