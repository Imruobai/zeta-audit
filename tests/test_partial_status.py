"""The verdict must be three-valued: a skipped check is not a pass.

Regression test for a real bug found by installing the built wheel into a clean venv
without mpmath: the CLI printed `ALL CHECKS PASSED` and exited 0 after skipping the
independent and windowed checks — the only two that can detect a *missing* zero. That
contradicted the README's own promise that "skipped" is not "passed".

The fix is `audit()` returning status in {passed, partial, failed}, and the CLI exiting 0
only for `passed`, 2 for `partial`, 1 for `failed`.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# Windows consoles are not UTF-8 by default; this file prints non-ASCII text.
import _console  # noqa: F401  (side effect: force UTF-8 on stdout/stderr)

from zeta_audit.audit_table import audit, load_table  # noqa: E402
from zeta_audit.crosscheck import HAS_MPMATH  # noqa: E402


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
    return ok


def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[1]
    table = root / "data" / "odlyzko_zeros1.txt"
    if not table.exists():
        print("[SKIP] reference table absent")
        return 0

    results = []
    r = audit(load_table(table))
    results.append(check("status field present", "status" in r, r.get("status", "")))
    results.append(check(
        "all_ok agrees with status == passed",
        r["all_ok"] == (r["status"] == "passed"),
        f"status={r['status']} all_ok={r['all_ok']}",
    ))
    results.append(check(
        "checks_skipped lists the environment-dependent checks",
        isinstance(r.get("checks_skipped"), list),
        str(r.get("checks_skipped")),
    ))

    # The environment here decides which branch is exercised; assert the invariant that
    # applies to it rather than assuming mpmath is present.
    if HAS_MPMATH:
        results.append(check("with mpmath: status is passed", r["status"] == "passed",
                             f"status={r['status']}"))
        code_expected = 0
    else:
        results.append(check("without mpmath: status is partial", r["status"] == "partial",
                             f"status={r['status']}"))
        results.append(check("without mpmath: skipped names the independent check",
                             "independent" in r["checks_skipped"],
                             str(r["checks_skipped"])))
        results.append(check("without mpmath: all_ok is False", r["all_ok"] is False,
                             f"all_ok={r['all_ok']}"))
        code_expected = 2

    # the CLI exit code must match the status
    with tempfile.TemporaryDirectory() as td:
        out = pathlib.Path(td) / "o.txt"
        proc = subprocess.run(
            [sys.executable, "-m", "zeta_audit.audit_table", str(table), "--quiet"],
            capture_output=True, text=True, cwd=root,
        )
        results.append(check(
            f"CLI exit code for this environment is {code_expected}",
            proc.returncode == code_expected,
            f"got {proc.returncode}",
        ))

    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())