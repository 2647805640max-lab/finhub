#!/usr/bin/env python3
"""Static smoke tests for the presentation-only FinHub UI v6 layer."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]

class FinHubUiV6Smoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.board = (ROOT / "board.html").read_text(encoding="utf-8")
        cls.css = (ROOT / "ui-v6.css").read_text(encoding="utf-8")

    def test_both_entry_points_load_shared_theme(self):
        self.assertIn('href="ui-v6.css?v=2"', self.index)
        self.assertIn('href="ui-v6.css?v=2"', self.board)
        self.assertIn('<body class="fh-v6">', self.index)
        self.assertIn('<body class="fh-v6">', self.board)

    def test_existing_data_and_audit_mount_points_remain(self):
        for marker in ('id="app"', 'id="page-live"', 'id="page-hold"',
                       'id="page-gov"', 'id="s-audit"', 'id="govReloadBtn"',
                       'id="hsubmit"', 'id="actionbar"', 'id="devbar"'):
            self.assertIn(marker, self.index)
        for marker in ('board.json', 'chain', 'audit', 's-audit'):
            self.assertIn(marker, self.board)

    def test_responsive_and_accessibility_rules_exist(self):
        for marker in ('@media(max-width:767px)', '@media(min-width:1280px)',
                       '@media(prefers-reduced-motion:reduce)', ':focus-visible',
                       'minmax(0,1fr)'):
            self.assertIn(marker, self.css)

    def test_narrow_screen_status_and_decision_bars_wrap(self):
        for marker in ('#v5pills', 'grid-template-columns:repeat(2,minmax(0,1fr))',
                       'overflow-wrap:anywhere', 'white-space:normal',
                       '#actionbar', '@media(max-width:430px)'):
            self.assertIn(marker, self.css)

    def test_action_bar_is_structured_without_changing_decision_inputs(self):
        self.assertIn("action-summary", self.index)
        self.assertIn("action-evidence", self.index)
        self.assertIn("textContent=summary", self.index)
        self.assertIn("ev.slice(0,2)", self.index)
        self.assertIn(".actionbar-structured", self.css)
        self.assertIn("grid-template-columns:minmax(0,1fr)", self.css)

    def test_unverified_or_stale_decisions_fail_closed(self):
        for marker in ("decisionIntegrityFor", "gate.status!=='PASS'",
                       "gate.canRecommend!==true", "gate.checkedAt", "24*60*60*1000", "age>1.5",
                       "BLOCK · 不可决策", "当前不提供 HOLD / ADD / TRIM / EXIT 建议",
                       "完整性阻断", "不可判定（完整性阻断）", "完整性阻断，不展示旧金额",
                       "决策完整性未通过", "最近快照风险仓位"):
            self.assertIn(marker, self.index)
        for marker in ("decisionIntegrityFor", "age>1.5", "gate.checkedAt",
                       "BLOCK · 不可决策", "完整性阻断",
                       "不可判定（完整性阻断）", "完整性阻断，不展示旧金额"):
            self.assertIn(marker, self.board)

    def test_theme_is_scoped_and_does_not_hide_data_by_default(self):
        self.assertIn('body.fh-v6', self.css)
        self.assertIn('[hidden]', self.index)
        self.assertIn('overflow-x:auto', self.css)

    def test_decision_integrity_behaviour_suite_runs_in_ci(self):
        """The blocked-decision money gate is behavioural, so CI must EXECUTE it.

        The existing CI step only runs `python tests/ui-v6-smoke.py -v`; running
        the behaviour suite as a subprocess from here guarantees that step really
        executes it (index.html changes trigger the workflow).  Kept as a
        separate process so one suite crashing cannot hide the other, and the
        child's stdout/stderr are embedded in the failure message for CI.
        """
        script = Path(__file__).with_name("ui-integrity-behavior.py")
        proc = subprocess.run([sys.executable, str(script), "-v"],
                              capture_output=True, text=True, encoding="utf-8",
                              timeout=120)
        detail = ("exit=%d\n--- stdout ---\n%s\n--- stderr ---\n%s"
                  % (proc.returncode, proc.stdout, proc.stderr))
        self.assertEqual(
            proc.returncode, 0,
            "behaviour suite failed (tests/ui-integrity-behavior.py):\n" + detail)
        # unittest writes its verbose runner lines to stderr, so check both.
        output = (proc.stdout or "") + (proc.stderr or "")
        self.assertRegex(output, r"Ran \d+ tests", detail)
        self.assertIn("test_blocked_decision_hides_all_personal_amounts", output, detail)
        self.assertIn("... ok", output, detail)
        self.assertIn("OK", output, detail)
        # Echo the child runner lines into this CI step's log, so "the behaviour
        # suite actually ran" is visible in the job output, not just inferred.
        child_lines = [ln.strip() for ln in output.splitlines()
                       if ln.strip().startswith("test_") and "... ok" in ln]
        self.assertGreaterEqual(len(child_lines), 4,
                                "behaviour suite reported %d executed tests:\n%s"
                                % (len(child_lines), detail))
        for line in child_lines:
            print("[ui-integrity-behaviour] " + line)

if __name__ == "__main__":
    unittest.main(verbosity=2)
