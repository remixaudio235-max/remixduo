"""Regression tests for fail-closed Native TF protocol type validation."""

from dataclasses import replace

import pytest

from smaart_live_tf_reader_v873 import (
    NativeTFReader,
    SDKBinding,
    TFPacket,
    UntrustedFrame,
)


def binding(**updates):
    value = SDKBinding(
        8,
        "v3",
        "engine-1",
        "trace-A",
        1,
        48000,
        verified=True,
        sdk_document_reference="UNIT_TEST_FIXTURE_ONLY",
    )
    return replace(value, **updates)


def packet(**updates):
    value = TFPacket(
        8,
        "v3",
        "engine-1",
        "trace-A",
        1,
        1,
        1_000_000,
        48000,
        (100.0, 1000.0),
        (-3.0, 0.0),
        (0.0, 1.0),
        (0.9, 0.8),
        0.0,
        "NATIVE_SDK_STREAM",
    )
    return replace(value, **updates)


@pytest.mark.parametrize(
    ("updates", "error"),
    [
        ({"sequence": True}, "INVALID_SEQUENCE"),
        ({"source_timestamp_ns": True}, "MISSING_SOURCE_TIMESTAMP"),
        ({"frequency_hz": (False, True)}, "NONFINITE_TF"),
        ({"magnitude_db": (False, True)}, "NONFINITE_TF"),
        ({"phase_rad": (False, True)}, "NONFINITE_TF"),
        ({"coherence": (False, True)}, "INVALID_COHERENCE"),
    ],
)
def test_boolean_protocol_scalars_are_rejected(updates, error):
    reader = NativeTFReader()
    reader.bind(binding())

    assert not reader.ingest(packet(**updates), received_ns=100)
    assert reader.last_rejection == error


def test_boolean_generation_is_rejected_at_binding_boundary():
    reader = NativeTFReader()

    with pytest.raises(UntrustedFrame, match="INVALID_GENERATION"):
        reader.bind(binding(generation=True))


def test_unhashable_packet_identity_fails_closed_instead_of_raising():
    reader = NativeTFReader()
    reader.bind(binding())

    assert not reader.ingest(packet(engine_id=["engine-1"]), received_ns=100)
    assert reader.last_rejection == "INVALID_SOURCE_ID"


def test_unhashable_binding_identity_is_rejected_explicitly():
    reader = NativeTFReader()

    with pytest.raises(UntrustedFrame, match="INVALID_SOURCE_ID"):
        reader.bind(binding(engine_id=["engine-1"]))


@pytest.mark.parametrize(
    "updates",
    [
        {"frequency_hz": [100.0, 1000.0]},
        {"magnitude_db": [-3.0, 0.0]},
        {"phase_rad": [0.0, 1.0]},
        {"coherence": [0.9, 0.8]},
    ],
)
def test_mutable_tf_arrays_cannot_enter_the_frame_cache(updates):
    reader = NativeTFReader()
    reader.bind(binding())

    assert not reader.ingest(packet(**updates), received_ns=100)
    assert reader.last_rejection == "INVALID_TF_ARRAY_TYPE"
    assert reader.latest(8, "engine-1", "trace-A", now_ns=101) is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_traces": True},
        {"max_traces": 1.5},
        {"ttl_ms": True},
        {"ttl_ms": 1.5},
    ],
)
def test_reader_bounds_require_plain_integers(kwargs):
    with pytest.raises(ValueError, match="Invalid reader bounds"):
        NativeTFReader(**kwargs)


@pytest.mark.parametrize("sample_rate", [True, float("nan"), 7999, 384001])
def test_invalid_binding_sample_rate_is_rejected_early(sample_rate):
    reader = NativeTFReader()

    with pytest.raises(UntrustedFrame, match="INVALID_FS"):
        reader.bind(binding(sample_rate_hz=sample_rate))


def test_truthy_non_boolean_verification_flag_cannot_establish_trust():
    reader = NativeTFReader()

    with pytest.raises(UntrustedFrame, match="INVALID_VERIFICATION_FLAG"):
        reader.bind(binding(verified=1))


def test_non_string_sdk_document_reference_is_rejected_explicitly():
    reader = NativeTFReader()

    with pytest.raises(UntrustedFrame, match="INVALID_SDK_DOCUMENT_REFERENCE"):
        reader.bind(binding(sdk_document_reference=123))


def test_non_packet_sdk_value_fails_closed_without_an_exception():
    reader = NativeTFReader()

    assert not reader.ingest(object(), received_ns=100)
    assert reader.last_rejection == "INVALID_PACKET"
