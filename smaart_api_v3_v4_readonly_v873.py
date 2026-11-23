"""RemiX Duo V8.73 - passive Smaart 8 API3 / Smaart 9 API4 observer.

V3 source: https://github.com/bitfocus/companion-module-rationalacoustics-smaart3
V4 source: https://github.com/bitfocus/companion-module-rationalacoustics-smaart4
Only the documented Companion connection path and GET handshake are reused.
No SDK TF subscription/encoding is known: GET does not yield TFPacket.
This module is not imported by V8.72's GUI and cannot operate audio/DSP.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import time
from typing import Callable

EDITION_PATHS = {8: "/api/v3/", 9: "/api/v4/"}
SMAART_EXES = frozenset(("smaart.exe", "smaart suite.exe"))
MAX_REPLY_BYTES = 256 * 1024


@dataclass(frozen=True)
class SmaartProcess:
    pid: int
    edition: int
    exe: str
    created_at: float


@dataclass(frozen=True)
class PassiveMessage:
    """Metadata only. Never treat an unsolicited message as a TF frame."""
    byte_count: int
    sha256: str
    kind: str


@dataclass(frozen=True)
class ReadOnlyProbe:
    edition: int
    api: str
    status: str
    pid: int | None = None
    application_name: str | None = None
    messages: tuple[PassiveMessage, ...] = ()
    tf_stream_verified: bool = False  # NO documented TF subscription/parser.
    engine_verified: bool = False
    trace_verified: bool = False


def _version_from_windows_file(path: str) -> int | None:
    try:
        import win32api
        info = win32api.GetFileVersionInfo(path, "\\")
        return int(win32api.HIWORD(info["FileVersionMS"]))
    except (OSError, KeyError, ValueError, TypeError, ImportError):
        return None


def inspect_smaart_pid(pid: int) -> SmaartProcess | None:
    """Validate installed executable and Windows file major, never window text."""
    try:
        import os
        import psutil
        proc = psutil.Process(pid)
        exe = proc.exe()
        if os.path.basename(exe).lower() not in SMAART_EXES:
            return None
        major = _version_from_windows_file(exe)
        if major not in EDITION_PATHS:
            return None
        return SmaartProcess(pid, major, exe, proc.create_time())
    except (OSError, ValueError, ImportError):
        return None
    except Exception:  # psutil.AccessDenied/NoSuchProcess
        return None


def find_process(edition: int) -> tuple[str, SmaartProcess | None]:
    if edition not in EDITION_PATHS:
        return ("UNSUPPORTED_EDITION", None)
    try:
        import os
        import psutil
        candidates = []
        unverified = False
        for p in psutil.process_iter(["pid", "name"]):
            if (p.info.get("name") or "").lower() not in SMAART_EXES:
                continue
            identity = inspect_smaart_pid(p.info["pid"])
            if identity is None:
                unverified = True
            elif identity.edition == edition:
                candidates.append(identity)
        if len(candidates) != 1:
            return ("MULTIPLE_SMAART_INSTANCES" if len(candidates) > 1 else
                    "SMAART_VERSION_UNVERIFIED" if unverified else
                    "SMAART_NOT_RUNNING", None)
        return ("PROCESS_VERIFIED", candidates[0])
    except Exception:
        return ("PROCESS_DISCOVERY_UNAVAILABLE", None)


def port_owned_by(pid: int, port: int) -> bool:
    """A successful connect to another local WebSocket must never be accepted."""
    try:
        import psutil
        for connection in psutil.net_connections(kind="tcp"):
            if (connection.pid == pid and connection.status == "LISTEN"
                    and connection.laddr and connection.laddr.port == port):
                return True
    except Exception:
        return False
    return False


def _reply(raw: str | bytes, sequence: int) -> dict:
    if not isinstance(raw, (str, bytes)):
        raise ValueError("INVALID_MESSAGE_TYPE")
    if len(raw.encode("utf-8") if isinstance(raw, str) else raw) > MAX_REPLY_BYTES:
        raise ValueError("REPLY_TOO_LARGE")
    try:
        msg = json.loads(raw)
    except (ValueError, UnicodeDecodeError, TypeError) as exc:
        raise ValueError("INVALID_JSON_REPLY") from exc
    if not isinstance(msg, dict) or type(msg.get("sequenceNumber")) is not int:
        raise ValueError("INVALID_SEQUENCE")
    if msg["sequenceNumber"] != sequence:
        raise ValueError("SEQUENCE_MISMATCH")
    state = msg.get("response")
    if not isinstance(state, dict):
        raise ValueError("INVALID_RESPONSE_OBJECT")
    return state


def read_only_probe(
    edition: int, *, pid: int | None = None, port: int = 26000,
    timeout: float = 0.65, observe_s: float = 0.0,
    inspect: Callable[[int], SmaartProcess | None] = inspect_smaart_pid,
    find: Callable[[int], tuple[str, SmaartProcess | None]] = find_process,
    owns_port: Callable[[int, int], bool] = port_owned_by,
    websocket_factory: Callable | None = None,
) -> ReadOnlyProbe:
    """One exact V3 or V4 local read-only GET. No auto V3/V4 downgrade.

    Passive observe_s <= 2 seconds reads ONLY unsolicited messages after GET;
    hashes metadata, does not subscribe, decode TF or write audio controls.
    External socket factory is exclusively a unit-test seam.
    """
    if edition not in EDITION_PATHS:
        return ReadOnlyProbe(edition, "", "UNSUPPORTED_EDITION")
    api = "v3" if edition == 8 else "v4"
    def result(status, identity=None, app=None, messages=()):
        return ReadOnlyProbe(edition, api, status,
                             identity.pid if identity else None,
                             app, tuple(messages))
    if type(port) is not int or not 1 <= port <= 65535:
        return result("INVALID_PORT")
    if not (0.05 <= timeout <= 3.0) or not (0.0 <= observe_s <= 2.0):
        return result("INVALID_TIMEOUT")
    if pid is not None:
        identity = inspect(pid)
        if identity is None:
            return result("SMAART_PROCESS_UNVERIFIED")
    else:
        status, identity = find(edition)
        if identity is None:
            return result(status)
    if identity.edition != edition:
        return result("VERSION_MISMATCH")
    if not owns_port(identity.pid, port):
        return result("SMAART_API_LISTENER_UNVERIFIED", identity)

    sock = None
    try:
        if websocket_factory is None:
            import websocket
            websocket_factory = websocket.create_connection
        sock = websocket_factory(
            f"ws://127.0.0.1:{port}{EDITION_PATHS[edition]}",
            timeout=timeout, http_proxy_host=None
        )
        sock.send(json.dumps({"sequenceNumber": 1, "action": "get"},
                             separators=(",", ":")))
        state = _reply(sock.recv(), 1)
        if state.get("authenticationRequired") is True:
            return result("AUTH_REQUIRED_NO_PASSWORD_SENT", identity)
        if state.get("error") is not None:
            return result("API_GET_ERROR", identity)
        if state.get("authenticationRequired") is not False:
            return result("AUTH_STATE_NOT_CONFIRMED", identity)
        app = state.get("applicationName")
        app = app[:120] if isinstance(app, str) else None
        # Check PID hasn't been recycled or replaced during the handshake.
        current = inspect(identity.pid)
        if current != identity or not owns_port(identity.pid, port):
            return result("PROCESS_CHANGED_DURING_HANDSHAKE")
        events = []
        if observe_s:
            end = time.monotonic() + observe_s
            while len(events) < 16 and time.monotonic() < end:
                try:
                    if hasattr(sock, "settimeout"):
                        sock.settimeout(max(0.01, min(0.1, end-time.monotonic())))
                    msg = sock.recv()
                except TimeoutError:
                    continue
                except Exception as exc:
                    if type(exc).__name__.lower().endswith("timeout"):
                        continue
                    break
                if not isinstance(msg, (bytes, str)):
                    continue
                raw = msg.encode("utf-8") if isinstance(msg, str) else msg
                if len(raw) > MAX_REPLY_BYTES:
                    return result("UNSOLICITED_MESSAGE_TOO_LARGE", identity, app, events)
                # Metadata only. Never infer TF content from unknown JSON/binary.
                events.append(PassiveMessage(len(raw), hashlib.sha256(raw).hexdigest(),
                                             "BINARY_UNVERIFIED" if isinstance(msg, bytes)
                                             else "TEXT_UNVERIFIED"))
        return result("GET_CONFIRMED_NOT_TF_STREAM", identity, app, events)
    except ValueError as exc:
        return result(str(exc), identity)
    except Exception as exc:
        return result("API_CONNECT_" + type(exc).__name__.upper(), identity)
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass


def probe_v3(**kwargs) -> ReadOnlyProbe:
    return read_only_probe(8, **kwargs)


def probe_v4(**kwargs) -> ReadOnlyProbe:
    return read_only_probe(9, **kwargs)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Passive local Smaart GET, NO TF claim")
    p.add_argument("--edition", type=int, choices=(8, 9), required=True)
    p.add_argument("--pid", type=int, default=None)
    p.add_argument("--port", type=int, default=26000)
    p.add_argument("--observe-seconds", type=float, default=0.0)
    args = p.parse_args()
    outcome = read_only_probe(args.edition, pid=args.pid, port=args.port,
                              observe_s=args.observe_seconds)
    print(json.dumps({
        "edition": outcome.edition, "api": outcome.api,
        "status": outcome.status, "pid": outcome.pid,
        "application_name": outcome.application_name,
        "unsolicited_count": len(outcome.messages),
        "unsolicited": [vars(item) for item in outcome.messages],
        "tf_stream_verified": outcome.tf_stream_verified,
        "engine_verified": outcome.engine_verified,
        "trace_verified": outcome.trace_verified,
    }, indent=2))
