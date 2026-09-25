# ADR-005: Harness-agnostic core + thin adapters; Python stdlib   | 2026-09-24 | Status: Proposed

## Decision
- **Core** (`govdrift` package + CLI): event log, fold, packet renderer, exports, verify. Python 3.10+
  standard library only. No network.
- **MCP server** (stdio, hand-rolled minimal JSON-RPC, stdlib): exposes the agent's
  propose / request-discharge / flag tools to any MCP-capable harness.
- **Adapters** (each < 300 lines, H6): Claude Code plugin first (hooks.json + skills/commands +
  .mcp.json + settings deny rules); Codex hooks and a Hermes plugin (`on_session_start`,
  `pre_llm_call`, `pre_tool_call`, `subagent_start`) in v1 — installed by the user, never by
  editing an existing agent install.

## Alternatives considered
1. TypeScript/Node — native to Claude Code's ecosystem, but adds a runtime dependency for Hermes (Python) users and a build step.
2. Claude-Code-only plugin with logic in hook scripts — fastest v0, but locks the core to one harness; multi-harness use is the long game.

## Tradeoffs
Gain: one tested core across harnesses, zero deps, easy audit. Give up: hand-rolled MCP stdio (small, but ours to maintain).

## Cost impact
None.

## Failure modes
MCP protocol drift breaks the hand-rolled server → pin protocol version; contract tests; fall back to slash-command-only capture.

## Revisit trigger
Reopen if the MCP layer exceeds ~400 lines or breaks twice on harness upgrades (switch to an official SDK).
