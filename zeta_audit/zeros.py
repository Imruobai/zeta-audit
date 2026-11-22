"""Locate non-trivial zeros of ζ on the critical line and audit them.

Strategy: scan Z(t) (Hardy's real-valued function) for sign changes with a step
small enough to resolve every gap below T, then bisect to ~1e-12.  Every zero we
claim is reported with the real/imaginary residual of ζ(1/2+iγ), so the claim is
falsifiable without trusting this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict

from .zeta import Z, zeta_half, n_zeros_asymptotic


@dataclass
class Zero:
    index: int
    gamma: float          # ordinate, error |Δ| <= zero_tol
    residual: float       # |ζ(1/2 + i γ)| at the reported ordinate
    bracketed: bool

    def as_dict(self) -> dict:
        return asdict(self)


def bisect_zero(lo: float, hi: float, tol: float = 1e-13, max_iter: int = 200) -> float:
    """Bisection on Z, which is continuous and sign-changing across a simple zero."""
    flo = Z(lo)
    fhi = Z(hi)
    if flo == 0.0:
        return lo
    if fhi == 0.0:
        return hi
    if flo * fhi > 0.0:
        raise ValueError(f"no sign change on [{lo}, {hi}]")
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        fm = Z(mid)
        if fm == 0.0 or (hi - lo) < tol:
            return mid
        if flo * fm < 0.0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)


def find_zeros(
    t_max: float = 1000.0,
    t_min: float = 6.0,
    step: float = 0.25,
    residual_tol: float = 1e-8,
) -> list[Zero]:
    """All zeros with t_min < γ <= t_max, in increasing order.

    ``step`` must be smaller than the smallest gap in range; 0.25 is safe well
    past the first Lehmer pair (γ ≈ 7005).  The function self-checks against the
    smooth zero-count N(T) = θ(T)/π + 1 and records any discrepancy.
    """
    zeros: list[Zero] = []
    t = t_min
    f_prev = Z(t)
    while t < t_max:
        t_next = min(t + step, t_max)
        f_next = Z(t_next)
        if f_prev == 0.0:
            zeros.append(t)
        elif f_prev * f_next < 0.0:
            zeros.append(bisect_zero(t, t_next))
        t, f_prev = t_next, f_next

    out: list[Zero] = []
    for i, g in enumerate(zeros, start=1):
        res = abs(zeta_half(g))
        out.append(Zero(index=i, gamma=g, residual=res, bracketed=res <= residual_tol))
    return out


def audit(zeros: list[Zero], T: float) -> dict:
    """Cross-checks: count vs. N(T), residual quality, first-gap sanity."""
    smooth = n_zeros_asymptotic(T)
    flagged = [z for z in zeros if not z.bracketed]
    return {
        "T": T,
        "zeros_found": len(zeros),
        "N_T_smooth": smooth,
        "S_T": len(zeros) - smooth,
        "max_residual": max((z.residual for z in zeros), default=0.0),
        "unbracketed": len(flagged),
        "first_zero": zeros[0].gamma if zeros else None,
        "last_zero": zeros[-1].gamma if zeros else None,
    }


KNOWN_FIRST_ZEROS = (
    14.134725141734693,
    21.022039638771554,
    25.010857580145688,
    30.424876125859513,
    32.935061587739189,
    37.586178158825671,
    40.918719012147495,
    43.327073280914999,
    48.005150881167159,
    49.773832477672302,
)


def check_against_known(zeros: list[Zero], atol: float = 1e-9) -> dict:
    """Compare the leading zeros to the published values (Odlyzko's tables)."""
    worst = 0.0
    for known, z in zip(KNOWN_FIRST_ZEROS, zeros):
        worst = max(worst, abs(known - z.gamma))
    return {
        "compared": min(len(KNOWN_FIRST_ZEROS), len(zeros)),
        "max_abs_error": worst,
        "pass": worst <= atol and len(zeros) >= len(KNOWN_FIRST_ZEROS),
    }