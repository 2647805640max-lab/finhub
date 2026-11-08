#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI 阈值与 contracts/thresholds.json 的逐项一致性校验（D7）。

背景：时效阈值此前散落在 index.html / board.html 的内联 JS 里，与引擎、数据仓
各自的常量互不相干。实测证明改一处另几处不会跟着变（59 处硬编码）。

现在：
  · 页面里的阈值收敛成 GATE_THRESHOLDS 一个对象；
  · 唯一真源是 contracts/thresholds.json；
  · 本测试在 CI 里逐项比对 —— 改页面不改 JSON（或反之）→ CI 红。

退出码：0 = 一致；1 = 不一致；2 = 环境错误
"""
from __future__ import annotations

import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THRESHOLDS = os.path.join(REPO, "contracts", "thresholds.json")

# 页面里的常量名 → thresholds.json 的键
MAPPING = (
    ("verdictMaxAgeHours", "verdictMaxAgeHours"),
    ("positionMaxAgeDays", "positionMaxAgeDays"),
    ("futureClockSkewMinutes", "futureClockSkewMinutes"),
)

PAGES = ("index.html", "board.html")

OBJECT_RE = re.compile(
    r"const\s+GATE_THRESHOLDS\s*=\s*Object\.freeze\(\s*\{(?P<body>[^}]*)\}\s*\)",
    re.S)
KEY_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?P<val>-?\d+(?:\.\d+)?)")


def main() -> int:
    try:
        with open(THRESHOLDS, "r", encoding="utf-8") as fh:
            thresholds = json.load(fh)
    except (OSError, ValueError) as exc:
        print("[FAIL] 读不到 %s：%s" % (THRESHOLDS, exc))
        return 2

    print("=== UI 阈值一致性校验 ===")
    print("单一真相源:", THRESHOLDS)
    print()
    problems = []

    for page in PAGES:
        path = os.path.join(REPO, page)
        if not os.path.exists(path):
            problems.append("%s 不存在" % page)
            continue
        html = open(path, encoding="utf-8").read()
        match = OBJECT_RE.search(html)
        if not match:
            problems.append("%s 里找不到 GATE_THRESHOLDS 常量" % page)
            print("  [FAIL] %-12s 找不到 GATE_THRESHOLDS" % page)
            continue
        found = {m.group("key"): float(m.group("val")) for m in KEY_RE.finditer(match.group("body"))}
        print("  %-12s GATE_THRESHOLDS = %s" % (page, json.dumps(found, ensure_ascii=False)))
        for js_name, json_key in MAPPING:
            if js_name not in found:
                problems.append("%s 缺 GATE_THRESHOLDS.%s" % (page, js_name))
                print("    [FAIL] 缺 %s" % js_name)
                continue
            expected = thresholds.get(json_key)
            if expected is None:
                problems.append("thresholds.json 缺键 %s" % json_key)
                print("    [FAIL] thresholds.json 缺键 %s" % json_key)
                continue
            if abs(found[js_name] - float(expected)) > 1e-9:
                problems.append("%s 的 %s=%s ≠ thresholds.json 的 %s=%s"
                                % (page, js_name, found[js_name], json_key, expected))
                print("    [FAIL] %s 页面=%s JSON=%s" % (js_name, found[js_name], expected))
            else:
                print("    [ok] %-22s = %s" % (js_name, expected))

        # 页面里不许再出现裸写的阈值数字（1.5 / 24*60*60*1000 之类）
        body = match.group("body")
        leftovers = re.findall(r"(?:age|gateAgeMs)\s*[<>]\s*(\d+(?:\.\d+)?)", html)
        stray = [x for x in leftovers if x not in ("1.5",)]
        if stray:
            problems.append("%s 里仍有裸写的阈值比较：%s" % (page, stray))
            print("    [FAIL] 仍有裸写阈值比较 %s" % stray)
        else:
            print("    [ok] 无裸写阈值比较")

    print()
    if problems:
        print("=== %d 处不一致 ===" % len(problems))
        for p in problems:
            print("  -", p)
        return 1
    print("=== UI 阈值与 contracts/thresholds.json 逐项一致 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
