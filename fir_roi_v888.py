"""Independent FIR working-band gesture policy (no DSP or Smaart I/O)."""
import math

MIN_HZ = 20
MAX_HZ = 20000
MIN_OCTAVES = 1.0


def clamp_fir_drag(kind, value, lf, hf):
    """Keep the selected endpoint within FIR's minimum one-octave band."""
    if kind not in ("LF", "HF"):
        raise ValueError("Unknown FIR ROI endpoint")
    numbers = (value, lf, hf)
    if any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in numbers):
        raise ValueError("Invalid FIR ROI frequency")
    lf, hf = float(lf), float(hf)
    if not (MIN_HZ <= lf < hf <= MAX_HZ and hf >= 2 * lf):
        raise ValueError("Invalid current FIR working band")
    value = max(MIN_HZ, min(MAX_HZ, float(value)))
    if kind == "LF":
        return round(max(MIN_HZ, min(value, hf / 2, 19000)))
    return round(min(MAX_HZ, max(value, lf * 2, 100)))
