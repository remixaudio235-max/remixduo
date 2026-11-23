"""Manual V8.75 read-only verification on existing user TRF files.

No generator/capture/measurement writes. This is an offline file check,
not Smaart API live TF or trusted Data Bar tick identification.
"""
from __future__ import annotations
import argparse
import json
from smaart_discovery_v875 import scan_traces
from trf_core import read_trf


def probe(edition: int, maximum: int = 3) -> dict:
    if not 1 <= maximum <= 10:
        raise ValueError("INVALID_PROBE_LIMIT")
    inv = scan_traces(edition, max_names=maximum)
    outcome = []
    for name in inv.filenames:
        path = inv.folder / name
        try:
            trace = read_trf(path)
            outcome.append({
                "status": "PARSE_PASS", "name": name,
                "bins": len(trace.hz), "format": trace.kind,
                "frequency_start_hz": round(float(trace.hz[0]), 3),
                "frequency_end_hz": round(float(trace.hz[-1]), 3),
            })
        except Exception as exc:
            outcome.append({"status": "PARSE_FAIL",
                            "name": name, "reason": type(exc).__name__})
    return {"edition": edition, "directory_exists": inv.available,
            "trf_files": inv.count, "sample_checks": outcome,
            "live_api_tf_verified": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--edition", type=int, choices=(8, 9), required=True)
    parser.add_argument("--max", type=int, default=3)
    a = parser.parse_args()
    print(json.dumps(probe(a.edition, a.max), ensure_ascii=False, indent=2))
