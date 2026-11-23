import numpy as np

from qa_r65_native_latency import count_green, parse_latest_ready_ms


def test_latest_complete_native_ready_marker_wins():
    payload = (b"noise\nV8180_STATIC_MAG_NATIVE_READY_MS 812.4 source_score .98\n"
               b"V8180_STATIC_MAG_NATIVE_READY_MS 94.2 source_score .99\n")
    assert parse_latest_ready_ms(payload) == 94.2


def test_partial_or_missing_marker_is_not_evidence():
    assert parse_latest_ready_ms(b"V8180_STATIC_MAG_NATIVE_READY_MS ") is None
    assert parse_latest_ready_ms(b"unrelated") is None


def test_green_count_is_bounded_to_native_plot_rect():
    image = np.zeros((20, 30, 3), dtype=np.uint8)
    image[5:10, 7:12] = (20, 220, 20)
    assert count_green(image, (7, 5, 5, 5)) == 25
    assert count_green(image, (0, 0, 5, 5)) == 0
