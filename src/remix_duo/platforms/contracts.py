"""Portable boundary types. Coordinates and evidence never imply native PASS."""
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Protocol

@dataclass(frozen=True)
class WindowRef:
    platform: str
    pid: int
    process_started: str
    opaque_id: str

@dataclass(frozen=True)
class Capability:
    ready: bool
    reason: str

@dataclass(frozen=True)
class WindowState:
    ref: WindowRef
    rect: tuple[float,float,float,float]  # Quartz logical top-left x,y,width,height
    title: str
    foreground: bool
    on_screen: bool
    version: str
    companion_foreground: bool = False

@dataclass(frozen=True)
class CapturedFrame:
    window: WindowState
    png: bytes
    width: int
    height: int
    captured_at: float

    def valid_for(self, current: WindowState, now: float, max_age: float=.45):
        age=now-self.captured_at
        return (self.window==current and (current.foreground or current.companion_foreground) and current.on_screen and
                bool(self.png) and self.width>0 and self.height>0 and
                math.isfinite(age) and 0<=age<=max_age)

@dataclass(frozen=True)
class SelectionEvidence:
    window: WindowRef
    selected: tuple[str, ...]
    observed_at: float  # monotonic, never wall time
    complete: bool
    visible_verified: tuple[str, ...]

    def verified_selected(self, current: WindowRef | None, now: float,
                          expected: int, max_age: float = 1.5) -> tuple[str, ...] | None:
        """Fail closed on stale, ambiguous or wrong-window native AX ticks.

        A selected checkbox is evidence only when the full visible row set was
        verified for the same live Smaart window and monotonic observation.
        """
        if current is None or type(expected) is not int or expected not in (1, 2):
            return None
        age = now - self.observed_at
        if (current != self.window or not current.process_started or
            not current.opaque_id or current.pid <= 0 or not self.complete or
            not math.isfinite(age) or not 0 <= age <= max_age or
            len(self.selected) != expected or
            len(set(self.selected)) != expected or
            len(set(self.visible_verified)) != len(self.visible_verified) or
            any(not x or x not in self.visible_verified for x in self.selected)):
            return None
        return self.selected

    def verified_pair(self, current: WindowRef, now: float,
                      max_age: float = 1.5) -> tuple[str, str] | None:
        return self.verified_selected(current, now, 2, max_age)

@dataclass(frozen=True)
class PixelTransform:
    logical_origin: tuple[float, float]
    physical_origin: tuple[float, float]
    scale: float

    def __post_init__(self):
        if (not math.isfinite(self.scale) or self.scale <= 0 or
            not all(math.isfinite(v) for v in (*self.logical_origin, *self.physical_origin))):
            raise ValueError('Invalid display transform')

    def to_physical(self, point):
        return tuple(p+(v-l)*self.scale for v,l,p in zip(point,self.logical_origin,self.physical_origin))

    def to_logical(self, point):
        return tuple(l+(v-p)/self.scale for v,l,p in zip(point,self.logical_origin,self.physical_origin))

class InstanceLease(Protocol):
    def close(self) -> None: ...

class PlatformServices(Protocol):
    platform: str
    def machine_code(self) -> str: ...
    def acquire_lock(self, name: str, directory: Path) -> InstanceLease | None: ...
    def native_capability(self) -> Capability: ...
    def read_selection(self, window: WindowRef) -> SelectionEvidence: ...
