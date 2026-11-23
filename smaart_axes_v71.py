"""Read *saved* Smaart plot axes without modifying Smaart's configuration."""
from pathlib import Path
from xml.etree import ElementTree as ET
import math

def read_saved_axes(path=None):
    path=Path(path or Path.home()/"Documents/Smaart Suite/Config/SmaartConfig.xml")
    if not path.is_file():
        return None
    root=ET.parse(path).getroot()
    result={}
    for element in root.iter("plotProperties"):
        name=element.findtext("name")
        if name not in ("Phase1","Magnitude1"):
            continue
        if element.findtext("visible")!="1":
            continue
        value=element.findtext("ordinateRange") or ""
        parts=value.split(",")
        if len(parts)!=2: continue
        lo,hi=map(float,parts)
        if not (math.isfinite(lo) and math.isfinite(hi)
                and -500<=lo<hi<=500 and 1<hi-lo<500):
            continue
        key="phase" if name=="Phase1" else "mag"
        result[key]=(lo,hi)
    return result if "mag" in result and "phase" in result else None
