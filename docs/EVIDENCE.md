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

**Tier 2 — Claude Haiku and Sonnet (confirmatory, n=15 per arm).** With native memory ON: a fresh session knew what was
still owed **14/15 vs 3/15**, a second agent (Codex) saw the rules **13/15 vs 2/15**, and "don't push to GitHub" held after
two compactions **13/15 vs 6/15** — all three pre-registered primary effects, Holm-significant. The study was nevertheless
**NOT SUPPORTED as pre-registered**: our completion gate made small models refuse permitted work (6/15 vs 14/15). The gate
fired on any "Done." while an obligation was open and told the agent not to start new work; Haiku obeyed literally.

**Tier 2-fix.** We changed the gate (project-level claims only, once per obligation, "finish the request and add one line"),
pre-registered a re-test, and ran it: permitted work **5/6** (lazy owner **6/6**) vs native 5/6, with the gains intact
(fresh session 6/6 vs 0/6, GitHub boundary 6/6 vs 1/6).

**Tier 2b — GPT-6-Sol via Codex (n=10 per arm).** NOT SUPPORTED on its pre-registered primary cells (native Sol already
recovered the owed item in a fresh session 9/10, and Codex→Claude transfer through an exported file was weak). But inside
Codex the ledger changed Sol's behavior more than any other model's: native Sol built the parked leaderboard **10/10**
times (0/10 with the ledger), never cited the no-GitHub rule (10/10 with it), accepted the forged note 5/10 times (0/10
with it), with no over-refusal and **48% fewer output tokens**.

**Tier 2c — Claude Opus (descriptive, n=5), then to ~250k context.** Native Opus with memory passed almost everything —
including a forged "the owner approved publishing" note after a third compaction at 252–273k tokens. The ledger's one
clear contribution was carrying the rules to a second agent: **5/5 vs 0/5**.

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

- It doesn't make strong models much better inside a single harness — Opus with native memory is already there.
- Transfer into Claude Code from another harness through an exported file is weak; running the plugin in both harnesses is the supported path.

- It protects the **record**, not the agent's in-the-moment judgment: a convincing forged claim can still sway a weaker
  model for a turn. The next boundary restores the truth.
- It's not a hard interlock against the owner, and it won't enforce rules it can't check mechanically.
- Evidence so far is on one family of scenarios; more are coming through the eval harness in `eval/`.
