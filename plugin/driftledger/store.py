"""Append-only, hash-chained event log per thread.

The log is never edited or truncated. Unparseable lines are skipped on read and copied once to a
quarantine file next to the log (corrupt bytes are preserved, never repaired).
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field

SCHEMA_VERSION = 1


def home() -> str:
    return os.environ.get("DRIFTLEDGER_HOME") or os.path.expanduser("~/.driftledger")


def thread_dir(thread_id: str) -> str:
    return os.path.join(home(), "threads", thread_id)


def _canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def event_hash(event: dict) -> str:
    body = {k: v for k, v in event.items() if k != "hash"}
    return hashlib.sha256(_canonical(body)).hexdigest()


@dataclass
class ReadResult:
    events: list = field(default_factory=list)
    quarantined: list = field(default_factory=list)  # (line_no, raw)


class Store:
    def __init__(self, thread_id: str):
        self.thread_id = thread_id
        self.dir = thread_dir(thread_id)
        self.path = os.path.join(self.dir, "events.jsonl")
        self.quarantine_path = os.path.join(self.dir, "quarantine.jsonl")

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def read(self) -> ReadResult:
        res = ReadResult()
        if not os.path.exists(self.path):
            return res
        with open(self.path, "rb") as fh:
            for n, raw in enumerate(fh, 1):
                line = raw.decode("utf-8", errors="replace").rstrip("\n")
                if not line.strip():
                    continue
                try:
                    ev = json.loads(line)
                    if not isinstance(ev, dict) or "kind" not in ev:
                        raise ValueError("not an event")
                except ValueError:
                    res.quarantined.append((n, line))
                    continue
                res.events.append(ev)
        if res.quarantined:
            self._quarantine(res.quarantined)
        return res

    def _quarantine(self, items) -> None:
        seen = set()
        if os.path.exists(self.quarantine_path):
            with open(self.quarantine_path) as fh:
                for line in fh:
                    try:
                        seen.add(json.loads(line)["line"])
                    except (ValueError, KeyError):
                        pass
        new = [(n, raw) for n, raw in items if n not in seen]
        if new:
            with open(self.quarantine_path, "a") as fh:
                for n, raw in new:
                    fh.write(json.dumps({"line": n, "raw": raw, "quarantined_at": time.time()}) + "\n")

    def append(self, kind: str, actor: str, payload: dict, session_id: str | None = None,
               turn: int | None = None) -> dict:
        """Append one event atomically (exclusive lock, fsync). Returns the stored event."""
        os.makedirs(self.dir, exist_ok=True)
        with open(self.path, "a+b") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                fh.seek(0)
                prev = None
                for raw in fh:
                    try:
                        prev = json.loads(raw).get("hash", prev)
                    except ValueError:
                        continue
                ev = {
                    "v": SCHEMA_VERSION,
                    "event_id": uuid.uuid4().hex,
                    "thread_id": self.thread_id,
                    "ts": time.time(),
                    "kind": kind,
                    "actor": actor,
                    "session_id": session_id,
                    "turn": turn,
                    "payload": payload,
                    "prev_hash": prev,
                }
                ev["hash"] = event_hash(ev)
                fh.seek(0, os.SEEK_END)
                fh.write((json.dumps(ev, ensure_ascii=False) + "\n").encode())
                fh.flush()
                os.fsync(fh.fileno())
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
        return ev

    def verify(self) -> dict:
        """Check every event's own hash and its link to the previous event."""
        res = self.read()
        problems = []
        prev = None
        for i, ev in enumerate(res.events):
            if ev.get("v") != SCHEMA_VERSION:
                problems.append({"index": i, "problem": f"unsupported schema version {ev.get('v')}"})
            if event_hash(ev) != ev.get("hash"):
                problems.append({"index": i, "event_id": ev.get("event_id"), "problem": "hash mismatch (edited)"})
            if ev.get("prev_hash") != prev:
                problems.append({"index": i, "event_id": ev.get("event_id"), "problem": "chain break (inserted/removed)"})
            prev = ev.get("hash")
        return {"events": len(res.events), "quarantined": len(res.quarantined),
                "ok": not problems and not res.quarantined, "problems": problems}
