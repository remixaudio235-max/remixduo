from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7\overlay_v7.py")
s=p.read_text(encoding="utf-8")
s=s.replace("import argparse,concurrent.futures,sys,time", "import argparse,concurrent.futures,sys,time,os")
s=s.replace("import win32gui,win32con", "import win32gui,win32con,win32process")
s=s.replace('''        self.setWindowFlags(Qt.WindowType.Tool|Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(354,385)''','''        self.setWindowFlags(Qt.WindowType.Tool|Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(354,385)''')
old='''    def tick(self):
        if self.demo:
            if self.host:
                x,y,w,h=self.host.geometry().getRect()
                shapes=self.host.plot_boxes()
                for widget,key in [(self.graph_mag,"MAGNITUDE"),(self.graph_phase,"PHASE")]:
                    a,b,c,d=shapes[key]
                    rect=(x+a,y+b,c,d)
                    if widget.geometry().getRect()!=rect:widget.setGeometry(*rect)
                self.overlay_positioned=self.host.isVisible()
                self.refresh_visibility()
                if self.isVisible() and self.geometry().x()!=x+w-350:
                    self.move(x+w-350,y+45)
            return
        target=locate_smaart()
        if target is None or not target.foreground:
            self.overlay_positioned=False;self.refresh_visibility()
            return'''
new='''    def _target_is_foreground(self,target_hwnd):
        front=win32gui.GetForegroundWindow()
        if not front:return False
        if front==target_hwnd:return True
        # Panel and its child popups may take focus during editing.
        # Any unrelated process => overlay MUST be hidden.
        try:
            _,pid=win32process.GetWindowThreadProcessId(front)
            return pid==os.getpid()
        except Exception:return False

    def tick(self):
        if self.demo:
            if self.host:
                attached=self.host.isVisible() and self._target_is_foreground(int(self.host.winId()))
                x,y,w,h=self.host.geometry().getRect()
                shapes=self.host.plot_boxes()
                for widget,key in [(self.graph_mag,"MAGNITUDE"),(self.graph_phase,"PHASE")]:
                    a,b,c,d=shapes[key]
                    rect=(x+a,y+b,c,d)
                    if widget.geometry().getRect()!=rect:widget.setGeometry(*rect)
                self.overlay_positioned=attached
                self.refresh_visibility()
                if attached and not self.isVisible():self.show()
                if not attached and self.isVisible():self.hide()
                if attached and self.geometry().x()!=x+w-350:
                    self.move(x+w-350,y+45)
            return
        target=locate_smaart()
        if target is None or not self._target_is_foreground(target.hwnd):
            self.overlay_positioned=False;self.refresh_visibility()
            if self.isVisible():self.hide()
            return
        if not self.isVisible():self.show()'''
assert old in s,"old tick source not found"
s=s.replace(old,new)
p.write_text(s,encoding="utf-8")
print("V7_OTHER_WINDOW_HIDE_PATCH_PASS")
