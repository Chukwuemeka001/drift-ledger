"""Ledger state = deterministic fold over the event log.

Authority rules live here, not in callers: only the owner can make an entry governing, discharge
an obligation, consume an exception or supersede an entry. Agents can only propose, flag, and
offer evidence. Invalid events are kept in the log but ignored by the fold (and reported).
"""
from __future__ import annotations

from dataclasses import dataclass, field

TYPES = ("decision", "constraint", "parked", "obligation", "boundary", "exception", "mission")
OWNER = "owner"
AGENT = "agent"
CONTROLLER = "controller"

# status lifecycle
PROPOSED, ACTIVE, REJECTED = "PROPOSED", "ACTIVE", "REJECTED"
DISCHARGED, CONSUMED, SUPERSEDED = "DISCHARGED", "CONSUMED", "SUPERSEDED"


@dataclass
class Entry:
    id: str
    type: str
    text: str
    reason: str | None = None
    scope: str | None = None
    parent: str | None = None          # exceptions: the entry they lift, scoped
    matcher: dict | None = None        # mechanical matcher for action gates
    status: str = PROPOSED
    proposed_by: str | None = None
    created: dict = field(default_factory=dict)   # {session_id, turn, ts}
    confirmed: dict | None = None
    evidence: list = field(default_factory=list)  # [{by, refs, note, ts, accepted}]
    superseded_by: dict | None = None             # {by, scope, note, ts}
    consumed: dict | None = None
    flags: list = field(default_factory=list)     # [{request, session_id, ts}]
    history: list = field(default_factory=list)   # event ids

    @property
    def governing(self) -> bool:
        return self.status == ACTIVE

    @property
    def open_obligation(self) -> bool:
        return self.type == "obligation" and self.status == ACTIVE


@dataclass
class State:
    thread_id: str
    entries: dict = field(default_factory=dict)
    boundaries: list = field(default_factory=list)
    ignored: list = field(default_factory=list)   # (event_id, reason)
    off: bool = False

    def next_id(self) -> str:
        return f"L{len(self.entries) + 1}"

    def by_status(self, *statuses):
        return [e for e in self.entries.values() if e.status in statuses]


def _meta(ev):
    return {"session_id": ev.get("session_id"), "turn": ev.get("turn"), "ts": ev.get("ts")}


def fold(thread_id: str, events: list) -> State:
    st = State(thread_id=thread_id)
    for ev in events:
        err = _apply(st, ev)
        if err:
            st.ignored.append((ev.get("event_id"), err))
    return st


def _apply(st: State, ev: dict) -> str | None:
    kind, actor, p = ev.get("kind"), ev.get("actor"), ev.get("payload") or {}
    eid = p.get("entry_id")
    e = st.entries.get(eid) if eid else None

    if kind == "record":
        if eid in st.entries:
            return "duplicate entry id"
        if p.get("type") not in TYPES or not (p.get("text") or "").strip():
            return "invalid entry"
        if p.get("type") == "exception" and p.get("parent") not in st.entries:
            return "exception needs an existing parent entry"
        status = ACTIVE if actor == OWNER else PROPOSED
        if actor not in (OWNER, AGENT):
            return "only owner or agent may record"
        st.entries[eid] = Entry(
            id=eid, type=p["type"], text=p["text"].strip(), reason=p.get("reason"),
            scope=p.get("scope"), parent=p.get("parent"), matcher=p.get("matcher"),
            status=status, proposed_by=actor, created=_meta(ev),
            confirmed=_meta(ev) if status == ACTIVE else None, history=[ev.get("event_id")])
        return None

    if kind in ("confirm", "reject", "discharge", "consume", "supersede", "evidence", "flag") and e is None:
        return "unknown entry"

    if kind == "confirm":
        if actor != OWNER: return "only the owner can confirm"
        if e.status != PROPOSED: return f"cannot confirm from {e.status}"
        if p.get("as_type"):
            if p["as_type"] not in TYPES: return "invalid type"
            e.type = p["as_type"]
        e.status, e.confirmed = ACTIVE, _meta(ev)
    elif kind == "reject":
        if actor != OWNER: return "only the owner can reject"
        if e.status != PROPOSED: return f"cannot reject from {e.status}"
        e.status = REJECTED
    elif kind == "evidence":
        # anyone may attach evidence; it never changes status by itself
        e.evidence.append({"by": actor, "refs": p.get("refs") or [], "note": p.get("note"), **_meta(ev)})
    elif kind == "discharge":
        if actor != OWNER: return "only the owner can discharge"
        if not (e.type == "obligation" and e.status == ACTIVE): return "not an open obligation"
        e.status = DISCHARGED
        e.evidence.append({"by": OWNER, "refs": p.get("refs") or [], "note": p.get("note"), "accepted": True, **_meta(ev)})
    elif kind == "consume":
        if actor != OWNER: return "only the owner can mark an exception consumed"
        if not (e.type == "exception" and e.status == ACTIVE): return "not an active exception"
        e.status, e.consumed = CONSUMED, {"note": p.get("note"), **_meta(ev)}
    elif kind == "supersede":
        if actor != OWNER: return "only the owner can supersede"
        if e.status not in (ACTIVE,): return f"cannot supersede from {e.status}"
        e.status = SUPERSEDED
        e.superseded_by = {"by": OWNER, "scope": p.get("scope"), "note": p.get("note"),
                           "replacement": p.get("replacement"), **_meta(ev)}
    elif kind == "flag":
        e.flags.append({"by": actor, "request": p.get("request"), **_meta(ev)})
    elif kind == "boundary":
        if actor != CONTROLLER: return "only the controller records boundaries"
        st.boundaries.append({"source": p.get("source"), "summary_sha": p.get("summary_sha"),
                              "context_tokens": p.get("context_tokens"), **_meta(ev)})
        return None
    elif kind == "switch":
        if actor != OWNER: return "only the owner can switch the ledger on/off"
        st.off = bool(p.get("off"))
        return None
    else:
        return f"unknown kind {kind}"
    e.history.append(ev.get("event_id"))
    return None
