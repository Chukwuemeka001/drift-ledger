# FAQ

**Why not just use CLAUDE.md / AGENTS.md?**
Use them — for general operating principles. They're static and agent-editable. In our tests the same rules in a static
CLAUDE.md held up for recall but not for anything that changes (a one-time exception, an obligation that's owed), and
7 of 15 agents rewrote the file. Drift Ledger is for the governing state of a piece of work, with its lifecycle.

**Doesn't Claude Code already have memory?**
Yes, and it's good at capture. Drift Ledger works alongside it. The differences: the ledger is owner-confirmed (the agent
can't promote its own conclusions), status-tracked, tamper-evident, re-issued at every boundary, and readable by other
harnesses. In our tests, native memory could be poisoned by a forged note and pass the poison to the next session; the
ledger couldn't.

**Will it make my agent refuse to do things?**
It's designed not to. The handoff notice tells the agent the ledger governs *how* it acts on your instructions, not
*whether* you may give them: flag a conflict once, ask, and then do what you decide. Permitted work adjacent to a rule
shouldn't be blocked, and we measure that in every eval.

**Does it cost tokens?**
The packet is ~1–2k tokens per boundary and the capture reminder ~60 tokens per turn. In our measurements governed
sessions were **cheaper** overall (~20–25%), because agents stopped doing work the owner had ruled out.

**What if I forget to confirm proposals?**
They stay visible as pending and never govern. The agent keeps working. We test this "lazy owner" case explicitly.

**Can the agent mark its own work as done?**
No. It can attach evidence to an obligation; only you can discharge it. Attempts to run owner commands or touch the
store are denied.

**Where's my data?**
In `~/.driftledger/` on your machine. No network calls, no telemetry. Set `DRIFTLEDGER_HOME` to move it.

**Does it work with Codex?**
Yes — Codex's hook schema matches Claude Code's; `driftledger codex-setup` prints the config. Other harnesses with
similar hooks are next.

**Teams?**
Single owner in v0.1. Shared threads are on the roadmap if people want them.

**Windows?**
Not yet (the store uses Unix file locking). macOS and Linux.

**How do I know the claims are real?**
Read the pre-registrations and raw results in [GovDrift](https://github.com/Chukwuemeka001/GovDrift), or run the eval
harness in `eval/` yourself.
