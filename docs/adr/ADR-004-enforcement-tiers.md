# ADR-004: Three enforcement tiers, all mechanical; the owner always wins   | 2026-09-24 | Status: Proposed

## Decision
1. **Inform** (all entries): the packet at every SessionStart (startup/resume/compact), banner v2
   semantics — summary is lossy, ledger governs HOW not WHETHER, flag once then proceed on owner
   confirmation.
2. **Gate completion** (obligations): Stop hook blocks *once* when the final message claims
   completion while an obligation is OPEN without evidence; loop guard prevents repeat blocks.
3. **Gate actions** (constraints with a mechanical matcher only — path glob, command prefix,
   network domain): PreToolUse denies matching calls with a reason citing the entry. Owner
   confirmation converts to a scoped exception.
No semantic judgment in code (H6): code never decides whether text "violates" a rule; the model
does, informed by the packet.

## Alternatives considered
1. Inform only — Tier 1 showed direct owner pressure beats the packet on share/package cells (6/15 held); a mechanical gate helps exactly there.
2. LLM-judge gate on every tool call — semantic parsing (H6), cost, latency, over-refusal risk.

## Tradeoffs
Gain: hard stops where they're cheap and exact; judgment stays with the model. Give up: rules without a mechanical matcher are only informed, never enforced.

## Cost impact
Stop/PreToolUse hooks: local, < 300 ms, zero tokens unless they block.

## Failure modes
Over-blocking → owner frustration/over-refusal (banner v1 deadlock). Mitigation: every block names the entry and the one-word way through; never block twice on the same obligation in a turn.

## Revisit trigger
Reopen if dogfood shows > 1 false block per day, or eval edge probes show any over-refusal.
