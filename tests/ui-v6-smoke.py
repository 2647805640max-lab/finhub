#!/usr/bin/env python3
"""FinHub UI tests: decision-integrity BEHAVIOUR + static smoke contracts.

Why both suites live in this single file
----------------------------------------
`.github/workflows/ui-v6-smoke.yml` triggers on `push` and `pull_request` with a
path filter, and `tests/ui-v6-smoke.py` is one of the paths it covers.  The
maintainer credential available for this repo is an OAuth app token scoped
`read:org, repo`; GitHub refuses it when it pushes or API-writes a file under
`.github/workflows/` ("refusing to allow an OAuth App to create or update
workflow ... without `workflow` scope"), so the workflow cannot be extended to
list another test path.  Keeping the behavioural suite inside this already
covered file is therefore what guarantees the tests run on BOTH `push` and
`pull_request`.  `tests/ui-integrity-behavior.py` remains a thin launcher that
selects this class and holds no assertion, so the two can never drift apart.

Behavioural part (what makes it a real test, not a string grep):
  * We do NOT search index.html for marker strings.  We extract the REAL inline
    JS render functions with brace matching, execute them in node against a
    minimal stub surface (money/escHtml/boardData/trimState/...), and assert on
    the HTML actually rendered for blocked / pass / stale / no-board fixtures.
  * Both directions are asserted: blocked output must contain no money at all,
    while pass output must still contain the same amounts and the trim ticket —
    otherwise "fixing" the leak by deleting the feature would still pass.

Static part: presentation-layer contracts (theme scoping, mount points,
responsive rules, fail-closed copy).

Run:  python tests/ui-v6-smoke.py -v
      python tests/ui-integrity-behavior.py -v   (behaviour class only)
"""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

# Comma-grouped money, e.g. 1,000,000 / 271,000 / -42,900.
MONEY_RE = re.compile(r"(?<![\d,])-?\d{1,3}(?:,\d{3})+(?![\d,])")

EXTRACT_NAMES = (
    "decisionIntegrityFor",
    "decisionBlockedNotice",
    "renderTrimPlan",
    "renderHoldingsCard",
    "renderDailySignalCard",
)


def inline_scripts(html):
    return re.findall(r"<script\b[^>]*>([\s\S]*?)</script>", html, flags=re.I)


