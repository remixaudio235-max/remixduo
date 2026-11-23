from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_16_REALTIME_ROW_DOCK_QA\dock_geometry_v815.py")
s=p.read_text(encoding="utf8")
s=s.replace('''        if not all((tf,view,rt,impulse,spl)):
            return None''','''        if not all((rt,impulse,spl)):
            return None''')
s=s.replace('''        if view[1]-tf[3]<175 or tf[0]<0:return None
        return SidebarAnchors(tf[3],view[1],min(tf[0]-8,view[0]),
                              rt,impulse,spl,native)''',
'''        # The THREE tool buttons still follow Smaart when its TF Engine
        # sidebar is collapsed, hidden, or too short for the work panel.
        # TF/View anchors are optional; only the dock depends on them.
        if tf is None or view is None:
            return SidebarAnchors(-1,-1,rt[0],rt,impulse,spl,native)
        return SidebarAnchors(tf[3],view[1],min(tf[0]-8,view[0]),
                              rt,impulse,spl,native)''')
s=s.replace('''    dock_x=max(sl+2,min(r-width-3,sr-width-2))''','''    if anchors.tf_bottom<0 or anchors.view_top<0:
        return DockRects((x,real_y,width,real_h),None)
    dock_x=max(sl+2,min(r-width-3,sr-width-2))''')
p.write_text(s,encoding="utf8")
print("V816_NATIVE_TOOLBAR_INDEPENDENT_OF_SIDEBAR_PASS")
