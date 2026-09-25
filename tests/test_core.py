import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from driftledger import model, packet, threads
from driftledger.cli import main
from driftledger.ledger import Ledger, LedgerError


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["DRIFTLEDGER_HOME"] = self.tmp.name
        self.L = Ledger("t1")

    def tearDown(self):
        self.tmp.cleanup()


class StoreTests(Base):
    def test_append_read_verify(self):
        self.L.record("owner", "decision", "no databases", reason="cat at 3am")
        self.L.record("agent", "parked", "dashboards")
        v = self.L.store.verify()
        self.assertTrue(v["ok"]); self.assertEqual(v["events"], 2)

    def test_edit_detected(self):
        self.L.record("owner", "decision", "no databases")
        p = self.L.store.path
        s = open(p).read().replace("no databases", "use sqlite")
        open(p, "w").write(s)
        v = self.L.store.verify()
        self.assertFalse(v["ok"]); self.assertIn("hash mismatch", v["problems"][0]["problem"])

    def test_deletion_detected(self):
        for t in ("a", "b", "c"):
            self.L.record("owner", "decision", t)
        lines = open(self.L.store.path).readlines()
        open(self.L.store.path, "w").writelines([lines[0], lines[2]])
        self.assertTrue(any("chain break" in p["problem"] for p in self.L.store.verify()["problems"]))

    def test_corrupt_tail_quarantined_not_repaired(self):
        self.L.record("owner", "decision", "a")
        with open(self.L.store.path, "a") as fh:
            fh.write('{"kind": "record", torn')
        raw_before = open(self.L.store.path).read()
        r = self.L.store.read()
        self.assertEqual(len(r.events), 1); self.assertEqual(len(r.quarantined), 1)
        self.assertEqual(open(self.L.store.path).read(), raw_before)  # never repaired
        self.assertTrue(os.path.exists(self.L.store.quarantine_path))
        self.assertFalse(self.L.store.verify()["ok"])


class AuthorityTests(Base):
    def test_agent_proposes_only(self):
        e = self.L.record("agent", "constraint", "stdlib only")
        self.assertEqual(e.status, model.PROPOSED)
        self.assertFalse(e.governing)

    def test_owner_records_active(self):
        self.assertEqual(self.L.record("owner", "constraint", "stdlib only").status, model.ACTIVE)

    def test_agent_cannot_confirm_or_discharge(self):
        e = self.L.record("agent", "obligation", "run corruption drill")
        with self.assertRaises(LedgerError):
            self.L._do("confirm", "agent", e.id)
        self.L.confirm(e.id)
        with self.assertRaises(LedgerError):
            self.L._do("discharge", "agent", e.id)
        # agent can only attach evidence; status unchanged
        e2 = self.L.evidence("agent", e.id, refs=["pytest: 27 passed"])
        self.assertEqual(e2.status, model.ACTIVE)
        self.assertTrue(e2.open_obligation)

    def test_rejected_event_stays_in_log(self):
        e = self.L.record("owner", "decision", "x")
        with self.assertRaises(LedgerError):
            self.L._do("confirm", "owner", e.id)  # already ACTIVE
        self.assertEqual(len(self.L.store.read().events), 2)
        self.assertEqual(len(self.L.state().ignored), 1)

    def test_duplicate_proposal_deduped(self):
        a = self.L.record("agent", "parked", "Dashboards  parked")
        b = self.L.record("agent", "parked", "dashboards parked")
        self.assertEqual(a.id, b.id)
        self.assertEqual(len(self.L.state().entries), 1)


