"""V8.72 — Portable FIR coefficient exports, profile list from RemiX Tune R23.

A named profile is an interchange-format hint, NOT vendor-specific file
certification. Confirm model-specific sample rate, tap limit, FIR availability,
endianness and importer with the DSP manual before loading hardware.
"""
from __future__ import annotations
from pathlib import Path
import json,struct
import numpy as np
from xml.etree import ElementTree as ET

PROFILES=({'name': 'Generic TXT', 'format': 'txt', 'extension': '.txt', 'max_taps': None, 'description': 'Plain one-coefficient-per-line float text.'}, {'name': 'Generic CSV', 'format': 'csv', 'extension': '.csv', 'max_taps': None, 'description': 'Comma-separated coefficient list.'}, {'name': 'Generic JSON', 'format': 'json', 'extension': '.json', 'max_taps': None, 'description': 'RemiX metadata plus coefficient payload.'}, {'name': 'Generic XML', 'format': 'xml', 'extension': '.xml', 'max_taps': None, 'description': 'XML coefficient payload for DSP/API workflows.'}, {'name': 'Generic WAV Float32', 'format': 'wav', 'extension': '.wav', 'max_taps': None, 'description': 'Mono 32-bit float WAV impulse response.'}, {'name': 'Generic BIN Float32', 'format': 'bin', 'extension': '.bin', 'max_taps': None, 'description': 'Raw little-endian float32 coefficients.'}, {'name': 'miniDSP TXT', 'format': 'txt', 'extension': '.txt', 'max_taps': None, 'description': 'miniDSP normalized coefficient text.'}, {'name': 'miniDSP WAV Float32', 'format': 'wav', 'extension': '.wav', 'max_taps': None, 'description': 'miniDSP mono float WAV impulse.'}, {'name': 'miniDSP BIN Float32', 'format': 'bin', 'extension': '.bin', 'max_taps': None, 'description': 'miniDSP raw float32 coefficient payload.'}, {'name': 'Powersoft X/T Series TXT', 'format': 'txt', 'extension': '.txt', 'max_taps': None, 'description': 'Coefficient text for Powersoft FIR workflows.'}, {'name': 'Xilica Neutrino/Solaro TXT', 'format': 'txt', 'extension': '.txt', 'max_taps': None, 'description': 'Coefficient text for Xilica FIR workflows.'}, {'name': 'Linea Research TXT', 'format': 'txt', 'extension': '.txt', 'max_taps': None, 'description': 'Coefficient text for Linea Research FIR workflows.'}, {'name': 'MARANI DPA/DSP 1024', 'format': 'txt', 'extension': '.txt', 'max_taps': 1024, 'description': 'Text export capped at 1024 taps.'}, {'name': 'DBX DriveRack 1024', 'format': 'txt', 'extension': '.txt', 'max_taps': 1024, 'description': 'Text export capped at 1024 taps.'}, {'name': 'RCF DX Series 1024', 'format': 'txt', 'extension': '.txt', 'max_taps': 1024, 'description': 'Text export capped at 1024 taps.'}, {'name': 'Dynacord DSP 1024', 'format': 'txt', 'extension': '.txt', 'max_taps': 1024, 'description': 'Text export capped at 1024 taps.'}, {'name': 'Bose ControlSpace 512', 'format': 'txt', 'extension': '.txt', 'max_taps': 512, 'description': 'Text export capped at 512 taps.'}, {'name': 'BSS Soundweb London 1024', 'format': 'txt', 'extension': '.txt', 'max_taps': 1024, 'description': 'Text export capped at 1024 taps.'}, {'name': 'FANE DSP TXT', 'format': 'txt', 'extension': '.txt', 'max_taps': None, 'description': 'Generic coefficient text for FANE DSP workflows.'}, {'name': 'Alto/EuroLive DSP 512', 'format': 'txt', 'extension': '.txt', 'max_taps': 512, 'description': 'Text export capped at 512 taps.'}, {'name': 'DSP Trung Quốc phổ thông 512', 'format': 'txt', 'extension': '.txt', 'max_taps': 512, 'description': 'Generic text export capped at 512 taps.'}, {'name': 'QSC Q-Sys Core110f 512', 'format': 'txt', 'extension': '.txt', 'max_taps': 512, 'description': 'Text export capped at 512 taps.'}, {'name': 'CamillaDSP WAV Float32', 'format': 'wav', 'extension': '.wav', 'max_taps': None, 'description': 'Mono Float32 impulse response for CamillaDSP convolution.'}, {'name': 'CamillaDSP TXT', 'format': 'txt', 'extension': '.txt', 'max_taps': None, 'description': 'Plain FIR coefficient text for CamillaDSP workflows.'}, {'name': 'BruteFIR TXT', 'format': 'txt', 'extension': '.txt', 'max_taps': None, 'description': 'Plain FIR coefficient text for BruteFIR.'}, {'name': 'Equalizer APO Convolution WAV', 'format': 'wav', 'extension': '.wav', 'max_taps': None, 'description': 'Mono Float32 WAV impulse for convolution workflows.'}, {'name': 'JRiver Convolution WAV', 'format': 'wav', 'extension': '.wav', 'max_taps': None, 'description': 'Mono Float32 WAV impulse for JRiver convolution.'}, {'name': 'Roon Convolution WAV', 'format': 'wav', 'extension': '.wav', 'max_taps': None, 'description': 'Mono Float32 WAV impulse for Roon convolution filters.'}, {'name': 'foobar2000 Convolver WAV', 'format': 'wav', 'extension': '.wav', 'max_taps': None, 'description': 'Mono Float32 WAV impulse for convolver components.'}, {'name': 'rePhase WAV Float32', 'format': 'wav', 'extension': '.wav', 'max_taps': None, 'description': 'Float32 WAV impulse for rePhase-compatible workflows.'}, {'name': 'Audiolense WAV Float32', 'format': 'wav', 'extension': '.wav', 'max_taps': None, 'description': 'Float32 WAV impulse for convolution playback engines.'}, {'name': 'Acourate WAV Float32', 'format': 'wav', 'extension': '.wav', 'max_taps': None, 'description': 'Float32 WAV impulse for Acourate-style convolution workflows.'}, {'name': 'Hang Loose Convolver WAV', 'format': 'wav', 'extension': '.wav', 'max_taps': None, 'description': 'Mono Float32 WAV impulse for HLC workflows.'}, {'name': 'OpenDRC TXT', 'format': 'txt', 'extension': '.txt', 'max_taps': None, 'description': 'Plain FIR coefficient text for OpenDRC-style workflows.'}, {'name': 'Generic FIR Engine Float32 BIN', 'format': 'bin', 'extension': '.bin', 'max_taps': None, 'description': 'Raw little-endian Float32 FIR coefficient payload.'}, {'name': 'Generic FIR API JSON', 'format': 'json', 'extension': '.json', 'max_taps': None, 'description': 'RemiX FIR metadata plus coefficient array for API integration.'}, {'name': 'Generic FIR API XML', 'format': 'xml', 'extension': '.xml', 'max_taps': None, 'description': 'XML FIR coefficient payload for API integration.'})


