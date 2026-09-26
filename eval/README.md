# govdrift-eval

Behavioral evaluation of agent governance across context boundaries. Used for GovDrift Tier 2 / 2b / 2c.

```bash
python3 runner.py scenarios/nclex_remediation.json --out results/run1 --runs native:haiku:1,plugin:haiku:1 --kill 10
python3 codex_runner.py scenarios/nclex_remediation.json --out results/run2 --runs native:sol6:1,plugin:sol6:1
python3 score.py export results/run1 scenarios/nclex_remediation.json   # blinded bundles + judge prompt
python3 score.py report results/run1 scenarios/nclex_remediation.json   # after judge verdicts are written
```

- **Scenario files** script an owner (turns with ground-truth governing events), work to a context band, compactions,
  probes with a written pass rule each, a fresh session and a second harness.
- **Isolation:** each lineage gets an empty `CLAUDE_CONFIG_DIR` (login via `CLAUDE_CODE_OAUTH_TOKEN` in
  `~/.config/govdrift/eval.env`) or its own `CODEX_HOME`; its own git repo; native memory ON.
  **Put `--out` outside your home directory**: Claude Code loads `CLAUDE.md` files from the workspace's ancestors
  (including `~/.claude/CLAUDE.md`) regardless of `CLAUDE_CONFIG_DIR`. Our own runs got this wrong — see the GovDrift
  isolation erratum.
- **Arms:** `native`, `plugin` (careful owner confirms proposals with the intended type), `plugin-lazy` (owner stops
  confirming after a set turn).
- **Robustness:** every step is keyed and skipped on resume; any failure stops the run; spend is transcript-derived and
  deduplicated by message id (never sum `total_cost_usd` — it's cumulative for resumed sessions; Codex `--json` usage is
  cumulative per session too); hard kill switch.
- **Scoring:** blinded bundles (ledger styling stripped) for an LLM judge; machine checks (memory claims, ledger
  discharges, git remotes); per-lineage token economics.
