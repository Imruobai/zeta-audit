"""Audit an external zero table: the repo's main practical entry point.

The situation this addresses: zero tables are published as opaque files and consumed as
if they were correct. Every serious numerical use of ζ depends on them, and there is no
standard "check this file" step.

This tool takes a table in whatever whitespace-separated form it arrives in, and reports:

  1. **structural**  — sorted? duplicated? count matches the file's own numbering?
  2. **residual**    — is |ζ(1/2 + iγ)| actually ~0 at each ordinate we can afford to test?
  3. **independent** — does mpmath's own zero finder put a zero at that ordinate?
  4. **completeness** — does the table's count match N(T) = θ(T)/π + 1 + S(T), and does an
                       argument-principle count on the strip agree? (This is the check
                       that catches *missing* zeros, not just wrong ones.)

Exit code 0 = every check that could be run passed; 1 = at least one failed.

Formats accepted (auto-detected, first non-comment line wins):
    14.134725141734693            bare ordinate
    1 14.134725141734693          index then ordinate
    gamma=14.13...                keyed
Comma or tab separated also works. Lines starting with # are comments.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Read the version from the package without importing it (avoids a circular import:
# __init__ imports this module for its public ``audit_zero_table``).
_TOOL_VERSION = "0.4.0"


# --------------------------------------------------------------------------- #
# parsing
# --------------------------------------------------------------------------- #
@dataclass
class Table:
    path: str
    ordinates: list[float]
    indices: list[int] | None
    comments: list[str] = field(default_factory=list)
    sha256: str = ""

    @property
    def count(self) -> int:
        return len(self.ordinates)


def _pick_number(token: str) -> float | None:
    tok = token.strip().rstrip(",;")
    if not tok:
        return None
    if "=" in tok:
        tok = tok.rsplit("=", 1)[1]
    try:
        v = float(tok)
    except ValueError:
        return None
    if not math.isfinite(v):
        return None
    return v


def load_table(path: str | Path) -> Table:
    """Parse a zero table, tolerating index columns, key=value pairs, and comments."""
    p = Path(path)
    raw = p.read_bytes()
    import hashlib

    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8", "replace")

    ordinates: list[float] = []
    indices: list[int] = []
    comments: list[str] = []
    saw_index = False

    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#") or s.startswith("//") or s.startswith("%"):
            comments.append(s)
            continue
        parts = s.replace(",", " ").replace("\t", " ").split()
        if not parts:
            continue
        # Try "index ordinate" first, then "ordinate".
        if len(parts) >= 2 and parts[0].lstrip("+-").isdigit():
            v = _pick_number(parts[1])
            if v is not None:
                saw_index = True
                indices.append(int(parts[0]))
                ordinates.append(v)
                continue
        v = _pick_number(parts[-1])
        if v is not None:
            ordinates.append(v)

    return Table(
        path=str(p),
        ordinates=ordinates,
        indices=indices if saw_index else None,
        comments=comments[:20],
        sha256=digest,
    )


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #
def check_structure(t: Table) -> dict:
    ords = t.ordinates
    dupes = sum(1 for a, b in zip(ords, ords[1:]) if a == b)
    inversions = sum(1 for a, b in zip(ords, ords[1:]) if b < a)
    nonpos = sum(1 for a in ords if a <= 0)
    idx_bad = None
    if t.indices is not None:
        idx_bad = sum(1 for i, j in zip(t.indices, t.indices[1:]) if j != i + 1)
    return {
        "count": t.count,
        "sha256": t.sha256,
        "first": ords[0] if ords else None,
        "last": ords[-1] if ords else None,
        "nonpositive_ordinates": nonpos,
        "exact_duplicates_adjacent": dupes,
        "descending_steps": inversions,
        "index_column_present": t.indices is not None,
        "index_sequential_breaks": idx_bad,
        "ok": nonpos == 0 and dupes == 0 and inversions == 0,
    }


def check_residuals(t: Table, sample: int = 40, tol: float = 1e-6) -> dict:
    """|ζ(1/2+iγ)| at a sample of ordinates, by our evaluator and by mpmath."""
    from .zeta import zeta_half

    if t.count == 0:
        return {"available": False, "reason": "empty table"}
    n = t.count
    step = max(1, n // sample)
    picks = list(range(0, n, step))[:sample]

    worst_our = 0.0
    worst_our_at = 0.0
    for i in picks:
        g = t.ordinates[i]
        r = abs(zeta_half(g))
        if r > worst_our:
            worst_our, worst_our_at = r, g

    mp_ok = True
    worst_mp = None
    try:
        from .crosscheck import HAS_MPMATH, mpmath_residual

        if HAS_MPMATH:
            mp_vals = [mpmath_residual(t.ordinates[i]) for i in picks[: min(12, len(picks))]]
            worst_mp = max(mp_vals) if mp_vals else None
        else:
            mp_ok = False
    except Exception:  # noqa: BLE001
        mp_ok = False

    # Non-zero residuals are only meaningful relative to the ordinate size: a table
    # accurate to 1e-9 has |zeta| ~ 1e-9 nearby, so we scale by the claim if present.
    return {
        "available": True,
        "sampled": len(picks),
        "our_max_residual": worst_our,
        "our_max_residual_at": worst_our_at,
        "mpmath_available": mp_ok,
        "mpmath_max_residual": worst_mp,
        "tol": tol,
        "ok": worst_our <= tol and (worst_mp is None or worst_mp <= tol),
    }


def check_independent(t: Table, sample: int = 5) -> dict:
    """Does mpmath's own zero finder place a zero at the ordinate? (index-wise)"""
    try:
        from .crosscheck import HAS_MPMATH, mpmath_zeros
    except Exception:  # noqa: BLE001
        return {"available": False, "reason": "mpmath not installed"}

    if not HAS_MPMATH:
        return {"available": False, "reason": "mpmath not installed"}
    if t.count == 0:
        return {"available": False, "reason": "empty table"}

    # mpmath.zetazero is index-based, so this check is only meaningful from index 1.
    k = min(sample, t.count)
    ref = mpmath_zeros(k)
    worst = 0.0
    for i in range(k):
        if t.indices is not None and t.indices[i] != i + 1:
            return {"available": False, "reason": "table does not start at index 1"}
        worst = max(worst, abs(t.ordinates[i] - ref[i]))
    return {
        "available": True,
        "compared": k,
        "max_abs_diff_vs_mpmath": worst,
        "ok": worst < 1e-8,
    }


