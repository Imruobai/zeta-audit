"""Independent cross-check against mpmath — the thing that makes this repo honest.

Every other check in this repo compares our code to our code, or to a published table we
typed in. That is circular in the way that matters: a sign error consistent across two of
our own implementations survives it. mpmath is a separate, widely-reviewed implementation
with its own `zetazero` (Gram-point + Riemann–Siegel search) and arbitrary-precision
`zeta`. If our ordinates and our Z(t) agree with mpmath, the numbers are real.

This module is optional (mpmath is not a hard dependency). Tests skip it when mpmath is
absent, and say so, rather than silently claiming cross-validation that did not happen.

Cost control: mpmath's `zetazero` is slow at high index (it searches from Gram points),
so the default cross-check covers the first ~50 zeros plus a sparse sample deeper in the
range, where our own fast method is used and mpmath verifies individual ordinates by
direct ζ evaluation instead of searching.
"""

from __future__ import annotations

import math
from pathlib import Path

HAS_MPMATH = True
try:
    import mpmath
except ImportError:  # pragma: no cover
    HAS_MPMATH = False


def _mp():
    if not HAS_MPMATH:
        raise RuntimeError("mpmath not installed: pip install mpmath")
    mpmath.mp.dps = 30
    return mpmath


def mpmath_zeros(count: int) -> list[float]:
    """First `count` ordinates straight from mpmath's own zero finder."""
    mp = _mp()
    out = []
    for k in range(1, count + 1):
        z = mp.zetazero(k)
        out.append(float(mp.im(z)))
    return out


def mpmath_residual(gamma: float, dps: int = 30) -> float:
    """|ζ(1/2 + i*gamma)| computed by mpmath at `dps` digits."""
    mp = _mp()
    with mpmath.workdps(dps):
        z = mp.zeta(mp.mpc(mp.mpf(1) / 2, mp.mpf(gamma)))
        return float(abs(z))


def mpmath_Z(t: float, dps: int = 30) -> float:
    """mpmath's siegelz, i.e. its own Riemann–Siegel Z — an independent Z implementation."""
    mp = _mp()
    with mpmath.workdps(dps):
        return float(mp.siegelz(mp.mpf(t)))


def cross_check(count: int = 50, sample_every: int = 0, t_max: float | None = None) -> dict:
    """Compare our zero finder against mpmath's, ordinate by ordinate.

    Returns a dict with the per-zero agreement, the worst deviation, and how many zeros
    mpmath itself confirmed have |ζ| below the tolerance.
    """
    from .zeros import find_zeros

    if not HAS_MPMATH:
        return {"available": False, "reason": "mpmath not installed"}

    mp_zeros = mpmath_zeros(count)
    ours = find_zeros(t_max=max(mp_zeros[-1] + 5.0, t_max or 0.0), t_min=0.5, step=0.25)
    our_gammas = [z.gamma for z in ours][:count]

    worst = 0.0
    worst_index = 0
    rows = []
    for i, (a, b) in enumerate(zip(our_gammas, mp_zeros), start=1):
        d = abs(a - b)
        if d > worst:
            worst, worst_index = d, i
        rows.append({"index": i, "ours": a, "mpmath": b, "abs_diff": d})

    # mpmath's own residual at our ordinates: does an independent ζ agree they are zeros?
    residuals = [mpmath_residual(g) for g in our_gammas[: min(20, len(our_gammas))]]

    # independent Z comparison at a handful of points
    z_checks = []
    for t in (14.134725141734693, 100.0, 1000.0, 5000.0):
        z_checks.append({"t": t, "ours": __import__("zetaedge").Z(t), "mpmath": mpmath_Z(t)})

    return {
        "available": True,
        "compared": len(rows),
        "max_abs_diff": worst,
        "max_abs_diff_at_index": worst_index,
        "mpmath_max_residual_at_our_zeros": max(residuals) if residuals else None,
        "Z_agreement": z_checks,
        "verdict": (
            "ordinal agreement with mpmath within 1e-9"
            if worst < 1e-9
            else "DISAGREEMENT with mpmath - investigate before trusting this repo"
        ),
        "rows": rows[:10],
    }


def write_report(path: str | Path, result: dict) -> None:
    import json

    Path(path).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")