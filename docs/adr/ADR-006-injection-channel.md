# ADR-006: Packet delivery channel at boundaries   | 2026-09-24 | Status: Accepted 2026-09-24 (SPIKE-A)

## Decision (pending)
Tier 1 proved the packet when **prepended to the first user message after compaction**. The
plugin's natural channel is **SessionStart(source=compact|resume|startup) → additionalContext**,
which may be framed/weighted differently by the model. Addendum B also showed the handoff framing
matters (same content via CLAUDE.md gave no gen-1 token saving). Choose the channel by measurement.

## Alternatives considered
1. SessionStart additionalContext (clean, official, automatic).
2. UserPromptSubmit on the first prompt after a boundary: prepend the packet to the prompt (closest to what Tier 1 tested; needs a "boundary pending" flag set at SessionStart).
3. Both (belt and braces) — double tokens.

## Tradeoffs
Gain (1): simplest, no prompt rewriting. Gain (2): replicates the proven condition exactly.

## Cost impact
~1.2–1.8k tokens per boundary either way.

## Failure modes
(1) underperforms (2) on lifecycle cells → we'd ship a weaker product than our evidence claims.

## Revisit trigger
SPIKE-A result: if (1) is within 1/5 of (2) on conflict + supersession cells across 5 seeds, use (1); otherwise use (2).

## Outcome (SPIKE-A)
Hook ≈ prepend within 1/5 on conflict (1 vs 2) and share (1 vs 2) → default = SessionStart additionalContext, once per session per boundary. `packet_channel=prepend` kept as a config switch. Both channels underperformed Tier 1 on the same fork (environment drift) — re-baseline in Phase 3.
