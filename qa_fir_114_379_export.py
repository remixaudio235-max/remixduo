"""QA comparison FIR exports ONLY, never sent to Smaart, speakers or DSP."""
from pathlib import Path
import json,hashlib
import numpy as np
from trf_core import read_trf
from signal_tools_core_v813 import design_phase_only_fir,save_fir_txt,save_fir_wav_float
from remix_duo.core.fir_preview import phase_excess_rms
base=Path(__file__).resolve().parent
source=Path.home()/'Documents'/'Smaart Suite'/'Data'/'Transfer Function'/'Session Data'/'TUNNINNGGG-4.trf'
out=base/'_qa_outputs'/'fir_phase_114_379_20261103'
out.mkdir(parents=True,exist_ok=True)
trace=read_trf(source)
manifest=dict(status='QA_ONLY_NOT_APPROVED_FOR_HARDWARE_DSP',source=str(source),
    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    lf_hz=114,hf_hz=379,sampling_rate_hz=48000,
    coherence_gate=0.75,phase_quality='coherence-gated excess phase, fitted bulk delay removed',
    output_note='No realtime DSP write, no Smaart setting modification',
    designs=[])
for name,taps,plus in [('legacy1024',1024,False),('legacy4096',4096,False),('phaseplus4096',4096,True)]:
    result=design_phase_only_fir(trace.hz,trace.h,trace.coherence,taps=taps,
         fs=48000,lf=114,hf=379,source=source.stem,phase_plus=plus)
    b,a,improvement,n=phase_excess_rms(trace.hz,trace.h,trace.coherence,
                                       result.taps,result.fs,114,379)
    band=(result.hz>=20)&(result.hz<=20000)
    maxmag=float(np.max(np.abs(result.actual_db[band])))
    midpoint=taps//2
    pre=float(np.sum(result.taps[:midpoint-int(.005*48000)]**2)/np.sum(result.taps**2))
    root=out/f'QA_NOT_FOR_DSP_{name}_114-379Hz_48k_{taps}'
    txt=root.with_suffix('.txt');wav=root.with_suffix('.wav')
    save_fir_txt(txt,result);save_fir_wav_float(wav,result)
    manifest['designs'].append(dict(name=name,taps=taps,phase_plus=plus,
        delay_ms=result.latency_ms,excess_phase_rms_before_deg=b,
        excess_phase_rms_after_deg=a,improvement_percent=improvement,
        coherent_bins=n,max_20_20000_magnitude_error_db=maxmag,
        pre_main_5ms_energy_ratio=pre,files=[str(txt),str(wav)],
        txt_sha256=hashlib.sha256(txt.read_bytes()).hexdigest(),
        wav_sha256=hashlib.sha256(wav.read_bytes()).hexdigest()))
manifest_path=out/'fir114_379_comparison.json'
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print('QA_MANIFEST',manifest_path)
for item in manifest['designs']:
 print('QA_DESIGN',item['name'],'RMS',round(item['excess_phase_rms_after_deg'],3),
       'IMPROVEMENT',round(item['improvement_percent'],2),
       'MAX_MAG',round(item['max_20_20000_magnitude_error_db'],3),
       'LATENCY',round(item['delay_ms'],3))
