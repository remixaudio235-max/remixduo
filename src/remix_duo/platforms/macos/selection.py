"""Strict AX checkbox evidence; highlight/mtime order is never a tick."""
from dataclasses import dataclass
from ..contracts import SelectionEvidence

@dataclass(frozen=True)
class TraceRow:
    identity: str
    enabled: bool | None
    visible: bool

def checkbox_state(attributes):
    if attributes.get('AXRole')!='AXCheckBox':return None
    value=attributes.get('AXValue')
    if type(value) in (int,bool) and value in (0,1):return bool(value)
    return None

def selection_from_rows(window,rows,*,total,observed_at):
    names=[r.identity for r in rows]
    complete=(type(total) is int and total>0 and len(rows)==total and
        len(set(names))==len(names) and all(r.identity and r.visible and type(r.enabled) is bool for r in rows))
    return SelectionEvidence(window,tuple(r.identity for r in rows if r.enabled is True),observed_at,
                             complete,tuple(r.identity for r in rows if r.visible and type(r.enabled) is bool))