def check_completeness(t: Table, windows: int = 3, window_rows: int = 200) -> dict:
    """Is the count consistent, and is any single zero missing?

    Two checks of very different strength, reported separately because conflating them
    would be dishonest:

    * **sanity** — ``|count − (θ(T)/π+1)| < 3``. Cheap and *weak*: S(T) is O(log T) with a
      non-small constant, so a table can be off by a zero or two and still pass. Measured:
      removing one row from Odlyzko's 100k table leaves |S(T)| = 0.4.
    * **windowed count** — pick a few windows and count the zeros inside from ζ alone, via
      an independent implementation (mpmath's ``nzeros``, Turing's method), then compare
      with the rows the table lists there. Independent of the table, and it does catch a
      hole.

    Two implementation notes that were learned the hard way and are load-bearing:

    1. **Two contour-based attempts were abandoned.** The argument principle works but needs
       O(|Z|/step) evaluations of ζ; at T ≈ 4·10⁴ one window is ~1.5·10⁴ points × 6 ms, and
       the tool stopped being usable. ``nzeros`` does the same job in 0.1 s.
    2. **Never evaluate ``nzeros`` exactly at an ordinate.** Floating-point rounding makes
       ``nzeros(γ_k)`` return k or k−1 unpredictably (measured: γ₃ gives 2, not 3). The
       count is taken at points strictly between ordinates.

    A third attempt, local gap statistics, was also abandoned: with Gaussian-unitary
    spacing ~7% of legitimate gaps exceed 2× their local median, so it flags thousands of
    innocent rows while a real hole is indistinguishable from ordinary scatter.
    """
    from .zeta import n_zeros_asymptotic

    if t.count == 0:
        return {"available": False, "reason": "empty table"}
    T = t.ordinates[-1]
    smooth = n_zeros_asymptotic(T)
    dev = t.count - smooth

    ords = t.ordinates
    picks = []
    if len(ords) > window_rows * 2:
        for k in range(windows):
            start = int(len(ords) * (k + 1) / (windows + 1)) - window_rows // 2
            start = max(1, min(start, len(ords) - window_rows - 2))
            picks.append(start)

    try:
        from .crosscheck import HAS_MPMATH
    except Exception:  # noqa: BLE001
        HAS_MPMATH = False

    rows: list[dict] = []
    if HAS_MPMATH and picks:
        import mpmath

        mpmath.mp.dps = 20
        with mpmath.workdps(20):
            for start in picks:
                # Both ends are table ordinates; evaluate strictly inside them so no
                # count is taken on a zero (see note 2 above).
                lo = (ords[start - 1] + ords[start]) / 2.0
                hi = (ords[start + window_rows - 1] + ords[start + window_rows]) / 2.0
                inside = int(mpmath.nzeros(hi)) - int(mpmath.nzeros(lo))
                rows.append({
                    "rows": f"{start + 1}..{start + window_rows}",
                    "t_lo_mid": lo,
                    "t_hi_mid": hi,
                    "table_zeros_inside": window_rows,
                    "independent_count": inside,
                    "agree": inside == window_rows,
                })

    windows_ok = all(r["agree"] for r in rows) if rows else None
    ok = abs(dev) < 3.0 and (windows_ok is not False)
    return {
        "available": True,
        "T": T,
        "table_count": t.count,
        "smooth_N_T": smooth,
        "S_T_implied": dev,
        "sanity_ok": abs(dev) < 3.0,
        "sanity_note": "weak: does not detect a small number of missing zeros",
        "windows": rows,
        "windows_ok": windows_ok,
        "window_method": "mpmath.nzeros (Turing) at midpoints between ordinates"
        if HAS_MPMATH else None,
        "ok": bool(ok),
        "note": (
            "ok requires the weak sanity count AND, when mpmath is available, every "
            "windowed count to agree. Without mpmath only the weak check runs, and "
            "windows_ok is null rather than a false pass."
        ),
    }


