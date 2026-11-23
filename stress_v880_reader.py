"""Bounded synthetic reader benchmark. No network, GUI or audio operations."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import statistics
import time
import tracemalloc
from smaart_live_tf_reader_v873 import NativeTFReader, SDKBinding, TFPacket


def run():
    results = []
    for bins, traces, seconds in [(1024, 1, 3), (4096, 4, 8), (32768, 4, 8)]:
        reader = NativeTFReader(ttl_ms=1000)
        frequency = tuple(i * 24000 / (bins - 1) for i in range(bins))
        zeros = (0.,) * bins
        for trace in range(traces):
            reader.bind(SDKBinding(8, 'v3', 'SYNTHETIC', str(trace), 1, 48000,
                                   True, 'SYNTHETIC BENCHMARK ONLY'))
        deadline = time.monotonic() + seconds
        def producer(trace):
            latencies = []
            sequence = 0
            rejected = 0
            while time.monotonic() < deadline:
                sequence += 1
                p = TFPacket(8, 'v3', 'SYNTHETIC', str(trace), 1, sequence,
                             sequence, 48000, frequency, zeros, zeros,
                             origin='NATIVE_SDK_STREAM')
                start = time.perf_counter_ns()
                accepted = reader.ingest(p)
                rejected += not accepted
                reader.latest(8, 'SYNTHETIC', str(trace))
                elapsed = (time.perf_counter_ns() - start) / 1e6
                # Bounded measurement history, no benchmark-induced memory leak.
                if len(latencies) < 10000: latencies.append(elapsed)
            return sequence, rejected, latencies
        start = time.monotonic()
        cpu_start = time.process_time()
        with ThreadPoolExecutor(max_workers=traces) as pool:
            rows = list(pool.map(producer, range(traces)))
        elapsed = time.monotonic() - start
        lat = sorted(v for row in rows for v in row[2])
        latest = reader.latest(8, 'SYNTHETIC', '0')
        stale_hidden = reader.latest(8, 'SYNTHETIC', '0',
                                     now_ns=latest.receive_monotonic_ns + 1000000001) is None
        assert stale_hidden and len(reader._latest) <= traces
        assert sum(row[1] for row in rows) == 0
        results.append(dict(bins=bins, traces=traces, seconds=round(elapsed, 3),
            frames=sum(row[0] for row in rows), rejected=sum(row[1] for row in rows),
            fps=round(sum(row[0] for row in rows)/elapsed, 1),
            p50_ms=round(statistics.median(lat), 3),
            p95_ms=round(lat[int((len(lat)-1)*.95)], 3),
            p99_ms=round(lat[int((len(lat)-1)*.99)], 3),
            max_ms=round(max(lat), 3), cpu_seconds=round(time.process_time()-cpu_start, 3),
            cached_frames=len(reader._latest), stale_hidden=stale_hidden))
    # Separate retained-allocation check; tracing overhead excluded above.
    tracemalloc.start()
    reader = NativeTFReader()
    reader.bind(SDKBinding(8,'v3','MEM','0',1,48000,True,'SYNTHETIC'))
    p = TFPacket(8,'v3','MEM','0',1,1,1,48000,(100.,1000.),(0.,0.),(0.,0.),
                 origin='NATIVE_SDK_STREAM')
    for i in range(1, 50001): reader.ingest(replace(p,sequence=i,source_timestamp_ns=i))
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert len(reader._latest) == 1 and current < 1000000
    print(json.dumps(dict(scope='SYNTHETIC READER ONLY, NOT LIVE SMAART',
        profiles=results, memory_50000_frames=dict(retained_bytes=current,
        peak_bytes=peak,cached_frames=len(reader._latest))), indent=2))


if __name__ == '__main__': run()
