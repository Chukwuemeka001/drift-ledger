"""High-level API over one thread's event log. Every mutation is one appended event."""
from __future__ import annotations

from . import model
from .model import AGENT, CONTROLLER, OWNER
from .store import Store


class LedgerError(Exception):
    pass


class Ledger:
    def __init__(self, thread_id: str):
        self.thread_id = thread_id
        self.store = Store(thread_id)

    def state(self) -> model.State:
        return model.fold(self.thread_id, self.store.read().events)

    def _append(self, kind, actor, payload, session_id=None, turn=None):
        before = self.state()
        ev = self.store.append(kind, actor, payload, session_id, turn)
        after = model.fold(self.thread_id, self.store.read().events)
        rejected = [r for (eid, r) in after.ignored if eid == ev["event_id"]]
        if rejected:
            # the event stays in the append-only log, but it had no effect — tell the caller
            raise LedgerError(rejected[0])
        return ev, before, after

    def record(self, actor, type, text, reason=None, scope=None, parent=None, matcher=None,
               session_id=None, turn=None) -> model.Entry:
        if actor not in (OWNER, AGENT):
            raise LedgerError("only owner or agent may record")
        if type not in model.TYPES:
            raise LedgerError(f"type must be one of {', '.join(model.TYPES)}")
        # duplicate proposal guard: same type + text already pending or governing
        norm = " ".join(text.split()).lower()
        for e in self.state().entries.values():
            if e.type == type and " ".join(e.text.split()).lower() == norm and e.status in (model.PROPOSED, model.ACTIVE):
                return e
        entry_id = self.state().next_id()
        payload = {"entry_id": entry_id, "type": type, "text": text, "reason": reason, "scope": scope,
                   "parent": parent, "matcher": matcher}
        _, _, after = self._append("record", actor, payload, session_id, turn)
        return after.entries[entry_id]

    def _do(self, kind, actor, entry_id, session_id=None, turn=None, **payload):
        payload["entry_id"] = entry_id
        _, _, after = self._append(kind, actor, payload, session_id, turn)
        return after.entries[entry_id]

    def confirm(self, entry_id, as_type=None, **kw):
        if as_type:
            if as_type not in model.TYPES:
                raise LedgerError(f"type must be one of {', '.join(model.TYPES)}")
            return self._do("confirm", OWNER, entry_id, as_type=as_type, **kw)
        return self._do("confirm", OWNER, entry_id, **kw)
    def reject(self, entry_id, reason=None, **kw): return self._do("reject", OWNER, entry_id, reason=reason, **kw)
    def discharge(self, entry_id, refs=None, note=None, **kw): return self._do("discharge", OWNER, entry_id, refs=refs or [], note=note, **kw)
    def consume(self, entry_id, note=None, **kw): return self._do("consume", OWNER, entry_id, note=note, **kw)
    def supersede(self, entry_id, scope=None, note=None, replacement=None, **kw):
        return self._do("supersede", OWNER, entry_id, scope=scope, note=note, replacement=replacement, **kw)
    def evidence(self, actor, entry_id, refs=None, note=None, **kw):
        return self._do("evidence", actor, entry_id, refs=refs or [], note=note, **kw)
    def flag(self, actor, entry_id, request, **kw): return self._do("flag", actor, entry_id, request=request, **kw)

    def confirm_all(self, **kw):
        return [self.confirm(e.id, **kw) for e in self.state().by_status(model.PROPOSED)]

    def boundary(self, source, session_id=None, summary_sha=None, context_tokens=None):
        self.store.append("boundary", CONTROLLER, {"source": source, "summary_sha": summary_sha,
                                                   "context_tokens": context_tokens}, session_id)

    def switch(self, off: bool):
        self.store.append("switch", OWNER, {"off": off})
