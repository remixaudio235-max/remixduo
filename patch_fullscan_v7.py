from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7\selection_v7.py")
s=p.read_text(encoding="utf-8")
old='''    if color<.18:return "unknown"
    if w<.03:return "on"'''
new='''    # Grayscale trace icons can have a white X but no saturated pixels.
    # Treat as OFF only with strong white-cross evidence; otherwise unknown,
    # never auto-classify a grayscale icon as ON.
    if color<.18 and w>.08:return "off"
    if color<.18:return "unknown"
    if w<.03:return "on"'''
assert old in s
p.write_text(s.replace(old,new),encoding="utf-8")
q=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7\full_scan_v7.py")
a=q.read_text(encoding="utf-8-sig")
old='''        if len(active)!=2:
            raise ScanError(f"Expected 2 active stored traces, observed {len(active)}")
'''
assert old in a
q.write_text(a.replace(old,'        # A complete scan can legitimately find zero, one or multiple ticks.\n        # The caller must fail closed unless exactly two are active.\n'),encoding="utf-8")
print("V7_GRAY_X_AND_ZERO_SELECTED_FULLSCAN_PATCH_PASS")
