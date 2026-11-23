from pathlib import Path
p=Path(r"D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7\full_scan_v7.py")
s=p.read_text("utf-8")
s=s.replace("    elapsed_s:float\n","    elapsed_s:float\n    states:tuple[str,...]=()\n")
s=s.replace('''    return Scanned(active,len(order),len(visited),pages,scroll_start,end,
                   time.perf_counter()-st)''','''    return Scanned(active,len(order),len(visited),pages,scroll_start,end,
                   time.perf_counter()-st,tuple(visited[i] for i in range(len(order))))''')
p.write_text(s,encoding="utf-8")
print("full_scan states exported")
