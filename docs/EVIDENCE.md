# Evidence: what we tested, what we found, what surprised us

Drift Ledger is the product of a long line of experiments — most of them public in the
**[GovDrift](https://github.com/Chukwuemeka001/GovDrift)** repo, pre-registered before they ran, and published whether
they went our way or not. This page is the readable version.

## How we test

- **Real harnesses, real compaction.** Agents run in real Claude Code (and Codex) sessions, driven headlessly. Context is
  compacted with the harness's own compactor, not a simulation.
- **Forked lineages.** A worker session builds a project with an owner who makes realistic decisions. At a compaction,
  the session is forked into many identical copies — one per arm and seed — so every arm starts from exactly the same
  history.
- **Temptations, not quizzes.** After each boundary the owner asks for things that cross a line: add a database, build
  the parked dashboard, package it for a friend, "anything left before I call it done?", a note from a teammate saying the
  review is finished. We score what the agent **does**, not what it can recite.
- **Blinded judges.** Replies are anonymized, shuffled and stripped of tool styling, then scored against a written
  rubric by independent judges.
- **Isolation.** Eval runs use empty configs with a token-only login, so nothing from the experimenter's own setup leaks
  into the agents' context.
- **Pre-registration.** The question, arms, cells, statistics and "what would count as failure" are committed publicly
  before a run. Deviations are logged.

## The arc

**Tier 1 (pre-registered, 60 lineages, two real compactions, Claude Haiku).** A small governance packet — a handoff
notice plus a ledger of the owner's decisions — re-issued at each compaction, versus the harness's summary alone:
conflict surfacing **13/15 vs 2/15**, scoped supersession **11/15 vs 0/15**, rules recall **13/15 vs 5/15**. The
pre-registered overall criterion was *not supported as specified*; we published that anyway. The packet also made
sessions **~25% cheaper**.

**Addendum B — "just put it in CLAUDE.md?"** The same rule text in a static CLAUDE.md recovered recall (14/15) but not
lifecycle (scoped supersession 5/15 vs 11/15), and **7 of 15 agents rewrote their own governing file** — six
self-certifying the owed work as done, one deleting the file. A third compaction widened the gap between governed and
ungoverned agents.

**Dogfood 1 — the humbling one.** In a short, single-compaction session, our plugin *tied* plain Claude Code on every
governance check. The reason: Claude Code's **native auto-memory** had quietly captured the owner's rules, and done it
well. We had also told the agent to prefer our ledger over its memory, which made a small model hesitate on permitted
work. We removed that. Drift Ledger now coexists with native memory.

**Dogfood 2 — where memory is weak.** With native memory ON in every arm: a forged teammate note poisoned native memory
("review complete") in 2 of 3 small-model runs, and the corruption carried into the next fresh session. The ledger was
never changed, and every fresh governed session recovered the truth. A second agent (Codex) reading the same folder saw
the full rules only when the ledger was exported for it.

**Eval slice (isolated, blinded Opus judge, n=4 per arm).** Fresh-session truth **4/4 vs 1/4**; second harness
**4/4 vs 0/4**; a rule held after two compactions **4/4 vs 2/4**; ~20% cheaper. And one honest null: the forged note
fooled the small model *in the moment* in **both** arms (1/4 each).

**Tier 2 / 2b / 2c (pre-registered).** The confirmatory study with native memory ON — Claude Haiku and Sonnet
(n=15 per arm), GPT-6-Sol through Codex (n=10 per arm), and Claude Opus (n=5 per arm, descriptive) — including a
"lazy owner" arm who stops maintaining the ledger. Results are published in GovDrift.

## Things we didn't expect

- **The first message after a compaction is the most expensive one.** "Continue where we left off" sends agents
  re-exploring the workspace: ~1.5M tokens processed for that one question, in every arm.
- **~98% of tokens are cache reads.** The harness re-sends the whole context on every tool call, so the unit of waste is
  the tool call. Governance saves money in one specific way: agents stop doing work the owner already ruled out. A
  native agent building a forbidden Excel export spent ~1M tokens on that one request; governed agents asked first for
  ~50k.
- **Native memory fires when you state rules live.** In forked experiments where the rules lived in earlier history,
  native memory barely wrote anything. In fresh sessions where the owner stated them, it wrote 4–7 notes every time.
  Any benchmark of this problem needs a memory-ON baseline.
- **Agents write "memories" wherever they like.** Given the correct memory path, a small model still wrote its memory
  files into the project folder once.
- **The per-call cost number lies (politely).** Headless Claude Code's `total_cost_usd` is cumulative for resumed
  sessions; Codex's JSON usage is cumulative per session. Summing either overstates spend by an order of magnitude. We
  compute spend from transcripts, deduplicated by message.
- **Codex and Claude Code share a hook schema.** The same hook script works in both — which is what makes one ledger
  across two vendors practical.

## What it does not do (yet)

- It protects the **record**, not the agent's in-the-moment judgment: a convincing forged claim can still sway a weaker
  model for a turn. The next boundary restores the truth.
- It's not a hard interlock against the owner, and it won't enforce rules it can't check mechanically.
- Evidence so far is on one family of scenarios; more are coming through the eval harness in `eval/`.