def extract_function(source, name):
    """Extract `function <name>(...){...}` by brace matching.

    The scanner skips single/double quoted strings, template literals (including
    nested `${...}` expressions and nested templates) and comments, so braces
    that appear inside strings never end the function early.  That is what lets
    this test execute the shipped source instead of a hand-copied duplicate.
    """
    m = re.search(r"\bfunction\s+" + re.escape(name) + r"\s*\(", source)
    if not m:
        raise LookupError("function %s not found" % name)
    i = m.end() - 1  # position of '('
    depth = 0
    n = len(source)
    while i < n:
        ch = source[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                i += 1
                break
        i += 1
    while i < n and source[i] in " \t\r\n":
        i += 1
    if i >= n or source[i] != "{":
        raise LookupError("no function body for %s" % name)
    return source[m.start():_match_brace(source, i) + 1]


def _match_brace(source, start):
    depth = 0
    i = start
    n = len(source)
    state = "code"
    stack = []      # resumption state for template literals
    tpl_depth = []  # depth recorded when a ${ opened
    while i < n:
        c = source[i]
        if state == "code":
            if c == "'":
                state = "sq"
            elif c == '"':
                state = "dq"
            elif c == "`":
                stack.append("code")
                state = "tpl"
            elif c == "/" and i + 1 < n and source[i + 1] == "/":
                state = "lc"
                i += 1
            elif c == "/" and i + 1 < n and source[i + 1] == "*":
                state = "bc"
                i += 1
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if tpl_depth and depth == tpl_depth[-1] - 1:
                    tpl_depth.pop()
                    state = stack.pop()
                elif depth == 0:
                    return i
        elif state == "sq":
            if c == "\\":
                i += 1
            elif c == "'":
                state = "code"
        elif state == "dq":
            if c == "\\":
                i += 1
            elif c == '"':
                state = "code"
        elif state == "tpl":
            if c == "\\":
                i += 1
            elif c == "`":
                state = stack.pop()
            elif c == "$" and i + 1 < n and source[i + 1] == "{":
                depth += 1
                tpl_depth.append(depth)
                stack.append("tpl")
                state = "code"
                i += 1
        elif state == "lc":
            if c == "\n":
                state = "code"
        elif state == "bc":
            if c == "*" and i + 1 < n and source[i + 1] == "/":
                state = "code"
                i += 1
        i += 1
    raise LookupError("unbalanced braces while extracting function")


STUBS = r"""
'use strict';
var window = {};
var __board = null;
var __trim = {};
function boardData(){ return __board; }
function money(x){
  if(x==null || isNaN(x)) return '\u2014';
  var n = Math.round(Number(x));
  var neg = n < 0;
  n = Math.abs(n);
  var s = String(n), out = '';
  while(s.length > 3){ out = ',' + s.slice(-3) + out; s = s.slice(0, -3); }
  return (neg ? '-' : '') + s + out;
}
function escHtml(x){
  return String(x==null?'':x).replace(/[&<>"']/g, function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
  });
}
function num(v, d){ return v==null ? '\u2014' : Number(v).toFixed(d==null?2:d); }
function cls(v){ return v>0 ? 'up' : (v<0 ? 'dn' : 'fl'); }
function signedPct(v){ return (v>0?'+':'') + Number(v).toFixed(2) + '%'; }
function bar(lab, v, max, col){ return '<div class="bar">' + String(lab) + '</div>'; }
function trimStateGet(){ return JSON.parse(JSON.stringify(__trim)); }
function trimStateSet(v){ __trim = JSON.parse(JSON.stringify(v)); }
function nowIso(offsetMs){ return new Date(Date.now() + (offsetMs||0)).toISOString(); }
"""

FIXTURES = r"""
function fixtures(){
  var holdings = {
    asof:'2026-11-07 22:46', assets:1000000, totalPnl:123456, totalPnlPct:12.34,
    totalCash:50000, nPositions:2, costCoveragePct:100,
    platforms:[{platform:'支付宝', date:'2026-11-07', mv:950000, pnl:123456}],
    positions:[{name:'沪深300ETF', mv:600000, pnlPct:10.5, type:'ETF'},
               {name:'黄金ETF', mv:350000, pnlPct:2.1, type:'ETF'}]
  };
  var daily_signal = {
    date:'2026-11-07', builtAt:'2026-11-07T22:46:00+08:00',
    signal:{action:'TRIM', stage:'高潮', opportunity:30, risk:70, confidence:'中'},
    deviation:{total:1000000, risk:271000, riskPct:10.71, trimNeeded:271000},
    freshness:{incomplete:false}, checklist:['清单项']
  };
  var state = {generatedAt:'2026-11-07 22:46'};
  var freshPos = {currentPct:10.71, hardMaxPct:15, dataAgeDays:0.2};
  function board(status, canRecommend, message, pos){
    return {decisionIntegrity:{status:status, canRecommend:canRecommend,
              checkedAt:nowIso(-600000), message:message},
            today:{position:pos}, ips:{items:[]}};
  }
  return {
    blocked: {board:board('BLOCK', false, '上游完整性闸门未通过', freshPos),
              holdings:holdings, daily_signal:daily_signal, state:state},
    pass:    {board:board('PASS', true, 'PASS', freshPos),
              holdings:holdings, daily_signal:daily_signal, state:state},
    stale:   {board:board('PASS', true, 'PASS',
                          {currentPct:10.71, hardMaxPct:15, dataAgeDays:3.2}),
              holdings:holdings, daily_signal:daily_signal, state:state},
    noboard: {board:null, holdings:holdings, daily_signal:daily_signal, state:state}
  };
}
function safe(fn){
  try { return fn(); }
  catch(e){ return '<<ERROR: ' + (e && e.message ? e.message : String(e)) + '>>'; }
}
var fx = fixtures()[process.argv[2]];
__board = fx.board;
__trim = {};
var out = {
  trim:     safe(function(){ return renderTrimPlan(fx.holdings, fx.state); }),
  holdings: safe(function(){ return renderHoldingsCard(fx.holdings, fx.state); }),
  daily:    safe(function(){ return renderDailySignalCard(fx.daily_signal, fx.state); }),
  trimNeedSet: (function(){ var f = window.__trimNeed; return (f==null) ? 'unset' : 'set'; })()
};
process.stdout.write(JSON.stringify(out));
"""


class DecisionIntegrityBehaviour(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("node") is None:
            raise AssertionError("node executable is required to run the inline JS")
        html = INDEX.read_text(encoding="utf-8")
        scripts = inline_scripts(html)
        found = {}
        for name in EXTRACT_NAMES:
            for source in scripts:
                try:
                    found[name] = extract_function(source, name)
                    break
                except LookupError:
                    continue
        # Render entry points that must exist for the P0 fix; fail loudly instead
        # of silently passing when the gate is not implemented.
        for required in ("decisionIntegrityFor", "renderTrimPlan"):
            if required not in found:
                raise AssertionError(
                    "index.html is missing function %s; cannot test integrity behaviour" % required)
        cls.found = found
        cls._cache = {}
        cls._tmpdir = tempfile.mkdtemp(prefix="finhub-integrity-")
        harness = STUBS + "\n\n" + "\n\n".join(found[n] for n in EXTRACT_NAMES if n in found) \
            + "\n\n" + FIXTURES
        cls.harness = Path(cls._tmpdir) / "harness.js"
        cls.harness.write_text(harness, encoding="utf-8")
        # The extracted source must at least be syntactically valid on its own.
        check = subprocess.run(["node", "--check", str(cls.harness)],
                               capture_output=True, text=True, encoding="utf-8")
        if check.returncode != 0:
            raise AssertionError("extracted inline JS is not valid JS:\n" + check.stderr)

    def _scene(self, name):
        if name in self._cache:
            return self._cache[name]
        proc = subprocess.run(["node", str(self.harness), name],
                              capture_output=True, text=True, encoding="utf-8", timeout=60)
        if proc.returncode != 0:
            self.fail("node harness failed for scene %r (exit %d):\n%s\n%s"
                      % (name, proc.returncode, proc.stdout, proc.stderr))
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            self.fail("harness output for %r is not JSON: %s\n%r" % (name, exc, proc.stdout))
        self._cache[name] = out
        return out

    @staticmethod
    def _combined(out):
        return "\n".join(out[k] for k in ("trim", "holdings", "daily"))

    def assertNoRendererErrors(self, out, where):
        for key, value in out.items():
            if isinstance(value, str) and value.startswith("<<ERROR"):
                self.fail("%s: renderer crashed for field %r: %s" % (where, key, value))

    def assertNoMoney(self, out, where):
        combined = self._combined(out)
        for marker in ("1,000,000", "271,000", "需减", "调仓执行单", "已勾选"):
            self.assertNotIn(marker, combined,
                             "%s: blocked output still contains %r:\n%s" % (where, marker, combined))
        leaked = MONEY_RE.findall(combined)
        self.assertEqual(leaked, [],
                         "%s: blocked output still contains formatted amount(s) %r" % (where, leaked))

    def test_blocked_decision_hides_all_personal_amounts(self):
        out = self._scene("blocked")
        self.assertNoMoney(out, "blocked")
        self.assertIn("阻断", out["holdings"], out["holdings"])
        self.assertIn("阻断", out["daily"], out["daily"])
        self.assertIn("阻断", out["trim"], out["trim"])
        self.assertIn("⛔", out["holdings"])
        self.assertEqual(out["trimNeedSet"], "unset",
                         "blocked trim plan must not publish window.__trimNeed (stale amount)")
        self.assertNoRendererErrors(out, "blocked")

    def test_pass_decision_keeps_amounts_and_trim_ticket(self):
        out = self._scene("pass")
        self.assertIn("1,000,000", out["holdings"], out["holdings"])   # 总资产
        self.assertIn("总资产", out["holdings"])
        self.assertIn("调仓执行单", out["holdings"])                    # ticket still generated
        self.assertIn("需减", out["holdings"])
        self.assertIn("1,000,000", out["daily"], out["daily"])         # 总资产
        self.assertIn("271,000", out["daily"], out["daily"])           # 风险 / 需减
        self.assertIn("需减", out["daily"])
        self.assertIn("调仓执行单", out["trim"])
        self.assertNotIn("阻断", out["holdings"])
        self.assertNotIn("阻断", out["daily"])
        self.assertEqual(out["trimNeedSet"], "set",
                         "pass trim plan must publish window.__trimNeed for the checkbox footer")
        self.assertNoRendererErrors(out, "pass")

    def test_stale_snapshot_blocks_even_when_gate_says_pass(self):
        out = self._scene("stale")
        self.assertNoMoney(out, "stale")
        self.assertIn("36小时", out["holdings"], out["holdings"])
        self.assertIn("阻断", out["daily"], out["daily"])
        self.assertNoRendererErrors(out, "stale")

    def test_missing_board_fails_closed(self):
        out = self._scene("noboard")
        self.assertNoMoney(out, "noboard")
        self.assertIn("上游未提供决策完整性 PASS", out["holdings"], out["holdings"])
        self.assertIn("阻断", out["trim"], out["trim"])
        self.assertNoRendererErrors(out, "noboard")


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
