"""Thread binding: a work thread is bound to (project folder, git branch) by default.

Registry: $DRIFTLEDGER_HOME/threads.json = {"bindings": {binding: thread_id}, "threads": {id: {...}}}
"""
from __future__ import annotations

import json
import os
import re
import time

from .store import home


def _registry_path():
    return os.path.join(home(), "threads.json")


def _load():
    p = _registry_path()
    if os.path.exists(p):
        with open(p) as fh:
            return json.load(fh)
    return {"bindings": {}, "threads": {}}


def _save(reg):
    os.makedirs(home(), exist_ok=True)
    tmp = _registry_path() + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(reg, fh, indent=1)
    os.replace(tmp, _registry_path())


def git_branch(cwd: str) -> str | None:
    d = os.path.realpath(cwd)
    while True:
        head = os.path.join(d, ".git", "HEAD")
        if os.path.isfile(head):
            with open(head) as fh:
                ref = fh.read().strip()
            return ref.rsplit("/", 1)[-1] if ref.startswith("ref:") else ref[:12]
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def binding_for(cwd: str) -> str:
    b = git_branch(cwd)
    return os.path.realpath(cwd) + (f"@{b}" if b else "")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "thread"


def resolve(cwd: str, create: bool = True) -> str | None:
    reg = _load()
    b = binding_for(cwd)
    if b in reg["bindings"]:
        return reg["bindings"][b]
    if not create:
        return None
    return new_thread(cwd, os.path.basename(os.path.realpath(cwd)), reg=reg)


def new_thread(cwd: str, name: str, reg=None) -> str:
    reg = reg or _load()
    base = _slug(name)
    tid, n = base, 2
    while tid in reg["threads"]:
        tid, n = f"{base}-{n}", n + 1
    reg["threads"][tid] = {"name": name, "created": time.time(), "cwd": os.path.realpath(cwd)}
    reg["bindings"][binding_for(cwd)] = tid
    _save(reg)
    return tid


def use_thread(cwd: str, thread_id: str) -> None:
    reg = _load()
    if thread_id not in reg["threads"]:
        raise KeyError(thread_id)
    reg["bindings"][binding_for(cwd)] = thread_id
    _save(reg)


def list_threads() -> dict:
    return _load()
