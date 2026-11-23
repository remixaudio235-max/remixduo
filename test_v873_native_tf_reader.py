"""V8.73 contract-only synthetic unit fixtures. NOT Smaart stream parity."""
from dataclasses import replace
import pytest

from smaart_live_tf_reader_v873 import (
    NativeTFReader, SDKBinding, TFPacket, UntrustedFrame
)


def bound(edition=8, *, verified=True, trace="trace-A", generation=1):
    return SDKBinding(
        edition, "v3" if edition == 8 else "v4",
        "engine-1", trace, generation, 48000,
        verified=verified, sdk_document_reference="UNIT_TEST_FIXTURE_ONLY"
    )


def frame(edition=8, **updates):
    raw = TFPacket(
        edition, "v3" if edition == 8 else "v4",
        "engine-1", "trace-A", 1, 1, 1_000_000,
        48000, (100., 1000., 10000.),
        (-3., 1., 0.), (0., 1., -1.),
        (0.95, 0.9, 0.8), 6.25,
        "NATIVE_SDK_STREAM"
    )
    return replace(raw, **updates)


@pytest.mark.parametrize("edition", [8, 9])
def test_version_isolation_and_verified_native_frame(edition):
    rd = NativeTFReader()
    rd.bind(bound(edition))
    assert rd.ingest(frame(edition), received_ns=100_000_000)
    assert rd.latest(edition, "engine-1", "trace-A", now_ns=100_000_010)
    assert not rd.solver_ready(edition, "engine-1", "trace-A")
    assert rd.latest(edition, "engine-1", "trace-A", now_ns=1_100_000_001) is None


def test_state_get_or_offline_trf_is_not_a_live_frame():
    rd = NativeTFReader()
    rd.bind(bound())
    assert not rd.ingest(frame(origin="API_GET_STATUS"))
    assert rd.last_rejection == "NOT_NATIVE_LIVE_STREAM"
    assert not rd.ingest(frame(origin="OFFLINE_TRF"))
    assert rd.latest(8, "engine-1", "trace-A") is None


def test_unverified_sdk_never_produces_a_frame():
    rd = NativeTFReader()
    rd.bind(bound(verified=False))
    assert not rd.ingest(frame())
    assert rd.last_rejection == "SDK_CONTRACT_NOT_VERIFIED"


@pytest.mark.parametrize("changes,error", [
    ({"engine_id": "other"}, "ENGINE_NOT_BOUND"),
    ({"trace_id": "other"}, "ENGINE_NOT_BOUND"),
    ({"sample_rate_hz": 44100}, "FS_MISMATCH"),
    ({"source_timestamp_ns": 0}, "MISSING_SOURCE_TIMESTAMP"),
    ({"frequency_hz": (100., 200., 200.)}, "NONMONOTONIC_FREQUENCY_GRID"),
    ({"frequency_hz": (100., 50000., 60000.)}, "FREQUENCY_OUTSIDE_NYQUIST"),
    ({"magnitude_db": (1., 2.)}, "MISALIGNED_TF_ARRAYS"),
    ({"phase_rad": (0., float("nan"), 0.)}, "NONFINITE_TF"),
    ({"coherence": (1.0, 1.5, 0.8)}, "COHERENCE_OUT_OF_RANGE"),
    ({"coherence": (1.0, 0.8)}, "INVALID_COHERENCE"),
    ({"generation": 2}, "GENERATION_MISMATCH"),
    ({"api": "v4"}, "API_EDITION_MISMATCH"),
])
def test_corrupt_and_foreign_packets_are_rejected(changes, error):
    rd = NativeTFReader()
    rd.bind(bound())
    assert not rd.ingest(frame(**changes)), changes
    assert rd.last_rejection == error


