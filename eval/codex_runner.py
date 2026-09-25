#!/usr/bin/env python3
"""govdrift-eval — Codex harness (Tier 2b: GPT-6-Sol as the main agent). Separate from the frozen Tier-2 runner.

  python3 codex_runner.py <scenario.json> --out <dir> --runs native:sol6:1,plugin:sol6:1,plugin-lazy:sol6:1

Same scenario, careful owner, band, probes and scoring as runner.py. Codex specifics (SPIKE-E):
- Each lineage has its OWN CODEX_HOME (Codex memory is a global per-home handbook): auth.json is a symlink to the
  isolated login at ~/.config/govdrift/codex-home (never read or copied), memories feature ON in every arm.
- Multi-turn: `codex exec resume <thread_id>`; stdin closed.
- Compaction: `/compact` doesn't work in exec, so a compact step is a checkpoint turn run with
  model_auto_compact_token_limit=1000, which forces a real auto-compaction (PreCompact/PostCompact, then
  SessionStart source=compact). A passive PostCompact logger (no output) runs in every arm to verify it happened.
- Drift Ledger for Codex = the SAME plugin hook script and MCP server, wired with per-run `-c` overrides.
- Second harness (X1) = Claude Code (Haiku, isolated token login) reading the folder; plugin arms get a
  read-only CLAUDE.md export of the ledger (Claude Code can't read Codex memory).
"""
import json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import runner  # noqa: E402

MODELS = {"sol6": "gpt-6-sol"}
AUTH = os.path.expanduser("~/.config/govdrift/codex-home/auth.json")
HOOK = os.path.join(runner.PLUGIN, "hooks", "dl_hook.py")
MCP = os.path.join(runner.PLUGIN, "mcp", "server.py")


class CodexLineage(runner.Lineage):
    def __init__(self, out, arm, model, seed, scenario):
        super().__init__(out, arm, model, seed, scenario)
        self.cxhome = os.path.join(self.base, "codexhome")
        if not os.path.exists(self.cxhome):
            os.makedirs(self.cxhome)
            os.symlink(AUTH, os.path.join(self.cxhome, "auth.json"))
            open(os.path.join(self.cxhome, "config.toml"), "w").write(
                f'model = "{MODELS[model]}"\n\n[features]\nmemories = true\n')
        self.st.setdefault("usage", [])

    # ---- codex plumbing ----
    def _overrides(self, compact_now=False):
        q = lambda s: s.replace('"', '\\"')
        mk = lambda ev, cmd: ["-c", f'hooks.{ev}=[{{hooks=[{{type="command",command="{q(cmd)}"}}]}}]']
        logger = os.path.join(self.base, "compaction_logger.py")
        if not os.path.exists(logger):
            open(logger, "w").write("import sys,json,time\nd=json.loads(sys.stdin.read() or '{}')\n"
                                    f"open({os.path.join(self.base, 'compaction_log.jsonl')!r},'a').write(json.dumps({{'t':time.time(),'trigger':d.get('trigger')}})+'\\n')\n")
        args = mk("PostCompact", f"python3 {logger}")
        if self.arm.startswith("plugin"):
            env = f"DRIFTLEDGER_HOME={self.home}"
            for ev in ("SessionStart", "UserPromptSubmit", "Stop", "PreToolUse", "SubagentStart"):
                args += mk(ev, f"{env} python3 {HOOK} {ev}")
            args += ["-c", 'mcp_servers.drift-ledger.command="python3"',
                     "-c", f'mcp_servers.drift-ledger.args=["{MCP}"]',
                     "-c", f'mcp_servers.drift-ledger.env={{DRIFTLEDGER_HOME="{self.home}",DRIFTLEDGER_CWD="{self.ws}"}}']
        if compact_now:
            args += ["-c", "model_auto_compact_token_limit=1000"]
        return args

    def claude(self, prompt, new_session=False):   # name kept for Run compatibility; this drives Codex
        key = "sid2" if new_session else "sid"
        compact_now = prompt.strip() == "/compact"
        text = "Context checkpoint. Reply with OK only." if compact_now else prompt
        cmd = ["codex", "exec"] + (["resume", self.st[key]] if self.st.get(key) else []) + [
            "--skip-git-repo-check", "--dangerously-bypass-hook-trust", "--dangerously-bypass-approvals-and-sandbox",
            "--json", "-m", MODELS[self.model]] + self._overrides(compact_now) + [text]
        env = dict(os.environ, CODEX_HOME=self.cxhome, DRIFTLEDGER_HOME=self.home)
        p = subprocess.run(cmd, cwd=self.ws, capture_output=True, text=True, timeout=3600, env=env, stdin=subprocess.DEVNULL)
        evs = [json.loads(l) for l in p.stdout.splitlines() if l.startswith("{")]
        tid = next((e.get("thread_id") for e in evs if e.get("thread_id")), None)
        usage = [e["usage"] for e in evs if e.get("type") == "turn.completed" and e.get("usage")]
        msgs = [e["item"].get("text", "") for e in evs if (e.get("item") or {}).get("type") == "agent_message"]
        if p.returncode or not usage:
            raise SystemExit(f"FAIL {self.id} rc={p.returncode} {p.stderr[-300:]}")
        self.st[key] = self.st.get(key) or tid
        info = self._token_info(self.st[key])        # SPIKE-E: --json usage is a CUMULATIVE session total
        self.st.setdefault("totals", {})[key] = info.get("total_token_usage") or usage[-1]
        self.st["_last_ctx"] = (info.get("last_token_usage") or {}).get("input_tokens", 0)
        return "\n\n".join(msgs)

    def _token_info(self, thread_id):
        """Latest token_count event from this thread's rollout file: true live context + cumulative totals."""
        import glob
        files = [f for f in glob.glob(os.path.join(self.cxhome, "sessions", "*", "*", "*", "*.jsonl")) if thread_id in f]
        info = {}
        for f in files:
            for line in open(f, errors="replace"):
                if '"token_count"' in line:
                    try: info = (json.loads(line).get("payload") or {}).get("info") or info
                    except ValueError: pass
        return info or {}

    def ctx(self):
        return self.st.get("_last_ctx", 0)

    def usage(self):
        for u in (self.st.get("totals") or {}).values():
            yield {"input_tokens": u.get("input_tokens", 0) - u.get("cached_input_tokens", 0),
                   "cache_read_input_tokens": u.get("cached_input_tokens", 0), "cache_creation_input_tokens": 0,
                   "output_tokens": u.get("output_tokens", 0) + u.get("reasoning_output_tokens", 0)}

    def spend(self):
        return 0.0   # ChatGPT-plan usage, not metered; tokens are reported instead

    def snapshot(self, label):
        dst = os.path.join(self.base, "snapshots", label); os.makedirs(dst, exist_ok=True)
        mem = os.path.join(self.cxhome, "memories")
        if os.path.isdir(mem): shutil.copytree(mem, os.path.join(dst, "memory"), dirs_exist_ok=True)
        agents = os.path.join(self.ws, "AGENTS.md")
        if os.path.exists(agents): shutil.copy(agents, os.path.join(dst, "workspace_AGENTS.md"))
        if self.arm.startswith("plugin"):
            L = self.ledger()
            if L.store.exists(): shutil.copy(L.store.path, os.path.join(dst, "ledger_events.jsonl"))


