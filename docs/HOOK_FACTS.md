# Hook facts — SPIKE-C results (Claude Code 2.1.280, headless `claude -p`, `--plugin-dir`), 2026-09-24
Measured with a throwaway logging plugin, not taken from docs. The research agent's doc summary was wrong on three points (marked ✗).

| Fact | Result |
|---|---|
| Plugin hooks run in `-p` mode with `--plugin-dir` | ✅ |
| SessionStart `source` values seen | `startup`, `resume`, `compact` |
| SessionStart `additionalContext` reaches the model | ✅ (model repeated the marker) |
| Injected context **persists in the transcript** | ✅ — and SessionStart fires on **every** `-p --resume` call, so naive injection accumulates duplicate packets → product must inject **once per boundary** (dedupe by session id + compaction count) |
| SessionStart after `/compact` has `source=compact` | ✅ |
| **PreCompact exists** (✗ research said no) | ✅ input: `trigger` (manual/auto), `custom_instructions`, `transcript_path` |
| PreCompact `additionalContext` changes the summary | ❌ (token not in summary) — don't rely on steering the compactor |
| **PostCompact exists** | ✅ input includes `compact_summary` (full summary text) → log it for audit / drift checks |
| Compaction runs as a subagent | SubagentStop fires during `/compact` |
| Stop input | `last_assistant_message`, **`stop_hook_active`** (✗ research said no loop guard), `background_tasks` |
| Stop `{"decision":"block","reason":…}` makes the agent continue | ✅ (reason is followed); second Stop has `stop_hook_active=true` |
| SubagentStart `additionalContext` reaches the subagent (✗ research said no mechanism) | ✅ subagent reported the marker |
| UserPromptSubmit input | `prompt`, `prompt_id`, `permission_mode` |
| Isolation for evals: `CLAUDE_CONFIG_DIR=<empty>` | Not logged in → needs `ANTHROPIC_API_KEY` or an OAuth token env (owner action) |
| `--setting-sources project,local` | Does **not** exclude the user's global CLAUDE.md |
| `total_cost_usd` in `-p` JSON | Cumulative for resumed sessions (documented) |

## Design consequences
1. FR7 injection = SessionStart hook with a per-session boundary counter; inject on `startup`, on `compact`, and on `resume` only if this session hasn't received the current boundary's packet.
2. FR8 Stop gate = `last_assistant_message` + open obligations; block once; respect `stop_hook_active`.
3. Subagent propagation (Phase 4) is cheap: SubagentStart → compact packet.
4. PostCompact `compact_summary` → store a hash + excerpt per boundary (audit trail; later: detect when the summary contradicts the ledger).
5. Eval isolation needs an owner-provided API key or `claude setup-token` token for a clean config dir.

## Codex CLI 0.156.0 (SPIKE-E, 2026-09-25) — gpt-6-sol
| Fact | Result |
|---|---|
| Hook events | PreToolUse, PermissionRequest, PostToolUse, PreCompact, PostCompact, SessionStart, SessionEnd, UserPromptSubmit, SubagentStart, SubagentStop, Stop, Interrupt — **same schema as Claude Code** |
| Per-run hooks without touching user config | ✅ `-c 'hooks.SessionStart=[{hooks=[{type="command",command="…"}]}]'` (PascalCase keys) + `--dangerously-bypass-hook-trust`; snake_case keys do nothing; project `.codex/hooks.json` needs a trusted project |
| Injection | ✅ SessionStart `additionalContext` reached the model (repeated marker) |
| Payloads | SessionStart `source` (startup/resume/compact); UserPromptSubmit `prompt`; PreToolUse `tool_name:"Bash"`, `tool_input`; Stop `last_assistant_message`, `stop_hook_active` — **dl_hook.py compatible as-is** |
| Multi-turn headless | ✅ `codex exec resume <thread_id> "<prompt>"`; stdin must be closed (else it hangs "reading additional input from stdin") |
| `/compact` in exec | ❌ sent as plain text |
| Forced compaction | ✅ `-c model_auto_compact_token_limit=<N>` → PreCompact/PostCompact(trigger=auto) → SessionStart(source=compact) |
| Owner commands | ✅ `/drift-ledger:…` prompt reaches UserPromptSubmit (the hook can execute it) |
| Side effect | Codex **auto-writes project trust entries** into ~/.codex/config.toml for folders it runs in (non read-only) — spike entries removed; backup at ~/.codex/config.toml.bak-driftledger-20260925 |
| Native memory | `memories` feature is OFF by default on the owner's install |
