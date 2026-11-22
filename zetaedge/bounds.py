"""Prime-gap and π(x) error budgets, with the exact hypothesis for each labelled.

Hypothesis bookkeeping matters here, because the four statements below do **not** share
one:

  gap to next prime <= C sqrt(x) log^2 x     -- Cramér, *conditional on RH*
  |psi(x) - x| < (1/8pi) sqrt(x) log^2 x    -- Schoenfeld 1976, *conditional on RH*
  |pi(x) - li(x)| < (1/8pi) sqrt(x) log x    -- Schoenfeld 1976, *conditional on RH*
  |pi(x) - R(x)| <= 2 sqrt(x) log x / 8pi    -- RH

None of these is currently a theorem; all four are what RH *would* give. The code
therefore reports each as a conditional bound. Empirical ratios against exact values
are printed so a reader can see how tight the conditional constant is, but a ratio
below 1 on a finite range is evidence, not proof.

The Miller–Rabin base bound that used to live in the same story is a different
hypothesis again (ERH/GRH, not RH) and is labelled separately in ``primality.py``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict

import numpy as np

from .explicit import primes_upto, schoenfeld_psi_bound, schoenfeld_pi_bound, li, gram_R


CRAMER_C = 1.0 / (4.0 * math.pi)   # conservative effective constant for gap < C√x log²x


def cramer_gap_log10(x: float | int, c: float = CRAMER_C) -> float:
    """log10 of the RH-conditional gap ceiling — safe for 2048-bit and larger inputs."""
    lx = math.log(x)
    return math.log10(c) + (lx + 2.0 * math.log(lx)) / math.log(10.0)


def cramer_gap_ceiling(x: float | int, c: float = CRAMER_C) -> float:
    """Gap ceiling conditional on RH: C sqrt(x) log^2 x (Cramér 1936).

    Returns ``inf`` once the value exceeds float64 range (≈4096 bits); use
    ``cramer_gap_log10`` in that regime. Note the honest scaling: at 256 bits the
    ceiling is only ~1e-35 of x, so it is a shape argument for crypto sizes, not a
    practical scan budget — the *observed* scan is what one relies on.
    """
    log10 = cramer_gap_log10(x, c)
    if log10 > 300:
        return float("inf")
    return max(2.0, 10 ** log10)


@dataclass
class GapRecord:
    x: int
    gap: int
    ceiling: float
    ratio: float

    def as_dict(self) -> dict:
        return asdict(self)


def gap_audit(x_max: int = 10_000_000, x_min: int = 1_000) -> dict:
    """Largest prime gap ≤ x_max and how much of the RH ceiling it consumes.

    The ratio is only meaningful once x is large enough that the ceiling exceeds
    its 2-unit floor, so the ratio scan starts at ``x_min`` (default 1e3).
    """
    primes = primes_upto(x_max)
    gaps = np.diff(primes)
    base = primes[:-1]
    m = base >= x_min
    gaps_m = gaps[m]
    base_m = base[m]
    ceilings = np.maximum(
        2.0,
        CRAMER_C * np.sqrt(base_m.astype(np.float64)) * np.log(base_m.astype(np.float64)) ** 2,
    )
    ratio = gaps_m / ceilings
    i = int(np.argmax(gaps))
    j = int(np.argmax(ratio))
    order = ratio.argsort()[-5:][::-1]
    return {
        "x_min": x_min,
        "x_max": x_max,
        "primes": int(primes.size),
        "max_gap": int(gaps[i]),
        "max_gap_after": int(base[i]),
        "max_ratio_to_ceiling": float(ratio[j]),
        "ratio_argmax_x": int(base_m[j]),
        "gap_at_ratio_argmax": int(gaps_m[j]),
        "ceiling_at_argmax": float(ceilings[j]),
        "holds": bool(ratio[j] < 1.0),
        "records": [GapRecord(int(b), int(g), float(c), float(r)).as_dict()
                    for b, g, r, c in zip(base_m[order], gaps_m[order],
                                          ratio[order], ceilings[order])],
    }


def pi_error_audit(x_max: int = 2_000_000, stride: int = 997, x_min: int = 2657) -> dict:
    """Compare π(x) against R(x) and li(x) with the RH error bars attached.

    Schoenfeld's π bound is stated for x ≥ 2657; below that the constant is simply
    not claimed, so the grid starts there rather than producing meaningless ratios.
    """
    primes = primes_upto(x_max)
    grid = np.unique(np.arange(x_min, x_max + 1, stride, dtype=np.int64))
    rows = []
    worst_R = 0.0
    worst_li = 0.0
    for x in grid.tolist():
        px = int(np.searchsorted(primes, x, side="right"))
        rx = gram_R(float(x))
        lx = li(float(x))
        bL = schoenfeld_pi_bound(float(x))
        bR = schoenfeld_pi_bound(float(x))
        rR = abs(px - rx) / bR
        rL = abs(px - lx) / bL
        worst_R = max(worst_R, rR)
        worst_li = max(worst_li, rL)
        rows.append({"x": x, "pi": px, "R": rx, "li": lx,
                     "err_R": px - rx, "err_li": px - lx,
                     "bar_R": bR, "bar_li": bL})
    return {
        "x_min": x_min,
        "x_max": x_max,
        "samples": len(rows),
        "max_ratio_R": worst_R,
        "max_ratio_li": worst_li,
        "holds": worst_R < 1.0 and worst_li < 1.0,
        "note": "ratio < 1 means the Schoenfeld error bar covers the truth everywhere sampled",
        "rows": rows,
    }


def psi_zero_truncation_bound(x: float, gammas) -> float:
    """Bound on the tail Σ_{|γ|>T} √x/|ρ| ≈ √x·(log T)/(2π) for the explicit formula."""
    T = max(gammas) if len(gammas) else 1.0
    return math.sqrt(x) * math.log(T) / (2.0 * math.pi) * 2.0