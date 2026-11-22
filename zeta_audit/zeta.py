"""ζ(s) on and near the critical line, plus the Riemann–Siegel theta / Z functions.

Pure ``math`` / ``cmath`` implementation (no mpmath, no C extension), so the whole
pipeline runs anywhere Python runs.

Reference engine: Euler–Maclaurin summation with N ≈ |t| terms and K Bernoulli
terms.  Accuracy at |t| ≤ 10^4 is ~1e-13 or better (verified in tests).

The theta function is computed from the complex Stirling series for
log Γ(1/4 + it/2), which is accurate for t ≥ 6.
"""

from __future__ import annotations

import cmath
import math

# B_2, B_4, ... B_12 (Faulhaber / Bernoulli numbers with the "old" convention)
BERNOULLI = (
    (2, 1.0 / 6.0),
    (4, -1.0 / 30.0),
    (6, 1.0 / 42.0),
    (8, -1.0 / 30.0),
    (10, 5.0 / 66.0),
    (12, -691.0 / 2730.0),
)

LN2PI = math.log(2.0 * math.pi)


def _rising(s: complex, m: int) -> complex:
    """s(s+1)...(s+m-1), the rising factorial."""
    p = 1.0 + 0.0j
    for j in range(m):
        p *= s + j
    return p


def zeta(s, n_terms: int | None = None, k_terms: int = 5) -> complex:
    """Euler–Maclaurin evaluation of ζ(s).

    ζ(s) = Σ_{n<N} n^{-s} + N^{1-s}/(s-1) + N^{-s}/2
           + Σ_{k=1..K} B_{2k}/(2k)! · s(s+1)…(s+2k-2) · N^{-s-2k+1}
    """
    s = complex(s)
    if s == 1:
        raise ValueError("pole")
    t = abs(s.imag)
    N = n_terms if n_terms else max(16, int(t) + 8)
    log = math.log
    total = 0j
    for n in range(1, N):
        total += cmath.exp(-s * log(n))
    lnN = log(N)
    total += cmath.exp((1 - s) * lnN) / (s - 1)
    total += 0.5 * cmath.exp(-s * lnN)
    for k2, b in BERNOULLI[:k_terms]:
        total += (b / math.factorial(k2)) * _rising(s, k2 - 1) * cmath.exp((-s - k2 + 1) * lnN)
    return total


def zeta_half(t: float, n_terms: int | None = None, k_terms: int = 5) -> complex:
    """ζ(1/2 + it) — the hot path, using real cos/sin instead of cexp."""
    N = n_terms if n_terms else max(16, int(t) + 8)
    re = 0.0
    im = 0.0
    log = math.log
    cos = math.cos
    sin = math.sin
    sqrt = math.sqrt
    for n in range(1, N):
        ang = t * log(n)
        amp = 1.0 / sqrt(n)
        re += amp * cos(ang)
        im -= amp * sin(ang)
    s = 0.5 + 1j * t
    lnN = log(N)
    tail = cmath.exp((1 - s) * lnN) / (s - 1) + 0.5 * cmath.exp(-s * lnN)
    for k2, b in BERNOULLI[:k_terms]:
        tail += (b / math.factorial(k2)) * _rising(s, k2 - 1) * cmath.exp((-s - k2 + 1) * lnN)
    return complex(re, im) + tail


def theta(t: float) -> float:
    """Riemann–Siegel theta: Im log Γ(1/4 + it/2) − (t/2) log π.

    The Stirling series is only valid for t ≳ 20 (it loses ~2.6 rad of accuracy at
    t = 10), so small t is routed to the quadrature of θ'(t). Zeros themselves do not
    care — Z(t) = 0 iff ζ(1/2+it) = 0 whatever the phase — but N(T) = θ(T)/π + 1 and
    the Z chart do, and an off-by-radians θ silently corrupts both.
    """
    if t < 20.0:
        return theta_small_t(t)
    z = 0.25 + 0.5j * t
    lg = (
        (z - 0.5) * cmath.log(z)
        - z
        + 0.5 * LN2PI
        + 1.0 / (12.0 * z)
        - 1.0 / (360.0 * z ** 3)
        + 1.0 / (1260.0 * z ** 5)
    )
    return lg.imag - 0.5 * t * math.log(math.pi)


def Z(t: float, n_terms: int | None = None) -> float:
    """Hardy's Z function: e^{iθ(t)} ζ(1/2+it), real for real t."""
    z = zeta_half(t, n_terms=n_terms)
    th = theta(t)
    return math.cos(th) * z.real - math.sin(th) * z.imag


def zeta_on_line(t: float, n_terms: int | None = None) -> complex:
    """Convenience alias used by the zero-finder and the explicit formula."""
    return zeta_half(t, n_terms=n_terms)


def n_zeros_asymptotic(T: float) -> float:
    """N(T) = θ(T)/π + 1 + S(T); the first two terms are the smooth part."""
    return theta(T) / math.pi + 1.0


def theta_small_t(t: float) -> float:
    """θ(t) for t < 20 via Simpson quadrature of θ'(t).

    θ'(t) = ½·Re ψ(1/4 + it/2) − ½·log π,  θ(0) = 0.

    The Stirling series used by ``theta`` needs |t| ≳ 20; below that it is off by
    radians, which corrupts N(T) = θ(T)/π + 1 and the Z chart.
    """
    steps = 480 if t > 8 else 240
    h = t / steps
    acc = 0.0
    half_ln_pi = 0.5 * math.log(math.pi)
    for i in range(steps + 1):
        x = i * h
        f = 0.5 * _digamma_complex(0.25 + 0.5j * x).real - half_ln_pi
        w = 1.0 if i in (0, steps) else (4.0 if i % 2 else 2.0)
        acc += w * f
    return acc * h / 3.0


def _digamma_complex(z: complex) -> complex:
    """ψ(z) by recurrence to |z| ≥ 8 then the asymptotic series."""
    shift = 0.0
    while abs(z) < 8:
        shift -= 1.0 / z
        z += 1
    inv = 1.0 / z
    inv2 = inv * inv
    series = (
        cmath.log(z)
        - 0.5 * inv
        - inv2
        * (1.0 / 12.0 - inv2 * (1.0 / 120.0 - inv2 * (1.0 / 252.0 - inv2 * (1.0 / 240.0 - inv2 / 132.0))))
    )
    return series + shift