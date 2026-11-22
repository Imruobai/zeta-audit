"""Explicit formula, prime counting, and the RH-conditional error bounds.

Under RH every zero sits on Re s = 1/2, so the explicit formula

    ψ(x) = x - Σ_ρ x^ρ/ρ - log 2π - ½ log(1 - x^-2)

has every term bounded by |x^ρ| = √x, which is what turns the zeros into a
*usable* error budget for ψ(x), π(x), and anything built on them.

Two theorems are used as the "post-proof" payload:

  Schoenfeld (1976):  |ψ(x) - x| < (1/8π) √x log²x          for x ≥ 59
                      |π(x) - li(x)| < (1/8π) √x log x      for x ≥ 2657

This module verifies both inequalities numerically over a large range, and
reconstructs ψ(x) from the zeros to show the formula actually converges.
"""

from __future__ import annotations

import math

import numpy as np

from .zeta import zeta

EULER_GAMMA = 0.57721566490153286060651209008240243


# --------------------------------------------------------------------------- #
# exact combinatorial side
# --------------------------------------------------------------------------- #
def primes_upto(n: int) -> np.ndarray:
    """All primes ≤ n via a numpy boolean sieve (fast for n ≤ 1e9)."""
    if n < 2:
        return np.array([], dtype=np.int64)
    sieve = np.ones(n + 1, dtype=bool)
    sieve[:2] = False
    for p in range(2, int(n ** 0.5) + 1):
        if sieve[p]:
            sieve[p * p :: p] = False
    return np.nonzero(sieve)[0].astype(np.int64)


def prime_power_events(x_max: int) -> tuple[np.ndarray, np.ndarray]:
    """Sorted (value, Δψ) events: every prime power p^k ≤ x_max adds log p."""
    primes = primes_upto(x_max)
    vals = []
    deltas = []
    logs = np.log(primes.astype(np.float64))
    for p, lp in zip(primes, logs):
        q = int(p)
        while q <= x_max:
            vals.append(q)
            deltas.append(lp)
            if q > x_max // p:
                break
            q *= p
    order = np.argsort(np.asarray(vals, dtype=np.int64), kind="stable")
    return np.asarray(vals, dtype=np.int64)[order], np.asarray(deltas, dtype=np.float64)[order]


def psi_table(x_max: int) -> tuple[np.ndarray, np.ndarray]:
    """ψ evaluated just after each prime power ≤ x_max."""
    vals, deltas = prime_power_events(x_max)
    psi = np.cumsum(deltas)
    return vals, psi


def chebyshev_psi(x: float, table: tuple[np.ndarray, np.ndarray] | None = None) -> float:
    """Exact ψ(x) = Σ_{p^k ≤ x} log p (jump handled as ψ(x-), i.e. dedicated)."""
    if table is None:
        table = psi_table(int(x))
    vals, psi = table
    idx = np.searchsorted(vals, int(x), side="right") - 1
    return 0.0 if idx < 0 else float(psi[idx])


def chebyshev_psi_between(x: float, table=None) -> float:
    """(ψ(x-) + ψ(x+))/2 — the value the explicit formula converges to."""
    if table is None:
        table = psi_table(int(x) + 1)
    vals, psi = table
    left = np.searchsorted(vals, int(x), side="left")
    right = np.searchsorted(vals, int(x), side="right")
    before = float(psi[left - 1]) if left > 0 else 0.0
    after = float(psi[right - 1]) if right > 0 else 0.0
    return 0.5 * (before + after)


def pi_exact(x: int) -> int:
    return int(np.count_nonzero(primes_upto(x) <= x))


# --------------------------------------------------------------------------- #
# analytic side: li, R, and the zero sum
# --------------------------------------------------------------------------- #
def li(x: float, terms: int = 200) -> float:
    """Logarithmic integral li(x) = Ei(log x) via the Ei power series."""
    if x <= 1.0:
        raise ValueError("li is real only for x > 1")
    z = math.log(x)
    total = EULER_GAMMA + math.log(z)
    term = 1.0
    for k in range(1, terms):
        term *= z / k
        add = term / k
        total += add
        if k > z and abs(add) < 1e-16 * abs(total):
            break
    return total


def mobius_upto(n: int) -> np.ndarray:
    """μ(1..n) by a linear sieve (numpy int8 array, index = value)."""
    mu = np.ones(n + 1, dtype=np.int64)
    is_comp = np.zeros(n + 1, dtype=bool)
    primes: list[int] = []
    mu[0] = 0
    for i in range(2, n + 1):
        if not is_comp[i]:
            primes.append(i)
            mu[i] = -1
        for p in primes:
            ip = i * p
            if ip > n:
                break
            is_comp[ip] = True
            if i % p == 0:
                mu[ip] = 0
                break
            mu[ip] = -mu[i]
    return mu.astype(np.int8)


_MU_CACHE: dict[int, np.ndarray] = {}


def _mu(n: int) -> np.ndarray:
    for k in _MU_CACHE:
        if k >= n:
            return _MU_CACHE[k]
    arr = mobius_upto(max(n, 1000))
    _MU_CACHE[len(arr) - 1] = arr
    return arr


