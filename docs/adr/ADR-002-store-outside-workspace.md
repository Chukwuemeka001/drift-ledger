# ADR-002: Canonical ledger lives outside the workspace, append-only   | 2026-09-24 | Status: Accepted (owner)

## Decision
The canonical store is an append-only event log at `~/.govdrift/threads/<thread-id>/events.jsonl`
(state = deterministic fold). The workspace gets only a read-only Markdown export on request.
Agent tools are denied write access to both (permission deny rules for Edit/Write + a PreToolUse
hook on Bash matching the store and export paths). Events are never edited or deleted;
corrupt tail lines are quarantined, not repaired.

## Alternatives considered
1. In-repo `.govdrift/` git-tracked — visible and shareable, but Addendum B showed 7/15 agents editing a governing file in reach (one `rm -f`'d it); deny rules don't reliably cover Bash side-effects.
2. Mutable JSON state file — simpler, but loses history, provenance, and the ability to prove who changed what.

## Tradeoffs
Gain: tamper resistance by construction, full provenance, replayable history. Give up: not in git by default; team sharing needs an explicit export (fine for v0 — single owner).

## Cost impact
None at runtime; a few KB per thread.

## Failure modes
Hook misses a creative Bash path → agent could still edit the store. Blast radius limited: append-only + hash chain (each event carries the previous event's hash) makes tampering detectable; `govdrift verify` reports it.

## Revisit trigger
Reopen when a team (≥ 2 owners) needs shared threads, or if any dogfood/eval run records a successful agent write to the store.
