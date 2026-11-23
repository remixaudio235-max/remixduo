from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7\overlay_v7.py")
ls=p.read_text(encoding="utf-8-sig").splitlines()
assert "RemiX" in ls[0]
assert "SIMULATED" in ls[127]
assert "self.status.setText" in ls[227]
assert "self.status.setText" in ls[248]
assert "self.status.setText" in ls[261]
assert "self.status.setText" in ls[269]
ls[0]='"""RemiX Auto Align V7 Windows - independent transparent SUM Phase/Mag overlay.'
ls[127]='        p.setPen(QColor("#dce9f4"));p.drawText(20,38,"SIMULATED Smaart Data Bar - runtime QA")'
ls[227]='        self.status.setText("Loading selected pair...")'
ls[248]='        self.status.setText("Pair ready - SUM Mag/Phase follows Smaart" if not self.demo'
ls[261]='            self.status.setText("Two confirmed traces required");return'
ls[269]='            self.status.setText("Insufficient coherence in LF-HF region");return'
p.write_text("\n".join(ls)+"\n",encoding="utf-8")
print("BAD_UNICODE_LINES",[(i+1,repr(line)) for i,line in enumerate(ls) if any(ord(ch)>127 for ch in line)])
