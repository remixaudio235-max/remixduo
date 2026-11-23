from pathlib import Path
import shutil
root=Path(r'D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v7_5_ASCII_IMPORT_QA')
p=root/'selection_v7.py'
s=p.read_text(encoding='utf-8')
a=s.index('def archive_order(')
b=s.index('\ndef scan_icon_white_cross(',a)
patch='''def archive_order(folder:Path)->list[Path]:
    """Map Smaart 9.6.4 Data Bar files by index IDs plus verified new imports.

    Smaart may show newly imported ASCII TFs immediately as .trf at the TOP
    of Data Bar, *before* index.xml is saved. The old indexed order stays
    beneath newly imported entries; latest imported .trf appears first.
    This fallback is intentionally strict:
      - existing indexed paths must match a contiguous 0-based list;
      - all missing paths must be *newer* than the index.xml timestamp;
      - no duplicate names or tied import timestamps;
      - UIA row count is additionally checked by LiveDataBar/FullScan.
    It does NOT edit Smaart files or invent missing TF data.
    """
    from xml.etree import ElementTree as ET
    folder=Path(folder)
    all_paths=list(folder.glob("*.trf"))
    all_files={p.name.casefold():p for p in all_paths}
    if len(all_files)!=len(all_paths):
        raise ValueError("Ambiguous case-insensitive .trf filenames")
    index=folder.parent/"index.xml"
    if not index.is_file():
        raise ValueError("Smaart index.xml missing; mapping unverified")
    try:
        root=ET.parse(index).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"Smaart index.xml parse failed: {exc}") from exc
    ids={}
    indexed=set()
    for element in root.findall(".//path"):
        name=str(element.text or "").strip()
        if not name.lower().endswith(".trf"):
            continue
        key=Path(name).name.casefold()
        if key not in all_files:
            raise ValueError(f"Smaart index references missing TRF: {name}")
        try:
            ix=int(element.attrib["adhocIndex"])
        except (ValueError,KeyError) as exc:
            raise ValueError("Smaart index has invalid row ID") from exc
        if ix in ids or key in indexed:
            raise ValueError("Duplicate row/Trace in Smaart index")
        indexed.add(key)
        ids[ix]=all_files[key]
    if not ids or sorted(ids)!=list(range(len(ids))):
        raise ValueError("Smaart indexed row IDs incomplete/noncontiguous")
    missing=[p for k,p in all_files.items() if k not in indexed]
    if not missing:
        if len(ids)!=len(all_files):
            raise ValueError("Smaart index cardinality inconsistent")
        return [ids[i] for i in range(len(ids))]
    if len(missing)>16:
        raise ValueError(f"Too many unindexed imports: {len(missing)}")
    # Only accept fresh imports, never silently remap old or renamed traces.
    index_stamp=index.stat().st_mtime_ns
    if any(p.stat().st_mtime_ns <= index_stamp+1_000_000_000 for p in missing):
        raise ValueError("Unindexed .trf older than Smaart index; ambiguous order")
    times=[p.stat().st_mtime_ns for p in missing]
    if len(times)!=len(set(times)):
        raise ValueError("Imported .trf timestamps tied; ambiguous order")
    imported=sorted(missing,key=lambda p:p.stat().st_mtime_ns,reverse=True)
    # Note: recovered order MUST be corroborated against live Data Bar.
    return imported+[ids[i] for i in range(len(ids))]

def fresh_unindexed_imports(folder:Path)->tuple[Path,...]:
    """Metadata only; a visible GUI should label this provisional mapping."""
    from xml.etree import ElementTree as ET
    folder=Path(folder)
    index=folder.parent/"index.xml"
    if not index.is_file():
        return ()
    listed={Path(str(q.text)).name.casefold()
            for q in ET.parse(index).getroot().findall(".//path")
            if str(q.text).lower().endswith(".trf")}
    return tuple(p for p in folder.glob("*.trf") if p.name.casefold() not in listed)
'''
s=s[:a]+patch+s[b:]
p.write_text(s,encoding='utf-8')
print('V75_INDEX_ASCII_FALLBACK_PATCH_OK')
