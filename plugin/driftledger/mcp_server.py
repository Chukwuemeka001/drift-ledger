#!/usr/bin/env python3
"""Drift Ledger MCP server (stdio, newline-delimited JSON-RPC 2.0, stdlib only).

Agent-side tools only: propose, attach evidence, flag a conflict, read status. Nothing here can make
an entry governing, discharge an obligation or lift a rule — those are owner commands.
"""
import json
import os
import sys

from . import model, packet, threads
from .ledger import Ledger, LedgerError

PROTOCOL = "2025-06-18"
TOOLS = [
    {"name": "ledger_propose",
     "description": "Propose a governing entry the OWNER just stated (decision, rule, parked item, obligation, "
                    "boundary, one-time exception). Quote the owner's words. It stays PROPOSED until the owner confirms. "
                    "Never propose your own ideas or task steps.",
     "inputSchema": {"type": "object", "required": ["type", "text"], "properties": {
         "type": {"type": "string", "enum": list(model.TYPES)},
         "text": {"type": "string", "description": "the owner's words"},
         "reason": {"type": "string"}, "scope": {"type": "string"},
         "parent": {"type": "string", "description": "for exception: the entry id it lifts (e.g. L4)"}}}},
    {"name": "ledger_attach_evidence",
     "description": "Attach evidence to an open obligation (commands run, exit codes, files). This does NOT mark it "
                    "done; only the owner can discharge it.",
     "inputSchema": {"type": "object", "required": ["entry_id", "refs"], "properties": {
         "entry_id": {"type": "string"}, "refs": {"type": "array", "items": {"type": "string"}},
         "note": {"type": "string"}}}},
    {"name": "ledger_flag_conflict",
     "description": "Record that an owner request conflicts with a governing entry (use when you flag it to the owner).",
     "inputSchema": {"type": "object", "required": ["entry_id", "request"], "properties": {
         "entry_id": {"type": "string"}, "request": {"type": "string"}}}},
    {"name": "ledger_status",
     "description": "Read the current governing ledger for this project's thread.",
     "inputSchema": {"type": "object", "properties": {}}},
]


def ledger():
    return Ledger(threads.resolve(os.environ.get("DRIFTLEDGER_CWD") or os.getcwd()))


def call(name, a):
    L = ledger()
    if name == "ledger_propose":
        e = L.record(model.AGENT, a["type"], a["text"], reason=a.get("reason"), scope=a.get("scope"), parent=a.get("parent"))
        return f"Proposed {e.id} ({e.type}, {e.status}). Tell the owner in one line: \"Proposed {e.id} [{e.type.upper()}]: {e.text[:80]} — /drift-ledger:confirm {e.id} (or: confirm {e.id} as <type>)\"."
    if name == "ledger_attach_evidence":
        e = L.evidence(model.AGENT, a["entry_id"], refs=a.get("refs"), note=a.get("note"))
        return f"Evidence attached to {e.id}; status still {e.status} (owner discharges)."
    if name == "ledger_flag_conflict":
        e = L.flag(model.AGENT, a["entry_id"], a["request"])
        return f"Conflict with {e.id} recorded. Ask the owner once whether to proceed."
    if name == "ledger_status":
        return packet.render(L.state(), "resume", budget=4000)
    raise LedgerError(f"unknown tool {name}")


def reply(i, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": i}
    msg.update({"error": error} if error else {"result": result})
    sys.stdout.write(json.dumps(msg) + "\n"); sys.stdout.flush()


def main():
    for line in sys.stdin:
        try:
            req = json.loads(line)
        except ValueError:
            continue
        m, i, p = req.get("method"), req.get("id"), req.get("params") or {}
        if i is None:          # notification
            continue
        if m == "initialize":
            reply(i, {"protocolVersion": p.get("protocolVersion", PROTOCOL), "capabilities": {"tools": {}},
                      "serverInfo": {"name": "drift-ledger", "version": "0.1.0"}})
        elif m == "tools/list":
            reply(i, {"tools": TOOLS})
        elif m == "tools/call":
            try:
                text, err = call(p.get("name"), p.get("arguments") or {}), False
            except (LedgerError, KeyError) as ex:
                text, err = f"Drift Ledger: {ex}", True
            reply(i, {"content": [{"type": "text", "text": text}], "isError": err})
        elif m == "ping":
            reply(i, {})
        else:
            reply(i, error={"code": -32601, "message": f"method not found: {m}"})


if __name__ == "__main__":
    main()
