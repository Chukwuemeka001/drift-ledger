# Changelog

## 0.1.0 — 2026-09-25
First release.
- Thread-scoped, append-only, hash-chained ledger outside the repo; owner-only authority for confirm/discharge/consume/supersede.
- Claude Code plugin: SessionStart/SubagentStart injection once per boundary; per-turn capture reminder with empty-ledger
  bootstrap; owner commands executed in the prompt hook; Stop gate for open obligations (must be stated as still owed);
  PreToolUse protection for the store, owner verbs and mechanical matchers.
- MCP server (stdlib): ledger_propose, ledger_attach_evidence, ledger_flag_conflict, ledger_status.
- Codex CLI support via `driftledger codex-setup` (same hook schema).
- `confirm … as <type>` retyping; provenance clause (claims from others can't discharge or lift anything).
