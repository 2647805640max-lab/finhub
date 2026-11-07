#!/usr/bin/env python3
"""Static smoke tests for the presentation-only FinHub UI v6 layer."""
from pathlib import Path
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
                       "完整性阻断", "不可判定（完整性阻断）", "完整性阻断，不展示旧金额", "决策完整性未通过"):
            self.assertIn(marker, self.index)
        for marker in ("decisionIntegrityFor", "age>1.5", "BLOCK · 不可决策",
                       "完整性阻断"):
            self.assertIn(marker, self.board)

    def test_theme_is_scoped_and_does_not_hide_data_by_default(self):
        self.assertIn('body.fh-v6', self.css)
        self.assertIn('[hidden]', self.index)
        self.assertIn('overflow-x:auto', self.css)

if __name__ == "__main__":
    unittest.main(verbosity=2)