GENERIC_KEYS=frozenset(("Generic TXT","Generic CSV","Generic JSON",
    "Generic XML","Generic WAV Float32","Generic BIN Float32"))
def validate(result,profile):
    values=np.asarray(result.taps,dtype=np.float64).reshape(-1)
    errors=[]
    if not len(values) or not np.isfinite(values).all():errors.append("Invalid FIR coefficients")
    if len(values)>0 and np.max(np.abs(values))>32:errors.append("Coefficient amplitude unsafe")
    if not isinstance(result.fs,(int,np.integer)) or result.fs<8000 or result.fs>384000:
        errors.append("Invalid sample rate")
    if profile.get("max_taps") is not None and len(values)>int(profile["max_taps"]):
        errors.append("Tap count exceeds selected profile limit (no silent truncation)")
    if profile["format"] not in ("txt","csv","json","xml","wav","bin"):
        errors.append("Unsupported export format")
    return errors

def get_profile(name):
    for profile in PROFILES:
        if profile["name"]==name:return dict(profile)
    raise ValueError("Unknown DSP export profile")

def write_export(result,profile_name,dest):
    profile=get_profile(profile_name)
    errors=validate(result,profile)
    if errors:raise ValueError("; ".join(errors))
    path=Path(dest)
    if path.suffix.lower()!=profile["extension"].lower():
        raise ValueError("Export extension must match profile")
    if not path.parent.is_dir():raise ValueError("Destination directory unavailable")
    vals=np.asarray(result.taps,dtype=np.float32).reshape(-1)
    fmt=profile["format"]
    # Atomic output: do not leave an apparently valid partial DSP file.
    staging=path.with_name(path.name+".part")
    if staging.exists():raise FileExistsError("Staging export already exists")
    try:
        if fmt=="txt":
            staging.write_text("\n".join(f"{float(v):.10g}" for v in vals)+"\n",encoding="utf-8")
        elif fmt=="csv":
            staging.write_text("\n".join(f"{float(v):.10g}" for v in vals)+"\n",encoding="utf-8")
        elif fmt=="bin":
            staging.write_bytes(vals.astype("<f4",copy=False).tobytes())
        elif fmt=="wav":
            payload=vals.astype("<f4",copy=False).tobytes()
            fmtchunk=struct.pack("<HHIIHH",3,1,int(result.fs),int(result.fs)*4,4,32)
            chunks=b"fmt "+struct.pack("<I",len(fmtchunk))+fmtchunk
            chunks+=b"data"+struct.pack("<I",len(payload))+payload
            staging.write_bytes(b"RIFF"+struct.pack("<I",4+len(chunks))+b"WAVE"+chunks)
        elif fmt=="json":
            staging.write_text(json.dumps({"generator":"RemiX Duo V8.72",
                "profile":profile["name"],"sample_rate":int(result.fs),
                "taps":len(vals),"coefficients":[float(v) for v in vals]},
                ensure_ascii=False,indent=2),encoding="utf-8")
        elif fmt=="xml":
            root=ET.Element("FIR",profile=profile["name"],
                 sample_rate=str(result.fs),taps=str(len(vals)))
            for i,val in enumerate(vals):
                ET.SubElement(root,"Coeff",index=str(i)).text=f"{float(val):.10g}"
            ET.ElementTree(root).write(staging,encoding="utf-8",xml_declaration=True)
        staging.replace(path)
    except BaseException:
        try:staging.unlink(missing_ok=True)
        except OSError:pass
        raise
    return {"path":str(path),"profile":profile["name"],"format":fmt,
            "taps":len(vals),"fs":int(result.fs),
            "device_native_verified":False}
