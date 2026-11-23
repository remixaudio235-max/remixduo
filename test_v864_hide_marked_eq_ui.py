"""V8.64: only presentation removal, preserve verified MagEq and LF/HF logic."""
from test_v845_fir_one_trace import init

def test_marked_autoeq_panels_hidden_but_models_and_actions_intact():
    app,obs,engine,hub,fir=init()
    try:
        hub.select("eq")
        hub.dock.show()
        app.processEvents()
        eq=hub.eq
        for widget in (eq.roi_status,eq.mageq_toggle,eq.native_state,
                       eq.summary,eq.details):
            assert widget.isHidden(),widget.objectName()
        assert len(eq._ux_sections)==2
        assert [section.text()[:2] for section in eq._ux_sections]==["01","02"]
        assert all(section.isVisible() for section in eq._ux_sections)
        assert hub.dock.heading.text()=="AUTO EQ"
        assert eq.height()==337
        assert hub.dock.page_heights["eq"]==337
        assert eq.mageq_toggle.isChecked()
        assert eq.calculate.isVisible()
        assert eq.export.isVisible()
        assert eq.filter_count.isVisible()
        assert eq.target.isVisible()
        assert eq._ux_gain_boost_row.indexOf(eq.boost)>=0
        assert eq._ux_gain_cut_row.indexOf(eq.cut)>=0
        assert eq.lf.value()==60
        old_hf=eq.hf.value()
        eq.drag_roi_to("HF",1200)
        app.processEvents()
        assert eq.hf.value()!=old_hf
        assert "VÙNG AUTO EQ" in eq.roi_status.text()
        assert eq.roi_status.isHidden()
        eq.native_state.setText("MagEQ HOLD: QA")
        eq.summary.setText("Preview QA")
        eq.details.setPlainText("Test internal feedback")
        assert eq.native_state.text()=="MagEQ HOLD: QA"
        assert eq.summary.text()=="Preview QA"
        assert eq.details.toPlainText()=="Test internal feedback"
        assert eq.native_state.isHidden() and eq.summary.isHidden()
        assert eq.details.isHidden()
    finally:
        hub.close()
        app.processEvents()
