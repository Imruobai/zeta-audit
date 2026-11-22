"""Docs must not quote a stale test count.

Twice now a doc claimed "5 checks" and "81 checks" while the suite ran 84. The cause is
always the same: a number in prose that only a human keeps in sync. So the number is
checked mechanically instead.

Authoritative source: the *last* `N/N checks passed` line printed by run_all.py. Earlier
lines come from child test scripts that print their own counts, which is exactly how the
first corruption happened.
"""

from __future__ import annotations

import pathlib
import re
import sys

# Windows consoles are not UTF-8 by default; this file prints non-ASCII text.
import _console  # noqa: F401  (side effect: force UTF-8 on stdout/stderr)

ROOT = pathlib.Path(__file__).resolve().parents[1]

DOCS = ["README.md", "README.zh-CN.md", "PAPER.md", "CONTRIBUTING.md",
        "docs/DESCRIPTION.md", "docs/LAUNCH_COPY.md", "docs/RELEASE_NOTES.md",
        "docs/PYPI_README.md"]


def suite_total() -> str | None:
    """The suite total, without re-running the suite.

    run_all.py exports ZETA_AUDIT_SUITE_TOTAL before calling this test. Re-running
    run_all.py here would recurse forever (run_all -> this test -> run_all), which is
    exactly what happened once. Standalone falls back to the env var only.
    """
    import os

    env = os.environ.get("ZETA_AUDIT_SUITE_TOTAL")
    if env and env.isdigit():
        return env
    return None


def main() -> int:
    total = suite_total()
    if total is None:
        print("[SKIP] ZETA_AUDIT_SUITE_TOTAL not set; run this via tests/run_all.py")
        return 0
    print(f"suite total: {total}\n")

    failures: list[str] = []
    for name in DOCS:
        f = ROOT / name
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        stale: list[int] = []
        for i, line in enumerate(text.splitlines(), 1):
            # "python tests/run_all.py   # 84 checks" / "# 84 项检查"
            m = re.search(r"run_all\.py\s*#\s*(\d+)\s*(?:checks|\u9879\u68c0\u67e5)", line)
            if m and m.group(1) != total:
                stale.append(i)
            # "N/N checks passed" anywhere
            m2 = re.search(r"\b(\d+)/\d+ checks passed", line)
            if m2 and m2.group(1) != total:
                stale.append(i)
        ok = not stale
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            failures.append(f"{name}: stale counts on lines {sorted(set(stale))}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  -", f)
        print(f"\nThe suite runs {total} checks; update those lines (the number is generated,"
              " so prefer pointing at the command over quoting a total).")
        return 1
    print("\nno stale test counts in docs")
    return 0


if __name__ == "__main__":
    sys.exit(main())