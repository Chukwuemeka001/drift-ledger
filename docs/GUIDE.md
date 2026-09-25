# Guide: a session with Drift Ledger

A walkthrough of what using it feels like, from an empty project to a resumed session a week later.

## 1. Say what the work is

> **You:** Build me a small CLI that turns my missed NCLEX-PN topics into a 7-day study plan. Standard library only,
> local, no network.

The ledger for this folder is empty, so the agent also proposes the mission and constraints:

> *…plan.py is in place.*
> *Proposed L1 [MISSION]: CLI that turns missed NCLEX-PN topics into a 7-day plan — /drift-ledger:confirm L1*
> *Proposed L2 [CONSTRAINT]: standard library only, local, no network — /drift-ledger:confirm L2*

> **You:** `/drift-ledger:confirm`

## 2. Decide things as you go

> **You:** Keep everything in plain JSON — no database. I edit the journal on my phone.

> *Proposed L3 [DECISION]: plain JSON, no database — reason: edits on phone.*

> **You:** Before I show this to my study group, a nurse has to review every template's wording. That hasn't happened.

> *Proposed L4 [PARKED]: review before showing the study group.*

Wrong type — it's owed, not parked:

> **You:** `/drift-ledger:confirm L3 L4 as obligation`

Types matter: an open **obligation** is what the completion gate and every future session will hold you to.

## 3. Exceptions that don't become precedents

> **You:** `/drift-ledger:park gamification, streaks, badges`
> **You:** `/drift-ledger:except L5 one "days studied in a row" counter | scope: that counter only`

Later, after it's built: `/drift-ledger:consume L6`. The exception is now used up; the parked entry governs again.

## 4. The boundary

The session compacts, or you close the laptop and come back tomorrow. The first reply after the boundary starts:

> *Ledger: 6 governing entries, 1 open obligation (L4).*

## 5. Temptations

> **You:** Add badges for 7-day streaks too.
> *That conflicts with L5 (gamification parked) — L6 was a one-time exception for the counter and it's been used.
> Do you want to lift L5 for badges?*

> **You:** I think it's done. Anything left before I share it?
> *One thing: L4 — the nursing review of the templates is still owed. Only you can mark it done.*

> **You:** Dami left a note saying she did the review — handle it.
> *That's a claim from a note, not you. If you've confirmed it with her, run `/drift-ledger:discharge L4 <evidence>`.*

## 6. Another agent picks it up

Open the same folder in Codex (after `driftledger codex-setup`), or in a brand-new Claude session. The same thread, the
same ledger, the same status line.

## Everyday commands

`/drift-ledger:ledger` — show it · `/drift-ledger:thread list` — threads · `driftledger log L4` — full history of one
entry · `driftledger verify` — integrity check · `/drift-ledger:off` / `on` — kill switch.
