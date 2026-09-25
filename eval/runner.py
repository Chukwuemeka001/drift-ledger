#!/usr/bin/env python3
"""govdrift-eval runner — scenario-driven, isolated, resumable behavioral evaluation of agent governance.

  python3 runner.py <scenario.json> --out <dir> --runs native:haiku:1,plugin:haiku:1,... [--kill 40]

Isolation: every lineage runs with its own empty CLAUDE_CONFIG_DIR (login via CLAUDE_CODE_OAUTH_TOKEN loaded from
~/.config/govdrift/eval.env, never printed), its own git repo and its own ledger home — no owner-private context.
Native auto-memory stays ON (it lives in the lineage's config dir) — the realistic 2026 baseline.
Every step is keyed and skipped on resume; any failure stops the run (fail-stop); spend is transcript-derived,
deduplicated by message id, with a hard kill switch. Lessons D1–D5 + Dogfood 1/2 are built in.
"""
import argparse, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(os.path.dirname(HERE), "plugin")
sys.path.insert(0, PLUGIN)
MODELS = {"haiku": "claude-haiku-4-5-20251001", "sonnet": "claude-sonnet-5"}
PRICE = {"haiku": (1.0, 1.25, 0.10, 5.0), "sonnet": (3.0, 3.75, 0.30, 15.0)}   # $/M in, cache-w, cache-r, out
TOKEN_FILE = os.path.expanduser("~/.config/govdrift/eval.env")
slug = lambda p: re.sub(r"[^A-Za-z0-9]", "-", p)


def token_env():
    env = {}
    for line in open(TOKEN_FILE):
        k, _, v = line.strip().partition("=")
        if k: env[k] = v
    return env


class Lineage:
    def __init__(self, out, arm, model, seed, scenario):
        self.id = f"{arm}-{model}-s{seed}"; self.arm, self.model = arm, model
        self.base = os.path.join(out, "lineages", self.id)
        self.ws, self.home, self.cfg = (os.path.join(self.base, x) for x in ("proj", "ledger", "config"))
        self.state_path = os.path.join(self.base, "state.json")
        if not os.path.exists(self.state_path):
            for d in (self.ws, self.home, self.cfg): os.makedirs(d, exist_ok=True)
            seed_dir = os.path.join(os.path.dirname(scenario["_path"]), scenario["seed_dir"])
            shutil.copytree(seed_dir, os.path.join(self.ws, scenario.get("seed_as") or os.path.basename(seed_dir.rstrip("/"))))
            subprocess.run(["git", "init", "-q"], cwd=self.ws, check=True)
            self.st = {"sid": None, "sid2": None, "log": {}, "owner": []}; self.save()
        self.st = json.load(open(self.state_path))

    def save(self):
        json.dump(self.st, open(self.state_path + ".tmp", "w"), indent=1); os.replace(self.state_path + ".tmp", self.state_path)

    def transcripts(self):
        d = os.path.join(self.cfg, "projects", slug(os.path.realpath(self.ws)))
        return [os.path.join(d, f"{s}.jsonl") for s in (self.st.get("sid"), self.st.get("sid2")) if s]

    def usage(self):
        seen = set()
        for f in self.transcripts():
            if not os.path.exists(f): continue
            for line in open(f, errors="replace"):
                try: m = json.loads(line).get("message") or {}
                except ValueError: continue
                if m.get("usage") and m.get("role") == "assistant" and m.get("id") not in seen:
                    seen.add(m.get("id")); yield m["usage"]

    def spend(self):
        pi, pw, pr, po = PRICE[self.model]
        return sum(((u.get("input_tokens") or 0)*pi + (u.get("cache_creation_input_tokens") or 0)*pw
                    + (u.get("cache_read_input_tokens") or 0)*pr + (u.get("output_tokens") or 0)*po) / 1e6 for u in self.usage())

    def ctx(self):
        last = None
        for f in self.transcripts()[:1]:
            for line in open(f, errors="replace"):
                try: m = json.loads(line).get("message") or {}
                except ValueError: continue
                if m.get("usage") and m.get("role") == "assistant": last = m["usage"]
        return 0 if not last else sum(last.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))

    def claude(self, prompt, new_session=False):
        key = "sid2" if new_session else "sid"
        cmd = ["claude", "-p", prompt, "--model", MODELS[self.model], "--dangerously-skip-permissions", "--output-format", "json"]
        if self.arm.startswith("plugin"): cmd += ["--plugin-dir", PLUGIN]
        if self.st.get(key): cmd += ["--resume", self.st[key]]
        env = dict(os.environ, **token_env(), CLAUDE_CONFIG_DIR=self.cfg, DRIFTLEDGER_HOME=self.home)
        p = subprocess.run(cmd, cwd=self.ws, capture_output=True, text=True, timeout=3600, env=env)
        o = p.stdout; b = o.find("{")
        if p.returncode or b < 0: raise SystemExit(f"FAIL {self.id} rc={p.returncode} {p.stderr[-300:]}")
        d = json.loads(o[b:])
        if d.get("is_error"): raise SystemExit(f"FAIL {self.id} {str(d.get('result'))[:300]}")
        self.st[key] = d.get("session_id") or self.st.get(key)
        return d.get("result") or ""

    def ledger(self):
        sys.path.insert(0, PLUGIN); os.environ["DRIFTLEDGER_HOME"] = self.home
        from driftledger import threads; from driftledger.ledger import Ledger
        return Ledger(threads.resolve(self.ws))

    def snapshot(self, label):
        dst = os.path.join(self.base, "snapshots", label); os.makedirs(dst, exist_ok=True)
        mem = os.path.join(self.cfg, "projects", slug(os.path.realpath(self.ws)), "memory")
        if os.path.isdir(mem): shutil.copytree(mem, os.path.join(dst, "memory"), dirs_exist_ok=True)
        if self.arm.startswith("plugin"):
            L = self.ledger()
            if L.store.exists(): shutil.copy(L.store.path, os.path.join(dst, "ledger_events.jsonl"))


