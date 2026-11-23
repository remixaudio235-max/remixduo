"""V8.73 Smaart native TF receiving boundary (passive, fail-closed).

No guessed JSON/WebSocket subscription commands.  A VERSION-SPECIFIC,
OFFICIALLY-VERIFIED SDK adapter must call ingest() with genuine API frames.
This module NEVER controls Smaart, opens sound devices, or draws the GUI.
A GET response, imported .trf, screenshot or synthetic frame is NOT live TF.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
import threading
import time
from typing import Literal

Edition = Literal[8, 9]
API = Literal["v3", "v4"]


class UntrustedFrame(ValueError):
    """Insufficient evidence to publish a measurement as native live TF."""


@dataclass(frozen=True)
class TFPacket:
    # All fields must come from the actual documented SDK stream, not UI/OCR.
    edition: Edition
    api: API
    engine_id: str
    trace_id: str
    generation: int
    sequence: int
    source_timestamp_ns: int
    sample_rate_hz: float
    frequency_hz: tuple[float, ...]
    magnitude_db: tuple[float, ...]
    phase_rad: tuple[float, ...]
    coherence: tuple[float, ...] | None = None
    delay_ms: float | None = None
    origin: str = "UNVERIFIED"
    receive_monotonic_ns: int = 0


@dataclass(frozen=True)
class SDKBinding:
    """The identity and authority attested by a versioned SDK connector.

    A connector MUST NOT assert verified=True until its subscription, frame
    layout and engine/trace IDs are independently checked against official SDK.
    """
    edition: Edition
    api: API
    engine_id: str
    trace_id: str
    generation: int
    sample_rate_hz: float
    verified: bool = False
    sdk_document_reference: str = ""


def _finite(values: tuple[float, ...]) -> bool:
    # bool is an int subclass in Python, but a JSON/native protocol boolean is
    # never a valid TF scalar.
    return all(type(x) in (float, int) and math.isfinite(x) for x in values)


def validate_frame(packet: TFPacket, binding: SDKBinding) -> None:
    if not binding.verified or not binding.sdk_document_reference.strip():
        raise UntrustedFrame("SDK_CONTRACT_NOT_VERIFIED")
    if (packet.edition, packet.api) != (binding.edition, binding.api):
        raise UntrustedFrame("API_EDITION_MISMATCH")
    if (packet.edition, packet.api) not in ((8, "v3"), (9, "v4")):
        raise UntrustedFrame("UNSUPPORTED_API_EDITION")
    if packet.origin != "NATIVE_SDK_STREAM":
        raise UntrustedFrame("NOT_NATIVE_LIVE_STREAM")
    if not packet.engine_id or not packet.trace_id:
        raise UntrustedFrame("MISSING_SOURCE_ID")
    if (packet.engine_id, packet.trace_id) != (binding.engine_id, binding.trace_id):
        raise UntrustedFrame("FOREIGN_ENGINE_OR_TRACE")
    if (type(packet.generation) is not int or
            packet.generation != binding.generation or packet.generation < 1):
        raise UntrustedFrame("GENERATION_MISMATCH")
    if type(packet.sequence) is not int or packet.sequence < 0:
        raise UntrustedFrame("INVALID_SEQUENCE")
    if type(packet.source_timestamp_ns) is not int or packet.source_timestamp_ns <= 0:
        raise UntrustedFrame("MISSING_SOURCE_TIMESTAMP")
    fs = packet.sample_rate_hz
    if type(fs) not in (float, int) or not math.isfinite(fs):
        raise UntrustedFrame("INVALID_FS")
    if fs < 8000 or fs > 384000 or fs != binding.sample_rate_hz:
        raise UntrustedFrame("FS_MISMATCH")
    if (not isinstance(packet.frequency_hz, tuple) or
            not isinstance(packet.magnitude_db, tuple) or
            not isinstance(packet.phase_rad, tuple) or
            (packet.coherence is not None and
             not isinstance(packet.coherence, tuple))):
        raise UntrustedFrame("INVALID_TF_ARRAY_TYPE")
    n = len(packet.frequency_hz)
    if not 2 <= n <= 131073:
        raise UntrustedFrame("INVALID_BIN_COUNT")
    if len(packet.magnitude_db) != n or len(packet.phase_rad) != n:
        raise UntrustedFrame("MISALIGNED_TF_ARRAYS")
    if not all(_finite(v) for v in
               (packet.frequency_hz, packet.magnitude_db, packet.phase_rad)):
        raise UntrustedFrame("NONFINITE_TF")
    if packet.frequency_hz[0] < 0 or packet.frequency_hz[-1] > fs / 2 + 1e-5:
        raise UntrustedFrame("FREQUENCY_OUTSIDE_NYQUIST")
    if any(b <= a for a, b in zip(packet.frequency_hz, packet.frequency_hz[1:])):
        raise UntrustedFrame("NONMONOTONIC_FREQUENCY_GRID")
    if packet.coherence is not None:
        if len(packet.coherence) != n or not _finite(packet.coherence):
            raise UntrustedFrame("INVALID_COHERENCE")
        if any(c < 0 or c > 1 for c in packet.coherence):
            raise UntrustedFrame("COHERENCE_OUT_OF_RANGE")
    if packet.delay_ms is not None and (
        type(packet.delay_ms) not in (float, int) or
        not math.isfinite(packet.delay_ms)
    ):
        raise UntrustedFrame("INVALID_DELAY")


class NativeTFReader:
    """Thread-safe bounded latest-frame inbox; no network or audio side effects.

    The SDK layer is responsible for version-specific WebSocket authentication,
    subscription and binary/text frame decoding. It invokes ingest() only after
    real stream provenance is proved. Bounded to a maximum of four TF identities.
    """
    def __init__(self, *, max_traces: int = 4, ttl_ms: int = 1000):
        if (type(max_traces) is not int or type(ttl_ms) is not int or
                max_traces < 1 or max_traces > 4 or ttl_ms <= 0):
            raise ValueError("Invalid reader bounds")
        self.max_traces = max_traces
        self.ttl_ns = ttl_ms * 1_000_000
        self._lock = threading.RLock()
        self._bindings: dict[tuple[int, str, str], SDKBinding] = {}
        self._latest: dict[tuple[int, str, str], TFPacket] = {}
        self._grids: dict[tuple[int, str, str], tuple[float, ...]] = {}
        self._last_seq: dict[tuple[int, str, str], int] = {}
        self._last_source_ns: dict[tuple[int, str, str], int] = {}
        self._parity_verified: set[tuple[int, str, str]] = set()
        self.last_rejection: str = "NO_SDK_FRAME"
        self._binding_revision = 0

    @staticmethod
    def _key(edition: int, engine_id: str, trace_id: str):
        return (edition, engine_id, trace_id)

    def bind(self, identity: SDKBinding) -> None:
        if type(identity.verified) is not bool:
            raise UntrustedFrame("INVALID_VERIFICATION_FLAG")
        if not isinstance(identity.sdk_document_reference, str):
            raise UntrustedFrame("INVALID_SDK_DOCUMENT_REFERENCE")
        if (not isinstance(identity.engine_id, str) or
                not isinstance(identity.trace_id, str) or
                not identity.engine_id.strip() or not identity.trace_id.strip()):
            raise UntrustedFrame("INVALID_SOURCE_ID")
        if (identity.edition, identity.api) not in ((8, "v3"), (9, "v4")):
            raise UntrustedFrame("UNSUPPORTED_API_EDITION")
        if type(identity.generation) is not int or identity.generation < 1:
            raise UntrustedFrame("INVALID_GENERATION")
        fs = identity.sample_rate_hz
        if (type(fs) not in (float, int) or not math.isfinite(fs) or
                fs < 8000 or fs > 384000):
            raise UntrustedFrame("INVALID_FS")
        key = self._key(identity.edition, identity.engine_id, identity.trace_id)
        with self._lock:
            if key not in self._bindings and len(self._bindings) >= self.max_traces:
                raise UntrustedFrame("MAX_FOUR_TF")
            if self._bindings.get(key) != identity:
                self._latest.pop(key, None)
                self._grids.pop(key, None)
                self._last_seq.pop(key, None)
                self._last_source_ns.pop(key, None)
                self._parity_verified.discard(key)
            self._bindings[key] = identity
            self._binding_revision += 1

    def ingest(self, packet: TFPacket, *, received_ns: int | None = None) -> bool:
        now = time.monotonic_ns() if received_ns is None else received_ns
        try:
                if not isinstance(packet, TFPacket):
                    raise UntrustedFrame("INVALID_PACKET")
                if type(packet.edition) is not int or type(packet.api) is not str:
                    raise UntrustedFrame("INVALID_API_IDENTITY")
                if (not isinstance(packet.engine_id, str) or
                        not isinstance(packet.trace_id, str) or
                        not packet.engine_id.strip() or not packet.trace_id.strip()):
                    raise UntrustedFrame("INVALID_SOURCE_ID")
                key = self._key(packet.edition, packet.engine_id, packet.trace_id)
                with self._lock:
                    binding = self._bindings.get(key)
                    revision = self._binding_revision
                if binding is None:
                    raise UntrustedFrame("ENGINE_NOT_BOUND")
                validate_frame(packet, binding)
                return self._commit_frame(packet, binding, revision, key, now)
        except UntrustedFrame as exc:
            with self._lock:
                self.last_rejection = str(exc)
            return False

    def _commit_frame(self, packet, binding, revision, key, now):
        with self._lock:
            try:
                if revision != self._binding_revision or self._bindings.get(key) is not binding:
                    raise UntrustedFrame("BINDING_CHANGED_DURING_VALIDATION")
                previous_seq = self._last_seq.get(key)
                previous_ts = self._last_source_ns.get(key)
                if previous_seq is not None and packet.sequence <= previous_seq:
                    raise UntrustedFrame("STALE_OR_REORDERED_SEQUENCE")
                if previous_ts is not None and packet.source_timestamp_ns <= previous_ts:
                    raise UntrustedFrame("STALE_SOURCE_TIMESTAMP")
                grid = self._grids.get(key)
                if grid is not None and grid != packet.frequency_hz:
                    raise UntrustedFrame("FREQUENCY_GRID_CHANGED_REBIND_REQUIRED")
                self._latest[key] = replace(packet, receive_monotonic_ns=now)
                self._grids[key] = packet.frequency_hz
                self._last_seq[key] = packet.sequence
                self._last_source_ns[key] = packet.source_timestamp_ns
                self.last_rejection = ""
                return True
            except UntrustedFrame as exc:
                self.last_rejection = str(exc)
                return False

    def latest(self, edition: Edition, engine_id: str, trace_id: str,
               *, now_ns: int | None = None) -> TFPacket | None:
        key = self._key(edition, engine_id, trace_id)
        now = time.monotonic_ns() if now_ns is None else now_ns
        with self._lock:
            packet = self._latest.get(key)
            if packet is None or now < packet.receive_monotonic_ns:
                return None
            if now - packet.receive_monotonic_ns > self.ttl_ns:
                return None
            return packet

    def mark_parity(self, *_args, **_kwargs) -> None:
        """Not self-certifiable: explicit independent live QA is required."""
        raise UntrustedFrame("LIVE_SMAART_PARITY_REQUIRES_INDEPENDENT_QA")

    def solver_ready(self, edition: Edition, engine_id: str, trace_id: str) -> bool:
        """No Auto Phase / Auto EQ / Auto FIR activation before live A/B QA."""
        return False

    def unbind(self, edition: Edition, engine_id: str, trace_id: str) -> None:
        key = self._key(edition, engine_id, trace_id)
        with self._lock:
            self._binding_revision += 1
            self._bindings.pop(key, None)
            self._latest.pop(key, None)
            self._grids.pop(key, None)
            self._last_seq.pop(key, None)
            self._last_source_ns.pop(key, None)
            self._parity_verified.discard(key)


class NativeSDKStream:
    """Interface implemented ONLY after official SDK handshake is understood.

    connect_readonly returns a newly attested generation/identity; receive_tf
    returns real decoded SDK packets. There are intentionally no GET/SET,
    generator, capture, DSP, audio I/O, or guessed API subscription methods.
    """
    def connect_readonly(self) -> SDKBinding:
        raise NotImplementedError("OFFICIAL_SMAART_SDK_REQUIRED")

    def receive_tf(self, timeout_s: float) -> TFPacket | None:
        raise NotImplementedError("OFFICIAL_SMAART_SDK_REQUIRED")

    def close(self) -> None:
        pass


class NativeSDKWorker:
    """Opt-in stream worker with bounded latest-wins delivery and reconnect.

    Never instantiated by the V8.72 GUI; starts ONLY on an explicit start().
    A reconnect MUST yield an increased connection generation from the SDK.
    """
    def __init__(self, reader: NativeTFReader, sdk: NativeSDKStream):
        self.reader = reader
        self.sdk = sdk
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_error = "SDK_NOT_CONNECTED"
        self.reconnect_count = 0
        self.frames_received = 0

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("SDK_WORKER_ALREADY_RUNNING")
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="RemiXDuo-V873-ReadOnlyTF", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        try:
            self.sdk.close()
        except Exception:
            pass
        if self._thread is not None:
            self._thread.join(timeout=1.5)

    def _run(self) -> None:
        last_generation = 0
        retry_s = 0.25
        while not self._stop.is_set():
            binding = None
            try:
                binding = self.sdk.connect_readonly()
                if not isinstance(binding, SDKBinding) or not binding.verified:
                    raise UntrustedFrame("SDK_CONTRACT_NOT_VERIFIED")
                if not binding.sdk_document_reference.strip():
                    raise UntrustedFrame("SDK_DOCUMENT_REFERENCE_MISSING")
                if binding.generation <= last_generation:
                    raise UntrustedFrame("RECONNECT_GENERATION_NOT_ADVANCED")
                self.reader.bind(binding)
                last_generation = binding.generation
                retry_s = 0.25
                self.last_error = ""
                while not self._stop.is_set():
                    packet = self.sdk.receive_tf(timeout_s=0.2)
                    if packet is None:
                        # Some adapters poll nonblockingly: remain interruptible
                        # without burning a CPU core while no frame is available.
                        self._stop.wait(0.005)
                    if packet is not None:
                        if self.reader.ingest(packet):
                            self.frames_received += 1
                        else:
                            self.last_error = self.reader.last_rejection
                break
            except UntrustedFrame as exc:
                self.last_error = str(exc)
                break  # Never auto-retry a failed trust/protocol contract.
            except Exception as exc:
                self.last_error = "SDK_DISCONNECTED_" + type(exc).__name__
                self.reconnect_count += 1
                if self._stop.wait(retry_s):
                    break
                retry_s = min(retry_s * 2, 2.0)
            finally:
                if binding is not None:
                    self.reader.unbind(
                        binding.edition, binding.engine_id, binding.trace_id
                    )
                try:
                    self.sdk.close()
                except Exception:
                    pass
