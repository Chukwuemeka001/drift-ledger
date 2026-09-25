# How Drift Ledger works

A tour of the moving parts. Enough to trust it and reason about it; the code is the full story.

## Threads

A ledger belongs to a **work thread**, not a chat session. By default a thread is bound to the project folder plus its
git branch, so every session you start there — new, resumed, compacted, or a subagent — attaches to the same ledger.
You can run several threads in one project (`/drift-ledger:thread new <name>`) when work streams shouldn't mix.

## Entries

Each entry is one piece of governing state, stored with the owner's own words:

| Type | Example |
|---|---|
| `mission` | "A local NCLEX-PN study-plan CLI." |
| `decision` | "Plain JSON files, no database" — *reason:* "I edit the journal on my phone." |
| `constraint` / `boundary` | "Python standard library only." / "Don't push this to GitHub." |
| `parked` | "No gamification until I say so." |
| `obligation` | "A nurse reviews every template before the study group sees it." |
| `exception` | "Just one streak counter" — a scoped, one-time lift of a parked entry. |

And each carries a **status** that changes over time — `PROPOSED`, `ACTIVE`, `DISCHARGED` (obligation done, by the
owner, with evidence), `CONSUMED` (exception used up — not a precedent), `SUPERSEDED` (by the owner, for a stated scope),
`REJECTED` — plus the session and turn that created or changed it.

## Who can do what

| Action | Agent | Owner |
|---|---|---|
| Propose an entry | ✅ (MCP tool or a `PROPOSE` line) | ✅ |
| Make it governing | — | ✅ `/drift-ledger:confirm` |
| Attach evidence to an obligation | ✅ | ✅ |
| Mark an obligation done | — | ✅ `/drift-ledger:discharge` |
| Lift / supersede / consume | — | ✅ |
| Edit or delete the store | — | (append-only for everyone) |

Owner commands are typed as ordinary prompts (`/drift-ledger:…`). They're executed in the **prompt hook**, which only
fires for text a human typed — never for the agent's own tool calls — and the command files themselves contain nothing
executable. The agent's attempts to run owner commands through the shell, or to touch the ledger store, are denied by a
pre-tool hook.

## Capture

The hard part of any record is getting things into it. In our tests, telling the agent once at session start what to
record captured **4 of 10** governing statements for a small model; a ~60-token reminder on every turn raised that to
**8 of 10**, with zero false proposals. So Drift Ledger reminds, every turn, briefly. When a thread's ledger is empty it
also asks the agent to propose the mission and constraints from your opening request — the one thing agents never
proposed on their own.

A proposal shows up as one line at the end of the agent's reply. You confirm with one command (and can fix the type:
`/drift-ledger:confirm L5 as obligation`).

## Boundaries

At every boundary the harness reports — session start, resume, compaction, subagent start — Drift Ledger injects a
compact **packet**: a short handoff notice plus the governing entries, ordered by what matters most when space is tight
(open obligations first, then boundaries and constraints, decisions, parked items, exceptions, recent history). It's
~1–2k tokens and injected **once per boundary**, not on every call. The agent's first line afterwards states the ledger
status, e.g. *"Ledger: 7 governing entries, 1 open obligation."*

The handoff notice matters as much as the entries. It tells the agent the summary it's reading is lossy testimony, that
the ledger governs *how* it acts on new instructions but not *whether* the owner may give them, to flag a conflict once
and then ask, and that notes or claims from anyone but the owner can't close or lift anything.

## Gates

Two deterministic gates, both deliberately narrow:

- **Completion gate.** If the agent tries to finish a turn by declaring the work done while an obligation is open, and
  doesn't state that obligation as still owed, the stop hook sends it back once to say so. (Loop-guarded; it never blocks
  twice.)
- **Action gate.** Entries can carry a mechanical matcher — a path glob or a command prefix. Matching tool calls are
  denied with the entry cited and the one command that lifts it.

Nothing in the code judges whether work "violates" a rule in general. That's the model's job, informed by the ledger;
code only enforces what it can check exactly.

## Storage and integrity

The ledger lives outside your repo (`~/.driftledger/threads/<thread>/events.jsonl`). It's an **append-only event log**:
every change is a new event, each hash-chained to the previous one; the current state is a deterministic fold over the
log. `driftledger verify` detects an edited or deleted event. Corrupt trailing bytes are quarantined, never repaired.
`driftledger export` writes a read-only Markdown view when you want one in the repo or for another tool.

## Harnesses

- **Claude Code:** a plugin — hooks (SessionStart, UserPromptSubmit, Stop, PreToolUse, PostCompact, SubagentStart),
  an MCP server with four agent-side tools, and owner commands.
- **Codex CLI:** the same hook script and MCP server; Codex's hook schema matches Claude Code's. `driftledger
  codex-setup` prints the config.
- **A second harness on the same thread** (for example Codex picking up work Claude started) reads the same ledger.

Everything is plain Python standard library. No network, no telemetry, no dependencies.
