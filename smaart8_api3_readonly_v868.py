"""Smaart 8 API V3 bridge (read-only). Reference: Companion Smaart3 v2.1.2.

Only allow get action. In particular, never implement the Companion's API
'set' or 'issueCommand' actions, which can control generator and measurements.
This observer does NOT claim API provides desktop plot rectangles or trace ticks.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import json
import time
import win32process
import win32api
import pywintypes
import psutil

@dataclass(frozen=True)
class Probe:
    ok: bool
    status: str
    response: dict[str, Any] | None = None

# V8.113: (pid, create_time, exe) -> major. Called from App.tick() every
# 33 ms; reading version resources each time is wasteful and, under low
# commit memory, raised pywintypes.error (not OSError) that crashed the GUI.
_MAJOR_CACHE: dict[tuple, int] = {}

def process_smaart_major(hwnd: int) -> int | None:
    try:
        _, pid=win32process.GetWindowThreadProcessId(hwnd)
        proc=psutil.Process(pid)
        path=proc.exe()
        if not path.lower().endswith(("smaart.exe","smaart suite.exe")):
            return None
        key=(pid, proc.create_time(), path.lower())
        if key in _MAJOR_CACHE:
            return _MAJOR_CACHE[key]
        data=win32api.GetFileVersionInfo(path,"\\")
        major=int(win32api.HIWORD(data["FileVersionMS"]))
        if len(_MAJOR_CACHE)>32:
            _MAJOR_CACHE.clear()
        _MAJOR_CACHE[key]=major
        return major
    except (OSError, KeyError, ValueError, TypeError, psutil.Error,
            pywintypes.error):
        return None  # fail closed: unknown edition

def read_only_query(sock) -> dict:
    """Fixed GET only. Reject unknown response and auth challenges."""
    payload={"sequenceNumber":1,"action":"get"}
    sock.send(json.dumps(payload,separators=(",",":")))
    reply=json.loads(sock.recv())
    if not isinstance(reply,dict) or reply.get("sequenceNumber")!=1:
        raise ValueError("Unexpected Smaart V3 sequence/response")
    if not isinstance(reply.get("response"),dict):
        raise ValueError("No API V3 response object")
    return reply

def probe_api_v3(hwnd:int,*,host="127.0.0.1",port=26000,timeout=0.6) -> Probe:
    """Probe V3 locally only, and only for verified Smaart 8 process."""
    if process_smaart_major(hwnd)!=8:
        return Probe(False,"NOT_SMAART_8")
    if host not in ("127.0.0.1","localhost","::1"):
        return Probe(False,"REMOTE_HOST_DISABLED")
    if not isinstance(port,int) or not 1<=port<=65535:
        return Probe(False,"INVALID_PORT")
    sock=None
    try:
        import websocket
        sock=websocket.create_connection(
            f"ws://127.0.0.1:{port}/api/v3/",timeout=timeout,
            http_proxy_host=None)
        response=read_only_query(sock)
        state=response["response"]
        if state.get("authenticationRequired"):
            return Probe(False,"AUTH_REQUIRED")
        if state.get("error") is not None:
            return Probe(False,"API_V3_ERROR")
        return Probe(True,"API_V3_READ_ONLY",state)
    except (OSError,TimeoutError,ValueError,KeyError,TypeError,
            json.JSONDecodeError) as exc:
        return Probe(False,type(exc).__name__.upper())
    except Exception as exc:
        # Includes websocket handshake/connection errors.
        return Probe(False,type(exc).__name__.upper())
    finally:
        if sock:
            try:sock.close()
            except Exception:pass

_last: tuple[float,int,Probe] | None=None
def cached_probe(hwnd:int,interval=30.0)->Probe:
    global _last
    now=time.monotonic()
    if _last and _last[1]==hwnd and now-_last[0]<interval:
        return _last[2]
    result=probe_api_v3(hwnd)
    _last=(now,hwnd,result)
    return result
