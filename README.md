# Drift Ledger

**Your agent can't un-decide things — even after compaction, a new session, or a hand-off to another agent.**

Long-running coding agents lose governing state at context boundaries. Rules can be pinned (CLAUDE.md, native memory),
but real projects have state that *changes*: one-time exceptions get used up, obligations are owed until someone
actually does them, decisions get superseded for one request only. Pinned text doesn't carry that lifecycle — and
agent-written notes can be rewritten by the agent they're supposed to govern.

Drift Ledger keeps a small, **owner-confirmed** ledger per work thread and re-issues it at every boundary:

- **Agents propose, only you commit.** When you state a rule, decision, parked item, one-time exception or obligation,
  the agent proposes an entry; nothing governs until you confirm it.
- **Status and provenance on every entry** — ACTIVE, OBLIGATION owed, exception CONSUMED, SUPERSEDED (by whom, for
  what scope) — with the session and turn that created it.
- **Re-injected at every boundary** — after compaction, on resume, in a brand-new session, in subagents, and for a second
  harness (Claude Code ↔ Codex).
- **Append-only and tamper-evident**, stored outside your repo; the agent can't edit or delete it.
- **Hard gates where they're cheap and exact** — the agent can't mark an obligation done, can't run owner commands, and
  can't end a turn claiming "done" while something you're owed is open (it has to say so).

It works alongside native memory — it doesn't replace it.

## Evidence

Built on a public, pre-registered benchmark: **[GovDrift](https://github.com/Chukwuemeka001/GovDrift)**.

- Tier 1 (pre-registered): a governance packet re-issued at compaction beat native compaction on conflict surfacing
  (13/15 vs 2/15), scoped supersession (11/15 vs 0/15) and rules recall (13/15 vs 5/15), and was ~25% cheaper.
- Addendum B: the same rules in a static CLAUDE.md recovered recall but not lifecycle (scoped supersession 5/15 vs 11/15),
  and 7/15 agents rewrote their own CLAUDE.md (one deleted it).
- Exploratory eval slice with native memory ON (n=4/arm, blinded Opus judge): fresh-session truth 4/4 vs 1/4,
  second harness 4/4 vs 0/4, rule held after two compactions 4/4 vs 2/4; a forged "the review is done" note fooled the
  weaker model in-session in **both** arms (the ledger protects recorded state, not in-the-moment belief).
- Tier 2 (Claude Haiku/Sonnet), Tier 2b (GPT-6-Sol via Codex) and Tier 2c (Claude Opus): pre-registered, results in the
  GovDrift repo.

## How it works

```
You ──/drift-ledger:decide|forbid|park|owe|except|confirm──┐
                                                           ▼
Agent ──ledger_propose (MCP) ──▶ PROPOSED ──▶ ~/.driftledger/threads/<thread>/events.jsonl
                                              append-only · hash-chained · outside the repo
                                                  │ fold → current state
           ┌──────────────────────────────────────┼───────────────────────────┐
           ▼                                      ▼                           ▼
 SessionStart (startup/resume/compact)      Stop hook                   PreToolUse hook
 + SubagentStart: inject the ledger          can't claim "done" while   blocks owner-only commands, writes to the
 (~1.5k tokens, once per boundary)           an obligation is open      ledger store, and rules with a path/command matcher
```

The same hook script and MCP server serve Claude Code and Codex (their hook schemas match).

## Install

**Claude Code**

```
/plugin marketplace add Chukwuemeka001/drift-ledger
/plugin install drift-ledger@drift-ledger
```

**Codex CLI**

```bash
pip install git+https://github.com/Chukwuemeka001/drift-ledger
```

```bash
driftledger codex-setup
```

`codex-setup` prints the `~/.codex/hooks.json` and `config.toml` snippets (`--write` writes hooks.json and backs up any
existing file). Requires Python 3.10+ on macOS or Linux (Windows not yet supported), no dependencies.

## Use

Type these as ordinary prompts. They run in the prompt hook, which only fires for text you type — the agent can't
invoke them.

| Command | What it does |
|---|---|
| `/drift-ledger:decide <text> \| reason: <why>` | Record a decision |
| `/drift-ledger:forbid <text>` · `/drift-ledger:boundary <text>` | A rule / a hard line |
| `/drift-ledger:park <text>` | Park something until you say so |
| `/drift-ledger:owe <text>` | Something owed before you'll call it done |
| `/drift-ledger:except <id> <text> \| scope: <scope>` | One-time scoped exception to an entry |
| `/drift-ledger:confirm [ids…] [as <type>]` | Confirm the agent's proposals (optionally retype) |
| `/drift-ledger:reject <id>` · `/drift-ledger:discharge <id> [evidence]` · `/drift-ledger:consume <id>` · `/drift-ledger:supersede <id> [scope]` | Lifecycle |
| `/drift-ledger:ledger` | Show the governing ledger |
| `/drift-ledger:thread new\|use\|list [name]` | Work threads (default: one per project folder + git branch) |
| `/drift-ledger:off` · `/drift-ledger:on` | Kill switch |

The terminal CLI (`driftledger show | log <id> | verify | export`) reads the same store; `verify` checks the hash chain.

## What it is not

- Not a hard interlock against **you**: if your instruction conflicts with an entry, the agent flags it once and asks;
  you can always lift it.
- Not semantic enforcement: code never judges whether work "violates" a rule; the model does, informed by the ledger.
  Only mechanical matchers (paths, command prefixes) are blocked outright.
- Not proof against in-the-moment persuasion: a convincing forged note can still fool a weaker model in the turn it
  reads it. The record stays correct, and the next session recovers the truth.
- Single owner for now.

## Privacy

Everything is local. The ledger lives in `~/.driftledger/` (override with `DRIFTLEDGER_HOME`). Nothing is sent anywhere.

## Evaluate it yourself

`eval/` contains the harness used for the GovDrift tiers: scenario files with written rubrics, isolated runs (empty
config, token-only login), fail-stop/resumable steps, native-memory-ON baselines, Codex and Claude Code runners,
blinded judging and per-step token economics. See `eval/README.md`.

## License

MIT