class LifecycleTests(Base):
    def test_exception_consumed_parent_governs(self):
        parked = self.L.record("owner", "parked", "dashboards, summary views, exports")
        ex = self.L.record("owner", "exception", "one CSV export of the depot log", parent=parked.id, scope="that one command")
        self.assertEqual(ex.status, model.ACTIVE)
        ex = self.L.consume(ex.id, note="built --export-csv")
        self.assertEqual(ex.status, model.CONSUMED)
        st = self.L.state()
        self.assertTrue(st.entries[parked.id].governing)
        txt = packet.render(st)
        self.assertIn("CONSUMED EXCEPTIONS (used up — NOT precedent)", txt)

    def test_exception_requires_parent(self):
        with self.assertRaises(LedgerError):
            self.L.record("owner", "exception", "orphan", parent="L99")

    def test_supersede_and_discharge(self):
        d = self.L.record("owner", "decision", "flat files")
        self.L.supersede(d.id, scope="move to sqlite for the archive only", note="owner changed mind")
        o = self.L.record("owner", "obligation", "corruption drill before showing anyone")
        self.L.discharge(o.id, refs=["test_corruption_drill.py: 27 passed"], note="owner reviewed")
        st = self.L.state()
        self.assertEqual(st.entries[d.id].status, model.SUPERSEDED)
        self.assertEqual(st.entries[o.id].status, model.DISCHARGED)
        self.assertFalse(any(e.open_obligation for e in st.entries.values()))


class PacketTests(Base):
    def _tier1_p1(self):
        L = self.L
        L.record("owner", "mission", "A local-only, deterministic gear-depot checkout planner with an append-only depot log that survives crashes and resumes safely. Reliability over features.")
        L.record("owner", "constraint", "Local-only. Python standard library only. No network. Append-only depot log. Restart recovery and failure behavior require tests.")
        L.record("owner", "decision", "No databases / no SQLite — storage stays flat files that can be opened and read directly.", reason="at 3am the owner wants to cat the log, not install tooling")
        L.record("owner", "constraint", "No silent repair of log bytes: damaged records are preserved or quarantined exactly as found.")
        L.record("owner", "parked", "Dashboards, summary views and export features — nothing until the owner says so.", scope="integrity/audit commands are NOT parked")
        L.record("owner", "obligation", "Full fixture-corruption drill: every fixture type corrupted several ways, surviving all of them — before the tool is shown to anyone.")
        L.record("owner", "boundary", "Do not package, publish, or make it release-ready (no setup.py/pyproject, no distribution work).")
        return L.state()

    def test_golden_tier1_content(self):
        st = self._tier1_p1()
        txt = packet.render(st, "compact")
        for e in st.entries.values():
            self.assertIn(e.text, txt)
        for clause in ("ledger governs", "testimony, not memory", "flag that entry ONCE", "never a terminal state",
                       "never claim something is recorded"):
            self.assertIn(clause, txt)
        self.assertLess(packet.tokens(txt), 1800)

    def test_priority_under_budget(self):
        st = self._tier1_p1()
        for i in range(40):
            self.L.record("owner", "decision", f"filler decision number {i} " + "x" * 120)
        txt = packet.render(self.L.state(), "compact", budget=1200)
        self.assertIn("Full fixture-corruption drill", txt)   # obligations first
        self.assertIn("Do not package", txt)                    # boundaries second
        self.assertIn("omitted for length", txt)
        self.assertLessEqual(packet.tokens(txt), 1300)

    def test_pending_not_governing(self):
        self.L.record("agent", "constraint", "maybe use pytest")
        txt = packet.render(self.L.state())
        self.assertIn("PENDING PROPOSALS (NOT governing", txt)


class ThreadAndCliTests(Base):
    def test_thread_binding_stable(self):
        with tempfile.TemporaryDirectory() as proj:
            a = threads.resolve(proj); b = threads.resolve(proj)
            self.assertEqual(a, b)
            c = threads.new_thread(proj, "second stream")
            self.assertEqual(threads.resolve(proj), c)

    def test_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as proj:
            out = io.StringIO()
            with redirect_stdout(out):
                main(["--cwd", proj, "decide", "no sqlite", "--reason", "cat at 3am"])
                main(["--cwd", proj, "propose", "parked", "dashboards"])
                main(["--cwd", proj, "confirm"])
                main(["--cwd", proj, "status"])
            self.assertIn("2 governing entries", out.getvalue())
            err = io.StringIO()
            with redirect_stderr(err), redirect_stdout(io.StringIO()):
                rc = main(["--cwd", proj, "discharge", "L1"])
            self.assertEqual(rc, 2); self.assertIn("not an open obligation", err.getvalue())


if __name__ == "__main__":
    unittest.main()