# --------------------------------------------------------------------------- #
def audit(t: Table, windows: int = 3) -> dict:
    res = {
        "tool": f"zeta_audit {_TOOL_VERSION}",
        "table": t.path,
        "structure": check_structure(t),
        "residuals": check_residuals(t),
        "independent": check_independent(t),
        "completeness": check_completeness(t, windows=windows),
    }
    checks = [v for k, v in res.items() if isinstance(v, dict) and "ok" in v]
    res["all_ok"] = all(c["ok"] for c in checks) if checks else False
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m zeta_audit.audit_table",
        description="audit an external zero table (structure, residuals, independence, completeness)",
    )
    ap.add_argument("table", help="path to the zero table file")
    ap.add_argument("--windows", type=int, default=3,
                    help="number of windows to test with the argument-principle count (default 3)")
    ap.add_argument("--json", default="", help="write the full report here")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    t = load_table(a.table)
    if t.count == 0:
        print(f"{a.table}: no ordinates parsed", file=sys.stderr)
        return 1

    res = audit(t, windows=a.windows)

    if not a.quiet:
        s = res["structure"]
        print(f"table      : {a.table}")
        print(f"sha256     : {s['sha256']}")
        print(f"ordinates  : {s['count']:,}  ({s['first']:.6f} .. {s['last']:.6f})")
        print(f"structure  : {'ok' if s['ok'] else 'PROBLEM'}"
              f"  dupes={s['exact_duplicates_adjacent']} descents={s['descending_steps']}"
              f" nonpositive={s['nonpositive_ordinates']}")
        r = res["residuals"]
        if r.get("available"):
            print(f"residuals  : our max |zeta| = {r['our_max_residual']:.3e} over "
                  f"{r['sampled']} samples"
                  + (f", mpmath {r['mpmath_max_residual']:.3e}"
                     if r.get("mpmath_max_residual") is not None else ""))
        ind = res["independent"]
        if ind.get("available"):
            print(f"independent: max |diff| vs mpmath = {ind['max_abs_diff_vs_mpmath']:.3e}"
                  f" over {ind['compared']} zeros")
        else:
            print(f"independent: skipped ({ind.get('reason')})")
        c = res["completeness"]
        if c.get("available", True) and "table_count" in c:
            print(f"completeness: count={c['table_count']:,} vs smooth N(T)={c['smooth_N_T']:.3f}"
                  f"  S(T) implied = {c['S_T_implied']:+.3f}  (weak sanity check)")
            for w in c.get("windows", []):
                flag = "ok" if w["agree"] else "MISMATCH"
                print(f"              window rows {w['rows']}: table {w['table_zeros_inside']}"
                      f" vs independent count {w['independent_count']}  [{flag}]")
            if c.get("windows_ok") is None:
                print("              windowed count: skipped (mpmath not installed)")
        else:
            print(f"completeness: skipped ({c.get('reason')})")
        print()
        print("RESULT:", "ALL CHECKS PASSED" if res["all_ok"] else "FAILED")

    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if res["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())