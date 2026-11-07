#!/usr/bin/env python3
"""Thin launcher: run only the decision-integrity behaviour suite.

The suite itself lives in `tests/ui-v6-smoke.py` — the file the CI path filter
covers — so any edit to the test logic triggers the workflow on push and
pull_request.  This launcher deliberately contains no assertion: it just selects
the class out of the covered module, which is why the two cannot drift apart.

Run:  python tests/ui-integrity-behavior.py -v
"""
import subprocess
import sys
from pathlib import Path

TARGET = Path(__file__).with_name("ui-v6-smoke.py")
if __name__ == "__main__":
    raise SystemExit(subprocess.call(
        [sys.executable, str(TARGET), "DecisionIntegrityBehaviour"] + sys.argv[1:]))
