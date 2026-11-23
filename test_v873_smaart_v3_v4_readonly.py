"""V8.73 GitHub Bitfocus V3/V4 API GET unit tests; NO real TF fixtures."""
import json
from dataclasses import replace
import pytest

from smaart_api_v3_v4_readonly_v873 import (
    ReadOnlyProbe, SmaartProcess, MAX_REPLY_BYTES, probe_v3, probe_v4,
    read_only_probe, _reply
)


class DummySocket:
    def __init__(self, reply=None, extra=()):
        if reply is None:
            reply = {"sequenceNumber": 1,
                     "response": {"authenticationRequired": False,
                                  "applicationName": "Smaart Test Fixture"}}
        self.queue = [json.dumps(reply), *extra]
        self.sent = []
        self.closed = False
    def send(self, message):
        self.sent.append(json.loads(message))
    def recv(self):
        if self.queue:
            return self.queue.pop(0)
        raise TimeoutError()
    def settimeout(self, seconds):
        assert seconds <= 0.10001
    def close(self):
        self.closed = True


def setup(edition, sock=None, *, port_owned=True, actual_edition=None):
    sock = sock or DummySocket()
    proc = SmaartProcess(1444, actual_edition or edition,
                         r"C:\Program Files\Smaart\Smaart.exe", 10000.0)
    urls = []
    def factory(url, **kwargs):
        urls.append((url, kwargs))
        return sock
    params = dict(
        pid=proc.pid,
        inspect=lambda pid: proc if pid == proc.pid else None,
        owns_port=lambda pid, port: port_owned and pid == 1444 and port == 26000,
        websocket_factory=factory,
    )
    return sock, urls, params


@pytest.mark.parametrize("edition,path", [(8, "/api/v3/"), (9, "/api/v4/")])
def test_github_connection_and_only_get(edition, path):
    sock, urls, kw = setup(edition)
    result = read_only_probe(edition, **kw)
    assert urls == [(f"ws://127.0.0.1:26000{path}",
                      {"timeout": 0.65, "http_proxy_host": None})]
    assert sock.sent == [{"sequenceNumber": 1, "action": "get"}]
    assert sock.closed
    assert result.status == "GET_CONFIRMED_NOT_TF_STREAM"
    assert result.application_name == "Smaart Test Fixture"
    assert not result.tf_stream_verified
    assert not result.engine_verified and not result.trace_verified


def test_version_mismatch_never_opens_socket():
    sock, urls, kw = setup(8, actual_edition=9)
    assert probe_v3(**kw).status == "VERSION_MISMATCH"
    assert not urls and not sock.sent


@pytest.mark.parametrize("edition", [8, 9])
def test_port_not_owned_by_smaart_fail_closed(edition):
    sock, urls, kw = setup(edition, port_owned=False)
    assert read_only_probe(edition, **kw).status == "SMAART_API_LISTENER_UNVERIFIED"
    assert not urls


@pytest.mark.parametrize("edition", [8, 9])
def test_auth_challenge_never_sends_set_or_password(edition):
    sock = DummySocket({"sequenceNumber": 1,
                        "response": {"authenticationRequired": True}})
    sock, urls, kw = setup(edition, sock)
    response = read_only_probe(edition, **kw)
    assert response.status == "AUTH_REQUIRED_NO_PASSWORD_SENT"
    assert sock.sent == [{"sequenceNumber": 1, "action": "get"}]
    assert sock.closed


@pytest.mark.parametrize("state,expected", [
    ({"error": "not supported", "authenticationRequired": False}, "API_GET_ERROR"),
    ({"server": "Smaart"}, "AUTH_STATE_NOT_CONFIRMED"),
    ({"authenticationRequired": None}, "AUTH_STATE_NOT_CONFIRMED"),
])
def test_fail_closed_on_error_or_missing_auth(state, expected):
    sock, _, kw = setup(9, DummySocket({"sequenceNumber": 1, "response": state}))
    assert probe_v4(**kw).status == expected
    assert sock.closed


@pytest.mark.parametrize("reply,expected", [
    ({"sequenceNumber": 2, "response": {}}, "SEQUENCE_MISMATCH"),
    ({"sequenceNumber": True, "response": {}}, "INVALID_SEQUENCE"),
    ({"sequenceNumber": 1, "response": []}, "INVALID_RESPONSE_OBJECT"),
    ([], "INVALID_SEQUENCE"),
])
def test_malformed_sequence_or_response(reply, expected):
    sock, _, kw = setup(9, DummySocket(reply))
    assert probe_v4(**kw).status == expected


def test_invalid_json_and_size_limit():
    with pytest.raises(ValueError, match="INVALID_JSON_REPLY"):
        _reply(b"\xff", 1)
    with pytest.raises(ValueError, match="REPLY_TOO_LARGE"):
        _reply("x" * (MAX_REPLY_BYTES+1), 1)


def test_unsolicited_message_is_unverified_and_never_tf_frame():
    extra = ('{"something":"unsolicited"}', b"\x00\x04\x89data")
    sock, _, kw = setup(9, DummySocket(extra=extra))
    outcome = probe_v4(**kw, observe_s=0.03)
    assert outcome.status == "GET_CONFIRMED_NOT_TF_STREAM"
    assert len(outcome.messages) == 2
    assert outcome.messages[0].kind == "TEXT_UNVERIFIED"
    assert outcome.messages[1].kind == "BINARY_UNVERIFIED"
    assert all(len(x.sha256) == 64 for x in outcome.messages)
    assert outcome.tf_stream_verified is False


def test_process_replaced_after_get_rejected():
    proc = SmaartProcess(1444, 8, "Smaart.exe", 101.0)
    times = [proc, replace(proc, created_at=102.0)]
    sock = DummySocket()
    result = probe_v3(
        pid=1444,
        inspect=lambda pid: times.pop(0),
        owns_port=lambda pid, port: True,
        websocket_factory=lambda url, **kw: sock
    )
    assert result.status == "PROCESS_CHANGED_DURING_HANDSHAKE"
    assert sock.closed


def test_no_process_never_connects():
    sock, urls, kw = setup(9)
    kw["find"] = lambda edition: ("SMAART_NOT_RUNNING", None)
    assert read_only_probe(9, pid=None, **{k:v for k,v in kw.items() if k!="pid"}).status == "SMAART_NOT_RUNNING"
    assert not urls


def test_reject_user_supplied_host_and_unrelated_commands():
    # No host parameter and no "send" or "set" public API surface.
    sock, _, kw = setup(8)
    with pytest.raises(TypeError):
        probe_v3(host="192.168.1.99", **kw)
    assert not sock.sent
    assert probe_v3(**kw).tf_stream_verified is False


def test_explicit_version_wrappers_are_isolated():
    sock8, urls8, kw8 = setup(8)
    sock9, urls9, kw9 = setup(9)
    assert probe_v3(**kw8).api == "v3"
    assert probe_v4(**kw9).api == "v4"
    assert urls8[0][0] != urls9[0][0]


def test_bad_timeouts_never_connect():
    sock, urls, kw = setup(8)
    assert probe_v3(**kw, observe_s=60).status == "INVALID_TIMEOUT"
    assert probe_v3(**kw, timeout=0).status == "INVALID_TIMEOUT"
    assert not urls
