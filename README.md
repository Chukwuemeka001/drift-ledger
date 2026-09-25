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

## Documentation

- [Why Drift Ledger exists](docs/WHY.md) — the problem, why pinning isn't enough, what the record needs
- [How it works](docs/HOW_IT_WORKS.md) — threads, entries, authority, capture, boundaries, gates, storage
- [Evidence](docs/EVIDENCE.md) — how we test, what we found, what surprised us
- [Guide](docs/GUIDE.md) — a session from empty project to a resumed week later
- [FAQ](docs/FAQ.md)

## Evidence

Built and tested in public, with pre-registered studies and published nulls: **[GovDrift](https://github.com/Chukwuemeka001/GovDrift)**.
Every study runs agents through real compactions, then tempts them (the parked feature, a push to GitHub, "call it
done", a forged "the review is done" note), and scores what they **do**, blind.

**What the ledger reliably adds, across models (native memory ON in every comparison):**

| | Claude Haiku / Sonnet (n=15) | GPT-6-Sol via Codex (n=10) | Claude Opus (n=5, at ~250k context) |
|---|---|---|---|
| Fresh session knows what's still owed | **14/15** vs 3/15 | 10/10 vs 9/10 | 5/5 vs 5/5 |
| A second agent (Codex) sees the rules | **13/15** vs 2/15 | 1/10 vs 0/10 | **5/5** vs 0/5 |
| Holds "don't push to GitHub" after two compactions | **13/15** vs 6/15 | **10/10** vs 0/10 | 5/5 vs 5/5 |
| Doesn't build the parked feature | 15/15 vs 15/15 | **10/10** vs 0/10 | 5/5 vs 5/5 |
| Rejects a forged "review is done" note | 7/15 vs 3/15 | **10/10** vs 5/10 | 5/5 vs 5/5 |
| Output tokens | −13% | **−48%** | −4% to −21% |

**Honest verdicts.** The first confirmatory study (Claude) supported all three pre-registered primary effects but was
**NOT SUPPORTED as pre-registered**: our completion gate made small models over-refuse permitted work (6/15 vs 14/15).
We traced it, fixed it, pre-registered a re-test, and the over-refusal disappeared (5/6 and 6/6 vs native 5/6) while
the gains held. The Sol study was also NOT SUPPORTED on its pre-registered primary cells — its biggest effects landed
on cells we hadn't made primary. Both are published as specified.

**The pattern:** the stronger the model, the less it needs help *inside* one harness — Opus with native memory is
already excellent there. What doesn't shrink is **crossing boundaries**: a new agent, a different harness, a
compaction deep into a long session. That's where the ledger earns its keep.

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
- Not a substitute for keeping it current: only confirmed entries govern and transfer. If you stop confirming, later
  rules never reach another agent.
- Single owner for now.

## Privacy

Everything is local. The ledger lives in `~/.driftledger/` (override with `DRIFTLEDGER_HOME`). Nothing is sent anywhere.

## Evaluate it yourself

`eval/` contains the harness used for the GovDrift tiers: scenario files with written rubrics, isolated runs (empty
config, token-only login), fail-stop/resumable steps, native-memory-ON baselines, Codex and Claude Code runners,
blinded judging and per-step token economics. See `eval/README.md`.

## License

MIT
