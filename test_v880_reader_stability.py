from dataclasses import replace
import time
from smaart_live_tf_reader_v873 import NativeTFReader, NativeSDKWorker, SDKBinding, TFPacket


def binding():
    return SDKBinding(8, 'v3', 'test-engine', 'test-trace', 1, 48000,
                      True, 'SYNTHETIC UNIT CONTRACT, NOT LIVE SDK')


def packet():
    return TFPacket(8, 'v3', 'test-engine', 'test-trace', 1, 1, 1, 48000,
                    (100., 1000.), (0., 0.), (0., 0.), origin='NATIVE_SDK_STREAM')


def test_malformed_edition_cannot_crash_ingest():
    reader = NativeTFReader()
    reader.bind(binding())
    assert reader.ingest(replace(packet(), edition=[])) is False


def test_empty_nonblocking_sdk_does_not_busy_spin():
    class EmptySDK:
        calls = 0
        def connect_readonly(self): return binding()
        def receive_tf(self, timeout_s):
            self.calls += 1
            return None
        def close(self): pass
    sdk = EmptySDK()
    worker = NativeSDKWorker(NativeTFReader(), sdk)
    worker.start()
    try:
        time.sleep(.15)
    finally:
        worker.stop()
    assert sdk.calls < 100, f'Busy loop: {sdk.calls} empty polls in 150ms'
    assert not worker._thread.is_alive()
