"""Contract tests for the Claude Code adapter, owner-command authority, and the MCP server.
Hook payload shapes are the ones recorded from Claude Code 2.1.280 in SPIKE-C."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(ROOT, "plugin")
sys.path.insert(0, PLUGIN)
from driftledger import model, threads  # noqa: E402
from driftledger.ledger import Ledger  # noqa: E402


class PluginBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.proj = tempfile.TemporaryDirectory()
        self.env = dict(os.environ, DRIFTLEDGER_HOME=self.tmp.name)
        os.environ["DRIFTLEDGER_HOME"] = self.tmp.name
        self.tid = threads.resolve(self.proj.name)
        self.L = Ledger(self.tid)

    def tearDown(self):
        self.tmp.cleanup(); self.proj.cleanup()

    def hook(self, event, **inp):
        inp.setdefault("cwd", self.proj.name); inp.setdefault("session_id", "s1"); inp["hook_event_name"] = event
        p = subprocess.run([sys.executable, os.path.join(PLUGIN, "hooks", "dl_hook.py"), event], input=json.dumps(inp),
                           capture_output=True, text=True, env=self.env, cwd=self.proj.name, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout) if p.stdout.strip() else None



class SessionStartTests(PluginBase):
    def seed(self):
        self.L.record("owner", "parked", "dashboards and exports")
        self.L.record("owner", "obligation", "corruption drill before showing anyone")

    def test_empty_ledger_injects_nothing(self):
        self.assertIsNone(self.hook("SessionStart", source="startup"))

    def test_inject_once_per_boundary(self):
        self.seed()
        out = self.hook("SessionStart", source="startup")
        self.assertIn("GOVERNING LEDGER", out["hookSpecificOutput"]["additionalContext"])
        self.assertIsNone(self.hook("SessionStart", source="resume"))           # headless resume: no duplicate
        out = self.hook("SessionStart", source="compact")                       # new boundary: inject again
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("just compacted", ctx); self.assertIn("1 open obligation", ctx)
        self.assertIsNone(self.hook("SessionStart", source="resume"))
        self.assertEqual(sum(1 for b in self.L.state().boundaries if b["source"] == "compact"), 1)

    def test_subagent_gets_packet(self):
        self.seed()
        out = self.hook("SubagentStart", agent_id="a1", agent_type="general-purpose")
        self.assertIn("subagent", out["hookSpecificOutput"]["additionalContext"])


class PromptAndStopTests(PluginBase):
    def test_reminder_and_bootstrap(self):
        ctx = self.hook("UserPromptSubmit", prompt="build me a CLI")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("PROPOSE", ctx); self.assertIn("EMPTY", ctx)
        self.L.record("owner", "mission", "a CLI")
        ctx = self.hook("UserPromptSubmit", prompt="next")["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("EMPTY", ctx)

    def test_owner_command_prompt_gets_no_reminder(self):
        self.assertIn("executed", self.hook("UserPromptSubmit", prompt="/drift-ledger:confirm L1")["hookSpecificOutput"]["additionalContext"])

    def test_propose_lines_recorded_as_proposed(self):
        msg = ('Done with storage.\n\nPROPOSE decision: "plain JSON files, no database" | reason: readable on my phone | scope: storage\n'
               '**PROPOSE parked: "no gamification for now"** | reason: distraction | scope: features')
        self.hook("Stop", last_assistant_message=msg, stop_hook_active=False)
        es = list(self.L.state().entries.values())
        self.assertEqual([e.type for e in es], ["decision", "parked"])
        self.assertTrue(all(e.status == model.PROPOSED for e in es))
        self.assertEqual(es[0].reason, "readable on my phone")

    def test_stop_gate_blocks_once_on_false_completion(self):
        o = self.L.record("owner", "obligation", "scope-of-practice review before showing the study group")
        # Tier-2 regression: task-level "Done." must never trigger the gate (it caused over-refusal of permitted work)
        self.assertIsNone(self.hook("Stop", last_assistant_message="Done. Added the repeat-topics section.", stop_hook_active=False))
        self.assertIsNone(self.hook("Stop", last_assistant_message="Renamed the header.", stop_hook_active=False))
        # project-level claim while an obligation is open: blocked once, and the reason never tells it to stop working
        out = self.hook("Stop", last_assistant_message="All done — ready to share with the group!", stop_hook_active=False)
        self.assertEqual(out["decision"], "block"); self.assertIn(o.id, out["reason"])
        self.assertNotIn("not start new work", out["reason"]); self.assertIn("Do not refuse", out["reason"])
        self.assertIsNone(self.hook("Stop", last_assistant_message="Ready to share.", stop_hook_active=True))   # loop guard
        self.assertIsNone(self.hook("Stop", last_assistant_message="Ready to share!", stop_hook_active=False))  # once per session
        # a different session gets its own single reminder; stating it as owed passes
        self.assertIsNone(self.hook("Stop", session_id="s2", last_assistant_message=f"Ready to share, but {o.id} is still owed.", stop_hook_active=False))
        out = self.hook("Stop", session_id="s3", last_assistant_message=f"{o.id} is an external gate, not a blocker — ready to ship.", stop_hook_active=False)
        self.assertEqual(out["decision"], "block")

    def test_export_for_other_harnesses(self):
        from driftledger.cli import export_markdown
        self.L.record("owner", "obligation", "nurse reviews templates before sharing")
        self.L.record("owner", "boundary", "never push to GitHub")
        self.L.record("agent", "decision", "maybe add badges")          # proposed: must not appear
        txt = export_markdown(self.L.state())
        self.assertLess(txt.index("Still owed"), txt.index("Hard boundaries"))
        self.assertIn("never push to GitHub", txt); self.assertNotIn("maybe add badges", txt)


class PreToolTests(PluginBase):
    def deny(self, out):
        return out and out["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_store_protected(self):
        store = self.tmp.name
        self.assertTrue(self.deny(self.hook("PreToolUse", tool_name="Bash", tool_input={"command": f"rm -rf {store}/threads"})))
        self.assertTrue(self.deny(self.hook("PreToolUse", tool_name="Write", tool_input={"file_path": f"{store}/threads/x/events.jsonl", "content": ""})))
        self.assertTrue(self.deny(self.hook("PreToolUse", tool_name="Bash", tool_input={"command": "driftledger confirm L1"})))
        self.assertTrue(self.deny(self.hook("PreToolUse", tool_name="Bash", tool_input={"command": "python3 -m driftledger --json discharge L2"})))
        self.assertTrue(self.deny(self.hook("PreToolUse", tool_name="SlashCommand", tool_input={"command": "/drift-ledger:confirm L1"})))
        self.assertFalse(self.deny(self.hook("PreToolUse", tool_name="Bash", tool_input={"command": "driftledger status"})))
        self.assertFalse(self.deny(self.hook("PreToolUse", tool_name="Bash", tool_input={"command": "pytest -q"})))

    def test_mechanical_matchers(self):
        self.L.record("owner", "boundary", "no packaging", matcher={"path_glob": "*pyproject.toml"})
        self.L.record("owner", "constraint", "never push", matcher={"cmd_prefix": "git push"})
        self.assertTrue(self.deny(self.hook("PreToolUse", tool_name="Write", tool_input={"file_path": f"{self.proj.name}/pyproject.toml"})))
        self.assertTrue(self.deny(self.hook("PreToolUse", tool_name="Bash", tool_input={"command": "git push origin main"})))
        self.assertFalse(self.deny(self.hook("PreToolUse", tool_name="Bash", tool_input={"command": "git status"})))


class OwnerAuthorityTests(PluginBase):
    def owner_types(self, text):
        out = self.hook("UserPromptSubmit", prompt=text)
        return out["hookSpecificOutput"]["additionalContext"] if out else ""

    def test_owner_typed_command_executes(self):
        out = self.owner_types("/drift-ledger:decide plain JSON, no database | reason: phone editor")
        self.assertIn("ACTIVE", out)
        e = self.L.state().entries["L1"]
        self.assertEqual((e.type, e.status, e.reason), ("decision", model.ACTIVE, "phone editor"))

    def test_command_files_contain_nothing_executable(self):
        import glob
        for f in glob.glob(os.path.join(PLUGIN, "commands", "*.md")):
            body = open(f).read()
            self.assertNotIn("!`", body, f); self.assertIn("disable-model-invocation: true", body, f)

    def test_agent_cannot_reach_owner_paths(self):
        self.L.record("agent", "constraint", "x")
        for cmd in ("python3 plugin/scripts/dl_owner.py confirm L1", "driftledger confirm L1"):
            out = self.hook("PreToolUse", tool_name="Bash", tool_input={"command": cmd})
            self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny", cmd)
        self.assertEqual(self.L.state().entries["L1"].status, model.PROPOSED)

    def test_exception_and_consume(self):
        self.owner_types("/drift-ledger:park dashboards and exports")
        self.assertIn("exception", self.owner_types("/drift-ledger:except L1 one CSV export of the log | scope: that command only"))
        self.owner_types("/drift-ledger:consume L2")
        st = self.L.state()
        self.assertEqual(st.entries["L2"].status, model.CONSUMED); self.assertTrue(st.entries["L1"].governing)

    def test_confirm_with_retype(self):
        self.L.record("agent", "parked", "nursing review before showing the study group")
        out = self.owner_types("/drift-ledger:confirm L1 as obligation")
        self.assertIn("ACTIVE as OBLIGATION", out)
        self.assertTrue(self.L.state().entries["L1"].open_obligation)

    def test_bad_command_reports_usage(self):
        self.assertIn("unknown Drift Ledger command", self.owner_types("/drift-ledger:frobnicate x"))


class McpTests(PluginBase):
    def rpc(self, *msgs):
        p = subprocess.run([sys.executable, os.path.join(PLUGIN, "mcp", "server.py")],
                           input="\n".join(json.dumps(m) for m in msgs) + "\n", capture_output=True, text=True,
                           env=dict(self.env, DRIFTLEDGER_CWD=self.proj.name), timeout=30)
        return [json.loads(x) for x in p.stdout.splitlines()]

    def test_protocol_and_tools(self):
        r = self.rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
                     {"jsonrpc": "2.0", "method": "notifications/initialized"},
                     {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                     {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "ledger_propose",
                      "arguments": {"type": "obligation", "text": "nursing review of templates", "reason": "PN scope"}}})
        self.assertEqual(r[0]["result"]["serverInfo"]["name"], "drift-ledger")
        self.assertEqual({t["name"] for t in r[1]["result"]["tools"]},
                         {"ledger_propose", "ledger_attach_evidence", "ledger_flag_conflict", "ledger_status"})
        self.assertIn("Proposed L1", r[2]["result"]["content"][0]["text"])
        self.assertEqual(self.L.state().entries["L1"].status, model.PROPOSED)

    def test_evidence_does_not_discharge(self):
        self.L.record("owner", "obligation", "drill")
        r = self.rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "ledger_attach_evidence",
                      "arguments": {"entry_id": "L1", "refs": ["pytest: 25 passed"]}}})
        self.assertIn("still ACTIVE", r[0]["result"]["content"][0]["text"])
        self.assertTrue(self.L.state().entries["L1"].open_obligation)


if __name__ == "__main__":
    unittest.main()
