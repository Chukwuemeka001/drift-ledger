# ADR-003: Capture = agent proposes, owner confirms   | 2026-09-24 | Status: Accepted (owner); automation gated on SPIKE-B

## Decision
Only the owner commits governing entries. The agent proposes (MCP `ledger_propose`) when the owner
states a decision, constraint, obligation, exception or reversal; proposals appear as one line at
the end of the agent's reply and stay PROPOSED (visible but non-governing) until `/confirm`. The
owner can also write directly (`/decide`, `/forbid`, `/owe`, `/except`). No automatic extraction
engine (H6). A boundary "sweep" may later *suggest* missed entries as PROPOSED only.

## Alternatives considered
1. Owner-only commands — lowest risk, but capture depends on the owner remembering; misses decisions made mid-flow.
2. Auto-record with veto — lowest friction, but writes the agent's interpretations into the governing record (the self-certification drift seen in Addendum B).

## Tradeoffs
Gain: governing record stays owner-authored; agent does the noticing. Give up: a confirmation step (friction) and dependence on the agent noticing decisions.

## Cost impact
Proposal lines: ~30–80 tokens each; MCP call per proposal.

## Failure modes
(a) Agent under-proposes → capture rate low. (b) Owner ignores proposals → PROPOSED pile-up. (c) Agent paraphrases away the owner's words → store preserves the owner's quoted text separately from the agent's summary.

## Revisit trigger
Reopen if SPIKE-B/dogfood capture rate < 60% (add boundary sweep suggestions) or confirmations > 1 per 20 owner turns (add batch/auto-confirm for owner-typed slash commands only).

## Amendment (SPIKE-B, 2026-09-24)
A ~60-token UserPromptSubmit reminder every turn is REQUIRED (Haiku 4→8/10, Sonnet 7→8/10, 0 false proposals). New-thread bootstrap: when the ledger is empty, the reminder asks the agent to propose the mission and constraints from the opening request (never captured otherwise). Owner commands carry authority only via harness-executed `!` in plugin commands with `disable-model-invocation: true`, cross-checked against the UserPromptSubmit record of the owner's raw prompt (SPIKE-D).
