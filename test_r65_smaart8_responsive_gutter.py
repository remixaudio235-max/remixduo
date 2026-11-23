from types import SimpleNamespace

import mag_sum_native_v826 as module


def test_smaart8_axis_retries_inner_raster_when_role_box_has_gutters(monkeypatch):
    calls=[]
    monkeypatch.setattr(module,"capture_native_window",lambda hwnd:(object(),(0,0,1680,1002)))
    monkeypatch.setattr(module,"saved_mag_grid_interval",lambda *a,**k:None)
    monkeypatch.setattr(module,"fit_native_mag_grid",lambda *a,**k:
        module.SumMagAxis(False,reason="no grid"))
    monkeypatch.setattr("smaart8_api3_readonly_v868.process_smaart_major",lambda hwnd:8)

    def source(image,rect,window_rect,traces):
        calls.append(rect)
        if rect[0]==218 and rect[2]==1230:
            return module.SumMagAxis(True,-19.,18.,.91,1,"cyan","matched",240,20.,20000.)
        return module.SumMagAxis(False,reason="missing")
    monkeypatch.setattr(module,"_smaart8_native_source_axis",source)

    fit=module.capture_sum_mag_axis(1,(188,522,1290,387),(SimpleNamespace(),))
    assert fit.accepted and fit.score==.91
    assert (218,522,1230,387) in calls


def test_smaart8_axis_stops_after_first_strict_inner_match(monkeypatch):
    calls=[]
    monkeypatch.setattr(module,"capture_native_window",lambda hwnd:(object(),(0,0,1680,1002)))
    monkeypatch.setattr(module,"saved_mag_grid_interval",lambda *a,**k:None)
    monkeypatch.setattr(module,"fit_native_mag_grid",lambda *a,**k:
        module.SumMagAxis(False,reason="no grid"))
    monkeypatch.setattr("smaart8_api3_readonly_v868.process_smaart_major",lambda hwnd:8)

    def source(image,rect,window_rect,traces):
        calls.append(rect)
        if rect==(217,522,1232,387):
            return module.SumMagAxis(True,-19.,18.,.90,1,"cyan","matched",220,20.,20000.)
        return module.SumMagAxis(False,reason="missing")
    monkeypatch.setattr(module,"_smaart8_native_source_axis",source)

    fit=module.capture_sum_mag_axis(1,(188,522,1290,387),(SimpleNamespace(),))
    assert fit.accepted
    assert calls==[(188,522,1290,387),(217,522,1232,387)]


def test_smaart8_axis_remains_fail_closed_without_inner_match(monkeypatch):
    monkeypatch.setattr(module,"capture_native_window",lambda hwnd:(object(),(0,0,1366,720)))
    monkeypatch.setattr(module,"saved_mag_grid_interval",lambda *a,**k:None)
    monkeypatch.setattr(module,"fit_native_mag_grid",lambda *a,**k:
        module.SumMagAxis(False,reason="no grid"))
    monkeypatch.setattr("smaart8_api3_readonly_v868.process_smaart_major",lambda hwnd:8)
    monkeypatch.setattr(module,"_smaart8_native_source_axis",lambda *a,**k:
        module.SumMagAxis(False,reason="missing"))
    fit=module.capture_sum_mag_axis(1,(188,400,900,250),(SimpleNamespace(),))
    assert not fit.accepted and fit.reason=="missing"