class Run:
    def __init__(self, scenario_path, out, specs, kill):
        self.sc = json.load(open(scenario_path)); self.sc["_path"] = os.path.abspath(scenario_path)
        self.out, self.kill = os.path.abspath(out), kill
        self.lineages = [Lineage(self.out, *s, self.sc) for s in specs]

    def total_spend(self): return sum(l.spend() for l in self.lineages)

    def step(self, L, key, prompt, new_session=False, meta=None):
        if key in L.st["log"]: return
        reply = L.claude(prompt, new_session)
        L.st["log"][key] = {"prompt": prompt, "reply": reply, "ctx": None if new_session else L.ctx(), **(meta or {})}
        L.save(); sp = self.total_spend()
        print(f"{L.id} {key} ctx={L.st['log'][key]['ctx']} spend=${sp:.2f}", flush=True)
        if sp >= self.kill: raise SystemExit(f"KILL SWITCH ${sp:.2f}")

    def careful_owner(self, L, step):
        """Owner reviews proposals made during their own turn: confirms those that are recognizably what they said,
        with the TYPE they meant (from the scenario's ground truth); leaves anything else pending."""
        if not L.arm.startswith("plugin") or f"{step['id']}:owner" in L.st["log"]: return
        if L.arm == "plugin-lazy" and step["id"] not in self.sc.get("lazy_owner_turns", []):
            L.st["owner"].append({"turn": step["id"], "actions": [], "lazy": True}); L.st["log"][f"{step['id']}:owner"] = True; L.save(); return
        from driftledger import model
        words = lambda t: set(re.findall(r"[a-z]{4,}", t.lower()))
        intended = [re.match(r"G\d+ ([a-z/]+)", g).group(1).split("/")[0] for g in step.get("governing", []) if re.match(r"G\d+ ([a-z/]+)", g)]
        typemap = {"correction": "constraint", "walk-back": None, "mission": "mission"}
        acts = []
        for e in [e for e in L.ledger().state().entries.values() if e.status == model.PROPOSED]:
            if len(words(e.text) & words(step["text"])) < max(2, len(words(e.text)) // 3) or not intended:
                continue
            want = typemap.get(intended[0], intended[0]) if len(intended) == 1 else None
            acts.append(f"/drift-ledger:confirm {e.id}" + (f" as {want}" if want and want != e.type and want in model.TYPES else ""))
        for a in acts: self.step(L, f"{step['id']}:{a.split()[1]}", a)
        L.st["owner"].append({"turn": step["id"], "actions": acts}); L.st["log"][f"{step['id']}:owner"] = True; L.save()

    def band(self, L, tag):
        if f"{tag}:done" in L.st["log"]: return
        for i, w in enumerate(self.sc["work_turns"][: self.sc["max_work_turns"]]):
            if L.ctx() >= self.sc["band_tokens"]: break
            self.step(L, f"{tag}:w{i}", w + " Reply with a concise progress report under 300 words.")
        L.st["log"][f"{tag}:done"] = {"ctx": L.ctx()}; L.save()

    def codex(self, L, step):
        if step["id"] in L.st["log"]: return
        if L.arm.startswith("plugin"):
            from driftledger.cli import export_markdown
            open(os.path.join(L.ws, "AGENTS.md"), "w").write(export_markdown(L.ledger().state()))
        p = subprocess.run(["codex", "exec", "--skip-git-repo-check", "-s", "read-only", step["text"]], cwd=L.ws,
                           capture_output=True, text=True, timeout=1800)
        L.st["log"][step["id"]] = {"prompt": step["text"], "reply": (p.stdout or "")[-4000:], "cell": step.get("cell")}
        L.save(); print(f"{L.id} {step['id']} codex done", flush=True)

    def run_lineage(self, L):
        for st in self.sc["steps"]:
            k = st["kind"]
            if k == "owner": self.step(L, st["id"], st["text"]); self.careful_owner(L, st)
            elif k == "band": L.snapshot(f"pre_{st['id']}"); self.band(L, st["id"])
            elif k == "compact": self.step(L, st["id"], "/compact"); L.snapshot(f"after_{st['id']}")
            elif k == "probe":
                if st.get("note") and not os.path.exists(os.path.join(L.ws, st["note"])):
                    open(os.path.join(L.ws, st["note"]), "w").write(st["note_text"])
                self.step(L, st["id"], st["text"], meta={"cell": st.get("cell")})
            elif k == "new_session": self.step(L, st["id"], st["text"], new_session=True, meta={"cell": st.get("cell")}); L.snapshot("after_new_session")
            elif k == "codex": self.codex(L, st)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario"); ap.add_argument("--out", required=True); ap.add_argument("--runs", required=True)
    ap.add_argument("--kill", type=float, default=40.0)
    a = ap.parse_args()
    specs = [(x.split(":")[0], x.split(":")[1], int(x.split(":")[2])) for x in a.runs.split(",")]
    R = Run(a.scenario, a.out, specs, a.kill)
    for L in R.lineages:
        R.run_lineage(L)
    print(f"DONE spend=${R.total_spend():.2f} (Claude, transcript-derived; Codex uncounted)")


if __name__ == "__main__":
    main()
