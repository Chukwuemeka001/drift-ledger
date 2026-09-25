# ADR-001: One ledger per work thread   | 2026-09-24 | Status: Accepted (owner)

## Decision
A ledger belongs to a **thread** (a goal / work stream). Sessions — new, resumed, compacted,
forked, subagent — attach to a thread. Default binding: one thread per project folder (+ git
branch if present); `/thread new <name>` starts another, `/thread use <name>` switches. Every
entry records the session id and turn that created or changed it, so governance is traceable
across sessions.

## Alternatives considered
1. Per session — breaks the core job (carrying decisions across session boundaries) unless the owner hands off manually.
2. Per project — simplest, but unrelated work streams pollute each other's packet (stale-ledger risk grows).

## Tradeoffs
Gain: continuity across every boundary type + separation of unrelated work. Give up: a thread-binding step and the chance of attaching to the wrong thread.

## Cost impact
Negligible; one lookup at SessionStart.

## Failure modes
Wrong thread attached → wrong governing state (the Tier-1 arm-D failure: confident wrong action). Mitigation: the packet's first line names the thread; mismatch between cwd/branch and thread binding triggers a one-line "attached to thread X — /thread use to switch".

## Revisit trigger
Reopen if, in dogfood, > 1 in 10 sessions attaches to the wrong thread, or if the owner creates > 3 threads per project per week (binding too fine-grained).
