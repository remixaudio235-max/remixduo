"""Read-only R65 native SUM latency observer.

This probe never focuses a host, changes display settings, or clicks a trace.
The operator performs the controlled action separately.  We sample the current
desktop and the product telemetry continuously so a 3/7-second checkpoint is
never misreported as first-paint latency.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import ImageGrab
import win32gui

from plot_role_v812 import locate_role_plots


READY_RE = re.compile(
    rb"V8180_STATIC_MAG_NATIVE_READY_MS\s+([0-9]+(?:\.[0-9]+)?)"
)


@dataclass(frozen=True)
class LatencyEvidence:
    status: str
    hwnd: int
    title: str
    started_perf_counter: float
    sample_interval_ms: float
    first_visual_ms: float | None
    telemetry_ms: float | None
    samples: int
    mag_green_pixels: int
    phase_green_pixels: int
    reason: str


def parse_latest_ready_ms(payload: bytes) -> float | None:
    """Return the latest complete millisecond marker from a log suffix."""
    matches = READY_RE.findall(payload)
    return float(matches[-1]) if matches else None


def count_green(image: np.ndarray, rect: tuple[int, int, int, int]) -> int:
    """Count the established high-contrast SUM green pixels in a plot."""
    x, y, width, height = map(int, rect)
    crop = image[max(0, y):max(0, y + height), max(0, x):max(0, x + width)]
    if crop.size == 0:
        return 0
    red = crop[:, :, 0].astype(np.int16)
    green = crop[:, :, 1].astype(np.int16)
    blue = crop[:, :, 2].astype(np.int16)
    mask = ((green > 150) & (green > red * 1.35) &
            (green > blue * 1.5) & (red < 155) & (blue < 155))
    return int(mask.sum())


def observe(hwnd: int, log_path: Path, timeout_s: float = 8.0,
            sample_interval_s: float = 0.05) -> LatencyEvidence:
    """Observe an already-visible host without changing any external state."""
    if not win32gui.IsWindow(hwnd):
        raise ValueError(f"invalid HWND: {hwnd}")
    title = win32gui.GetWindowText(hwnd)
    layout = locate_role_plots(hwnd)
    if layout is None:
        return LatencyEvidence(
            "HOLD", hwnd, title, time.perf_counter(), sample_interval_s * 1000,
            None, None, 0, 0, 0, "native Phase/Mag roles not verified")

    start_offset = log_path.stat().st_size if log_path.is_file() else 0
    started = time.perf_counter()
    deadline = started + timeout_s
    first_visual_ms = None
    telemetry_ms = None
    samples = mag_green = phase_green = 0

    while time.perf_counter() < deadline:
        image = np.asarray(ImageGrab.grab().convert("RGB"))
        samples += 1
        mag_green = count_green(image, layout.mag)
        phase_green = count_green(image, layout.phase)
        now = time.perf_counter()
        if first_visual_ms is None and mag_green > 200 and phase_green > 250:
            first_visual_ms = (now - started) * 1000.0
        if log_path.is_file():
            with log_path.open("rb") as stream:
                stream.seek(start_offset)
                telemetry_ms = parse_latest_ready_ms(stream.read())
        if first_visual_ms is not None and telemetry_ms is not None:
            break
        time.sleep(sample_interval_s)

    status = "PASS" if first_visual_ms is not None else "HOLD"
    reason = ("continuous native visual proof observed" if status == "PASS"
              else "no verified SUM Phase/Mag visual proof before timeout")
    return LatencyEvidence(
        status, hwnd, title, started, sample_interval_s * 1000,
        first_visual_ms, telemetry_ms, samples, mag_green, phase_green, reason)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hwnd", required=True, type=int)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--interval-ms", type=float, default=50.0)
    args = parser.parse_args()
    evidence = observe(
        args.hwnd, args.log, args.timeout, max(0.02, args.interval_ms / 1000.0))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(asdict(evidence), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(asdict(evidence), ensure_ascii=False), flush=True)
    return 0 if evidence.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
