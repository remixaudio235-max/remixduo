from pathlib import Path
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_18_RESPONSIVE_DOCK_QA")
p=root/"dock_geometry_v815.py"
s=p.read_text(encoding="utf8")
needle='''    mode,tw=choose_toolbar_mode(available)
    toolbar_x=rx-tw-3'''
assert s.count(needle)==1
s=s.replace(needle,'''    mode,tw=choose_toolbar_mode(available)
    if not valid:
        # UIA row missing: show safe menu until native buttons verified.
        mode,tw="menu",68
    toolbar_x=rx-tw-3''')
p.write_text(s,encoding="utf8")
p=root/"qa_responsive_v818.py"
s=p.read_text(encoding="utf8")
needle='''        assert len(hub.menu_button.menu().actions())==3'''
assert s.count(needle)==1
s=s.replace(needle,'''        assert len(hub.menu_button.menu().actions())==3
        for i,expected_mode in enumerate(("phase","eq","fir")):
            hub.menu_button.menu().actions()[i].trigger()
            assert hub.active==expected_mode
        hub.select("phase")''')
needle='''assert rr and rr.panel is not None
print("MISSING_NATIVE_ANCHORS_FALLBACK_PASS"'''
assert s.count(needle)==1
s=s.replace(needle,'''assert rr and rr.panel is not None and rr.toolbar_mode=="menu"
print("MISSING_NATIVE_ANCHORS_FALLBACK_PASS"''')
p.write_text(s,encoding="utf8")
print("V818_MENU_FALLBACK_TEST_PATCH_PASS")