def gram_R(x: float, terms: int = 100) -> float:
    """Riemann's R(x) = 1 + Σ_{k≥1} (log x)^k / (k · k! · ζ(k+1)).

    R(x) is the classic "zero-free" approximation to π(x).  Under RH the error is
    π(x) - R(x) = O(√x log x), and every zero contributes a term of size √x/|ρ|,
    which is why the zeros are the *only* thing left in the error budget.
    """
    if x <= 1.0:
        raise ValueError("R is defined for x > 1")
    lx = math.log(x)
    total = 1.0
    zk = lx
    fact = 1.0
    for k in range(1, terms + 1):
        fact *= k
        total += zk / (k * fact * zeta(k + 1, k_terms=3).real)
        zk *= lx
        if k > lx and abs(zk / (k * fact)) < 1e-18 * max(1.0, abs(total)):
            break
    return total


def gram_R_mobius(x: float, terms: int = 60) -> float:
    """Independent evaluation of R via R(x) = Σ_n μ(n)/n · li(x^{1/n})."""
    lx = math.log(x)
    mu = _mu(terms)
    total = 0.0
    for n in range(1, terms + 1):
        if mu[n] == 0:
            continue
        total += mu[n] / n * li(math.exp(lx / n))
    return total


def psi_explicit(x: float, gammas) -> float:
    """ψ(x) reconstructed from the first zeros: x - Σ_ρ x^ρ/ρ - log2π - ½log(1-x⁻²)."""
    lx = math.log(x)
    sq = math.exp(0.5 * lx)
    acc = 0.0
    for g in gammas:
        rho = complex(0.5, g)
        acc += (cmath_exp(rho * lx) / rho).real
    return x - 2.0 * acc - math.log(2.0 * math.pi) - 0.5 * math.log(1.0 - 1.0 / (x * x))


def cmath_exp(z: complex) -> complex:
    return complex(math.exp(z.real) * math.cos(z.imag), math.exp(z.real) * math.sin(z.imag))


def pi_riemann_R(x: float) -> float:
    """π(x) estimated by R(x) alone — the zero-free baseline.

    Difference from exact π(x) is what the zeros have to pay for; under RH it is
    O(√x log x) and Schoenfeld's constant is checked in ``audit_pi_bound``.
    """
    return gram_R(x)


# --------------------------------------------------------------------------- #
# RH-conditional bounds and their numerical audit
# --------------------------------------------------------------------------- #
def schoenfeld_psi_bound(x: float) -> float:
    return math.sqrt(x) * math.log(x) ** 2 / (8.0 * math.pi)


def schoenfeld_pi_bound(x: float) -> float:
    return math.sqrt(x) * math.log(x) / (8.0 * math.pi)


def audit_psi_bound(x_max: int = 10_000_000, x_min: int = 59) -> dict:
    """max over prime powers of |ψ(x)-x| / bound, plus argmax."""
    vals, psi = psi_table(x_max)
    m = vals >= x_min
    xs = vals[m].astype(np.float64)
    dev = np.abs(psi[m] - xs)
    bound = np.sqrt(xs) * np.log(xs) ** 2 / (8.0 * math.pi)
    ratio = dev / bound
    i = int(np.argmax(ratio))
    return {
        "x_min": x_min,
        "x_max": x_max,
        "points": int(xs.size),
        "max_ratio": float(ratio[i]),
        "argmax_x": int(xs[i]),
        "max_abs_dev": float(dev[i]),
        "bound_at_argmax": float(bound[i]),
        "holds": bool(ratio[i] < 1.0),
    }


def audit_pi_bound(x_max: int = 2_000_000, x_min: int = 2657, stride: int = 137) -> dict:
    """|π(x)-li(x)| < √x log x /(8π) checked on a stride-sampled grid."""
    primes = primes_upto(x_max)
    grid = np.unique(np.arange(x_min, x_max + 1, stride).astype(np.int64))
    worst = 0.0
    arg = 0
    holds = True
    for x in grid.tolist():
        px = int(np.searchsorted(primes, x, side="right"))
        lx = li(float(x))
        dev = abs(px - lx)
        bound = schoenfeld_pi_bound(float(x))
        r = dev / bound
        if r > worst:
            worst, arg = r, x
        if r >= 1.0:
            holds = False
    return {
        "x_min": x_min,
        "x_max": x_max,
        "samples": int(grid.size),
        "max_ratio": worst,
        "argmax_x": arg,
        "holds": holds,
    }


def zero_sum_convergence(x: float, gammas, gamma_counts=(10, 25, 50, 100, 200)) -> list[dict]:
    """Show |ψ(x) - explicit(x, first k zeros)| shrinking as k grows."""
    table = psi_table(int(x) + 1)
    truth = chebyshev_psi_between(x, table)
    out = []
    for k in gamma_counts:
        if k > len(gammas):
            break
        approx = psi_explicit(x, gammas[:k])
        out.append({"zeros": k, "value": approx, "truth": truth, "error": approx - truth})
    return out