class CodexRun(runner.Run):
    def __init__(self, scenario_path, out, specs, kill):
        self.sc = json.load(open(scenario_path)); self.sc["_path"] = os.path.abspath(scenario_path)
        self.out, self.kill = os.path.abspath(out), kill
        self.lineages = [CodexLineage(self.out, *s, self.sc) for s in specs]

    def codex(self, L, step):
        """Second harness for Codex arms = Claude Code (Haiku, isolated), read-only question."""
        if step["id"] in L.st["log"]: return
        if L.arm.startswith("plugin"):
            from driftledger.cli import export_markdown
            open(os.path.join(L.ws, "CLAUDE.md"), "w").write(export_markdown(L.ledger().state()))
        cfg = os.path.join(L.base, "claude_x1_config"); os.makedirs(cfg, exist_ok=True)
        p = subprocess.run(["claude", "-p", step["text"], "--model", runner.MODELS["haiku"], "--permission-mode", "plan",
                            "--output-format", "json"], cwd=L.ws, capture_output=True, text=True, timeout=1800,
                           env=dict(os.environ, **runner.token_env(), CLAUDE_CONFIG_DIR=cfg))
        o = p.stdout; b = o.find("{")
        reply = json.loads(o[b:]).get("result", "") if b >= 0 else (o + p.stderr)[-2000:]
        L.st["log"][step["id"]] = {"prompt": step["text"], "reply": reply, "cell": step.get("cell"), "harness": "claude-code-haiku"}
        L.save(); print(f"{L.id} {step['id']} claude-code second harness done", flush=True)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario"); ap.add_argument("--out", required=True); ap.add_argument("--runs", required=True)
    a = ap.parse_args()
    specs = [(x.split(":")[0], x.split(":")[1], int(x.split(":")[2])) for x in a.runs.split(",")]
    R = CodexRun(a.scenario, a.out, specs, kill=float("inf"))
    for L in R.lineages:
        R.run_lineage(L)
    print("DONE (Codex usage is ChatGPT-plan, reported as tokens)")


if __name__ == "__main__":
    main()
