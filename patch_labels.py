from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7\overlay_v7.py")
lines=p.read_text(encoding="utf-8").splitlines()
out=[]
for i,line in enumerate(lines):
    stripped=line.strip()
    if stripped.startswith('self.setWindowTitle(') and 'V7' in line:
        line='        self.setWindowTitle("RemiX Auto Align V7 - Windows QA")'
    elif stripped.startswith('self.pair_label=QLabel('):
        line='        self.pair_label=QLabel("Ch\\u01b0a x\\u00e1c minh \\u0111\\u1ee7 2 Trace b\\u1eadt",self)'
    elif stripped.startswith('self.status=QLabel('):
        line='        self.status=QLabel("\\u0110ang ch\\u1edd Smaart",self);self.status.setObjectName("status")'
    elif stripped.startswith('self.invert=QCheckBox('):
        line='        self.invert=QCheckBox("\\u0110\\u1ea3o Trace 2");self.invert.stateChanged.connect(self.recalc)'
    elif stripped.startswith('self.candidates=[QLabel('):
        line='        self.candidates=[QLabel("-") for _ in range(3)]'
    elif stripped.startswith('self.notes=QLabel('):
        line='        self.notes=QLabel("TF l\\u01b0u tr\\u1eef - kh\\u00f4ng nh\\u1eadn TF tr\\u1ef1c ti\\u1ebfp qua Smaart API",self)'
    elif 'self.candidates:label.setText(' in line:
        line='        for label in self.candidates:label.setText("-")'
    elif 'self.pair_label.setText(' in line and 'TRACE 1' not in line:
        line='            self.pair_label.setText("Ch\\u01b0a c\\u00f3 2 Trace - SUM \\u0111\\u00e3 \\u1ea9n")'
    elif stripped.startswith('self.status.setText(') and 'result' not in line:
        if 'str(exc)' in line:
            line='            self.status.setText("Kh\\u00f4ng \\u0111\\u1ecdc \\u0111\\u01b0\\u1ee3c Trace: "+str(exc)[:120])'
        elif 'self.current_traces' not in line and 'status' not in line and 'Delay ' not in line:
            if line.startswith('        self.status.setText(') and ' if not self.demo' in line:
                line='        self.status.setText("C\\u1eb7p \\u0111\\u00e3 \\u0111\\u1ed3ng b\\u1ed9 - SUM Mag/Phase b\\u00e1m c\\u1eeda s\\u1ed5 Smaart" if not self.demo'
            elif line.startswith('                            else '):
                line='                            else "QA: hai \\u0111\\u01b0\\u1eddng SUM \\u0111\\u00e3 v\\u1ebd tr\\u00ean \\u0111\\u1ed3 th\\u1ecb m\\u00f4 ph\\u1ecfng")'
            elif line.strip().startswith('self.status.setText(') and 'Ch' in line:
                line='            self.status.setText("Ch\\u01b0a c\\u00f3 c\\u1eb7p Trace \\u0111\\u01b0\\u1ee3c x\\u00e1c minh");return'
            elif line.strip().startswith('self.status.setText(') and 'Coherence' in line:
                line='            self.status.setText("Kh\\u00f4ng \\u0111\\u1ee7 Coherence trong v\\u00f9ng LF-HF");return'
            elif line.strip().startswith('self.status.setText(') and ('m' in line or 't' in line):
                line='        self.status.setText("\\u0110ang t\\u1ea3i c\\u1eb7p Trace m\\u1edbi...")'
    elif line.strip().startswith('else "QA:'):
        line='                            else "QA: hai \\u0111\\u01b0\\u1eddng SUM \\u0111\\u00e3 v\\u1ebd tr\\u00ean \\u0111\\u1ed3 th\\u1ecb m\\u00f4 ph\\u1ecfng")'
    elif line.strip()=='else:label.setText("�"")' or ('else:label.setText(' in line):
        line='            else:label.setText("-")'
    elif 'QA synthetic reference' in line:
        line='            p.setPen(QColor("#e0eaf5"));p.drawText(x+10,y+23,text+" - QA reference")'
    elif 'drawText(8,18,self.label)' in line:
        line=line.replace('drawText(8,18,self.label)','drawText(150,19,self.label)')
    out.append(line)
p.write_text("\n".join(out)+"\n",encoding="utf-8")
print("ASCII_TRANSLATION_PATCH",sum(any(ord(c)>127 for c in x) for x in out))
