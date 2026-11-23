"""Apply V8.18 adaptive toolbar modes and never-hide-on-resize behavior.

Source is cloned V8.17 (preserves trace + Top 3 candidate selection);
the older V8.16/V8.17 QA files remain unchanged.
"""
from pathlib import Path
root=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_18_RESPONSIVE_DOCK_QA")
p=root/"signal_tools_gui_v813.py"
s=p.read_text(encoding="utf-8")
s=s.replace('self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)',
            'self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)')
s=s.replace('self.setWindowTitle("RemiX Signal V8.16")',
            'self.setWindowTitle("RemiX Signal V8.18")')
assert 'self.nav_frame=self' in s
s=s.replace('''        self.nav_frame=self
        self.title_bar=None''',
'''        self.nav_frame=self
        self.title_bar=None
        self._toolbar_mode="full"
        self._panel_mode="dock"
        self._last_anchor_good=None''')
needle='''        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)'''
assert s.count(needle)==1
s=s.replace(needle,'''        # Resized mode: compact labels or a real clickable menu button.
        self.menu_button=QPushButton("RemiX ▾")
        self.menu_button.setObjectName("responsiveMenu")
        self.menu_button.setToolTip("RemiX Signal — chọn công cụ")
        menu=QMenu(self.menu_button)
        for mode,text in (("phase","Auto Phase"),("eq","Auto EQ"),("fir","FIR")):
            action=menu.addAction(text)
            action.triggered.connect(lambda _,m=mode:self.select(m))
        self.menu_button.setMenu(menu)
        main.addWidget(self.menu_button)
        self.menu_button.hide()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)''')
needle='''        self.timer=QTimer(self)
        self.timer.timeout.connect(self.tick)'''
assert s.count(needle)==1
s=s.replace(needle,'''        self._set_toolbar_mode("full")
        self.timer=QTimer(self)
        self.timer.timeout.connect(self.tick)''')
needle='''    def select(self,mode):
        if mode not in self.pages:raise ValueError("Unknown tool")'''
assert s.count(needle)==1
s=s.replace(needle,'''    def _set_toolbar_mode(self,mode):
        if mode not in ("full","compact","mini","menu"):
            raise ValueError("Unknown responsive mode")
        self._toolbar_mode=mode
        labels={
            "full":("Auto Phase","Auto EQ","FIR"),
            "compact":("A.Phase","A.EQ","FIR"),
            "mini":("AP","EQ","FIR")
        }
        if mode=="menu":
            for button in self.buttons.values():button.hide()
            self.menu_button.show()
            self.menu_button.setText("RemiX ▾")
            self.menu_button.setStyleSheet(
                "font:bold 9px 'Segoe UI';min-height:21px;"
                "background:#FF9D35;color:#101923;border:0;border-radius:4px;")
        else:
            self.menu_button.hide()
            for (name,button),text in zip(self.buttons.items(),labels[mode]):
                button.setText(text)
                button.setMinimumWidth(0)
                button.show()
        # In compact mode, the current tool remains selected; only
        # its presentation changes. Do not reset Auto Phase/EQ/FIR data.
        self._style_buttons()

    def _style_buttons(self):
        for name,button in self.buttons.items():
            button.setStyleSheet(
                "font:bold 9px 'Segoe UI';min-width:0px;min-height:22px;"
                +("background:#FF9D35;color:#121820;border:0;"
                  "border-radius:4px;" if name==self.active else
                  "background:#18364A;color:#B6D8E4;"
                  "border:1px solid #315169;border-radius:4px;"))

    def select(self,mode):
        if mode not in self.pages:raise ValueError("Unknown tool")''')
needle='''        for name,button in self.buttons.items():
            button.setStyleSheet(
                "font:bold 9px 'Segoe UI';min-height:27px;"
                +("background:#FF9D35;color:#121820;border:0;"
                  "border-radius:4px;" if name==mode else
                  "background:#18364A;color:#B6D8E4;"
                  "border:1px solid #315169;border-radius:4px;"))'''
assert s.count(needle)==1
s=s.replace(needle,'''        self._style_buttons()''')
start=s.index('    def _update_placements(self,host):',s.index('class ToolHub('))
end=s.index('    def tick(self):',start)
new='''    def _update_placements(self,host):
        # Even when Smaart temporarily loses UIA anchors we provide
        # a visible fallback menu on the same approximate native row.
        rects=compute_dock_rects(host,self._anchors,self._screen_rect())
        if rects is None:
            # Degenerate/minimized host only; tick handles minimized.
            self.hide()
            self.dock.hide()
            return False
        x,y,w,h=rects.toolbar
        if self._toolbar_mode!=rects.toolbar_mode:
            self._set_toolbar_mode(rects.toolbar_mode)
        self.setFixedSize(w,h)
        self.move(x,y)
        if not self.isVisible():self.show()
        self._panel_mode=rects.panel_mode
        self.dock.apply_rect(rects.panel)
        self.dock.heading.setToolTip(
            "Panel: "+rects.panel_mode+" | Kéo nội dung để cuộn")
        if not self.dock.isVisible():self.dock.show()
        return True

'''
s=s[:start]+new+s[end:]
needle='''                self._anchors=latest
            except Exception:
                anchor_changed=self._anchors is not None
                self._anchors=None'''
assert s.count(needle)==1
s=s.replace(needle,'''                # A transient UIA failure must not make the whole
                # companion disappear. Retain last recognized row.
                if latest is not None:
                    self._last_anchor_good=latest
                    self._anchors=latest
                else:
                    self._anchors=self._last_anchor_good
                anchor_changed=(self._anchors!=previous_anchors)
            except Exception:
                self._anchors=self._last_anchor_good
                anchor_changed=(self._anchors!=previous_anchors)''')
needle='''        anchor_changed=False
        if self._anchor_future is not None and self._anchor_future.done():'''
assert s.count(needle)==1
s=s.replace(needle,'''        anchor_changed=False
        previous_anchors=self._anchors
        if self._anchor_future is not None and self._anchor_future.done():''')
needle='''        if target.hwnd!=self._last_hwnd:
            self._anchors=None'''
assert s.count(needle)==1
s=s.replace(needle,'''        if target.hwnd!=self._last_hwnd:
            self._last_anchor_good=None
            self._anchors=None''')
needle='''        if self._anchors is not None:
            if (anchor_changed or not self._was_target or
                rect!=previous_rect or not self.isVisible()):
                self._update_placements(rect)
        else:
            self.hide()
            self.dock.hide()'''
assert s.count(needle)==1
s=s.replace(needle,'''        if (anchor_changed or not self._was_target or
            rect!=previous_rect or not self.isVisible() or
            not self.dock.isVisible()):
            self._update_placements(rect)''')
p.write_text(s,encoding="utf-8")
p=root/"overlay_v7.py"
s=p.read_text(encoding="utf-8").replace("V8.17","V8.18")
p.write_text(s,encoding="utf-8")
print("V818_RESPONSIVE_GUI_PATCHED")
