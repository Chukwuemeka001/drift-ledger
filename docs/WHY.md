# Why Drift Ledger exists

## The problem nobody sees until it bites

Coding agents now run for hours. They don't keep that whole history in view: when the context window fills, the harness
**compacts** it into a summary and carries on. Sessions end and resume. Work gets handed to a subagent, or to a
different agent entirely. Every one of those is a **boundary**, and whatever doesn't make it across simply stops existing
for the agent on the other side.

What gets lost is rarely the code — the code is on disk. What gets lost is the **governing state** the owner built up
in conversation:

- *"No databases — I want to be able to `cat` the log at 3am."* (a decision, with its reason)
- *"Never silently repair damaged records."* (a correction)
- *"No dashboards or exports until I say so."* (something parked)
- *"Before anyone sees this, a nurse has to review the wording."* (an obligation that is owed)
- *"Okay — just that one CSV export. Everything else stays parked."* (a one-time exception)
- *"Actually, I'm not sharing it this week."* (a walk-back)

After a boundary, agents rebuild the dashboard you parked, treat a one-time exception as a new rule, tell you "all done"
while the thing you're owed never happened, and — our favourite — accept a note from "a teammate" saying the review is
finished.

## Why pinning isn't enough

The obvious fix is to pin the rules somewhere the agent always sees them: a `CLAUDE.md`, a constraints file, the
harness's own memory. Recent research does exactly that and shows it helps for **static** constraints.

We tested that too (GovDrift Addendum B): the same rule text, verbatim, in a `CLAUDE.md` that's loaded on every turn.
It recovered most of the *recall* benefit. It did not recover the *lifecycle*:

- After a one-time exception, the static file still said "exports parked" — but not that the CSV lift was *one-time*.
  Agents reasoned "the CSV was fine, so the area's open" and built the dashboard. (5/15 flagged it vs 11/15 with a
  ledger that recorded the exception's scope.)
- **7 of 15 agents rewrote their own governing file.** Six marked the owed work "COMPLETE" on their own say-so. One
  deleted the file while tidying up.

Native memory has the same two weaknesses. It's excellent at capturing what you say — but it's written by the agent,
edited by the agent, and it lives in one harness. In our tests, a forged note got written into native memory as
"review complete", and the next fresh session believed it.

**Context engineering for long-running agents is a record-keeping problem, not a retention problem.**

## What we think the record needs

1. **Status, not just text** — active, owed, used up, superseded (by whom, for what scope).
2. **Owner authority** — agents may *propose*; only the owner makes something governing, marks it done, or lifts it.
3. **Provenance** — which session and turn created or changed each entry, so "someone said it was approved" can be checked.
4. **Delivery at every boundary** — compaction, resume, a brand-new session, a subagent, a second harness.
5. **Integrity** — append-only, tamper-evident, and out of the agent's reach.
6. **Proportion** — mostly invisible; a line per proposal, a line after a boundary, a flag when a request crosses a line.
   It must never turn into an agent that refuses to work.

Drift Ledger is that record, and nothing more. It sits *alongside* native memory: memory is a notebook; the ledger is
the signed agreement.

## Where it came from

Drift Ledger grew out of **GovDrift**, a public, pre-registered benchmark we built to test one question — *does a
small governance record survive context compaction better than the harness's own summary?* — and then kept testing
honestly, including the results that went against us. The story of those tests is in [EVIDENCE.md](EVIDENCE.md).