def test_sequence_timestamp_and_grid_are_monotonic():
    rd = NativeTFReader()
    rd.bind(bound())
    assert rd.ingest(frame(), received_ns=100)
    assert not rd.ingest(frame(), received_ns=200)
    assert rd.last_rejection == "STALE_OR_REORDERED_SEQUENCE"
    assert not rd.ingest(frame(sequence=2, source_timestamp_ns=999_999))
    assert rd.last_rejection == "STALE_SOURCE_TIMESTAMP"
    assert not rd.ingest(frame(sequence=2, source_timestamp_ns=1_000_001,
                               frequency_hz=(200., 1000., 10000.)))
    assert rd.last_rejection == "FREQUENCY_GRID_CHANGED_REBIND_REQUIRED"
    assert rd.ingest(frame(sequence=2, source_timestamp_ns=1_000_001))
    rd.bind(bound(generation=2))
    assert rd.latest(8, "engine-1", "trace-A") is None
    assert rd.ingest(frame(generation=2))


def test_max_four_traces_and_parity_is_never_self_certified():
    rd = NativeTFReader()
    for i in range(4):
        rd.bind(bound(trace=f"trace-{i}"))
    with pytest.raises(UntrustedFrame, match="MAX_FOUR_TF"):
        rd.bind(bound(trace="trace-4"))
    with pytest.raises(UntrustedFrame, match="INDEPENDENT_QA"):
        rd.mark_parity(8, "engine-1", "trace-0")
    assert not rd.solver_ready(8, "engine-1", "trace-0")


def test_coherence_and_delay_remain_missing_not_fabricated():
    rd = NativeTFReader()
    rd.bind(bound())
    assert rd.ingest(frame(coherence=None, delay_ms=None))
    obj = rd.latest(8, "engine-1", "trace-A")
    assert obj is not None
    assert obj.coherence is None and obj.delay_ms is None


def test_unbind_forgets_provenance():
    rd = NativeTFReader()
    rd.bind(bound())
    assert rd.ingest(frame())
    rd.unbind(8, "engine-1", "trace-A")
    assert rd.latest(8, "engine-1", "trace-A") is None
    assert not rd.ingest(frame())
    assert rd.last_rejection == "ENGINE_NOT_BOUND"


def test_sdk_worker_never_starts_implicitly_and_rejects_unverified_sdk():
    import time
    from smaart_live_tf_reader_v873 import NativeSDKWorker, NativeSDKStream

    class UnverifiedSDK(NativeSDKStream):
        receives = 0
        def connect_readonly(self):
            return bound(verified=False)
        def receive_tf(self, timeout_s):
            self.receives += 1
            return frame()

    sdk = UnverifiedSDK()
    worker = NativeSDKWorker(NativeTFReader(), sdk)
    assert worker._thread is None
    worker.start()
    worker._thread.join(timeout=1.0)
    assert not worker._thread.is_alive()
    assert worker.last_error == "SDK_CONTRACT_NOT_VERIFIED"
    assert sdk.receives == 0 and worker.frames_received == 0
    worker.stop()


def test_sdk_worker_ingests_native_fixture_without_gui_or_audio():
    from threading import Event
    from smaart_live_tf_reader_v873 import NativeSDKWorker, NativeSDKStream

    seen = Event()

    class NativeFixtureSDK(NativeSDKStream):
        def __init__(self):
            self.count = 0
        def connect_readonly(self):
            return bound()
        def receive_tf(self, timeout_s):
            self.count += 1
            if self.count == 1:
                seen.set()
                return frame()
            seen.wait(timeout_s)
            return None

    sdk = NativeFixtureSDK()
    reader = NativeTFReader()
    worker = NativeSDKWorker(reader, sdk)
    worker.start()
    assert seen.wait(1.0)
    # Worker may still be inside ingest after the notification.
    import time
    deadline = time.monotonic() + 1
    while worker.frames_received == 0 and time.monotonic() < deadline:
        time.sleep(0.005)
    assert worker.frames_received == 1
    assert not worker.last_error
    worker.stop()
    assert worker._thread is not None and not worker._thread.is_alive()
