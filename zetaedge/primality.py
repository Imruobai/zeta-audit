"""Primality testing with the base list treated as a *checkable certificate*, not a guess.

Correctness condition, stated accurately: Miller-Rabin is deterministic on n once no base
in the set is a witness, and the "all primes a <= 2 log^2 n" bound is what **ERH/GRH**
gives (Bach 1990, on the least quadratic nonresidue). Plain RH does NOT imply it: RH says
nothing about zeros of Dirichlet L-functions, which is what the base bound needs. An
earlier version of this file said "under RH"; that was wrong and is corrected here.

So the output is reported as a *conditional* statement, and the hypothesis actually used
is printed next to the verdict. Individually re-checkable content: "these bases were
tested and none witnessed". That is the honest form of the claim.

The 13-base test below is unconditional below 3.317e24 and is used as an independent
oracle wherever both are defined.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

SMALL_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]

HYPOTHESIS = (
    "ERH/GRH, not plain RH: predicts every prime a <= 2 log^2 n is a quadratic "
    "nonresidue mod n, so no composite passes all of them. Unconditional for the "
    "13-base set below 3.317e24 (Sorenson-Webster)."
)

_BASE_CACHE: dict[float, list[int]] = {}


def _primes_upto_float(limit: float) -> list[int]:
    n = int(math.floor(limit))
    if n < 2:
        return []
    sieve = bytearray([1]) * (n + 1)
    sieve[0:2] = b"\x00\x00"
    for p in range(2, int(n ** 0.5) + 1):
        if sieve[p]:
            sieve[p * p :: p] = bytearray(len(range(p * p, n + 1, p)))
    return [i for i in range(2, n + 1) if sieve[i]]


def rh_base_bound(n: int) -> float:
    """2 log²n — the base ceiling that suffices under ERH/GRH (not plain RH)."""
    return 2.0 * math.log(n) ** 2


def rh_bases(n: int) -> list[int]:
    """Every prime base up to 2 log²n (the ERH/GRH-sufficient set).

    Cached by the *exact* floor of the ceiling: rounding the cache key would hand one
    n a base list computed for a different ceiling, which makes certificates
    irreproducible (caught by verify.py). Do not "optimise" this key.
    """
    bound = rh_base_bound(n)
    key = int(math.floor(bound))
    hit = _BASE_CACHE.get(key)
    if hit is not None:
        return hit
    bases = _primes_upto_float(bound)
    if len(_BASE_CACHE) > 64:
        _BASE_CACHE.clear()
    _BASE_CACHE[key] = bases
    return bases


def _mr_witness(n: int, a: int) -> bool:
    """True if a is a Miller–Rabin witness for the compositeness of n."""
    if n % 2 == 0:
        return n != 2
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    x = pow(a, d, n)
    if x == 1 or x == n - 1:
        return False
    for _ in range(s - 1):
        x = x * x % n
        if x == n - 1:
            return False
    return True


def is_prime_rh(n: int) -> bool:
    """Deterministic assuming ERH/GRH: test all bases <= 2 log^2 n.

    Name is kept for API stability; the hypothesis in force is ``HYPOTHESIS`` above.
    """
    if n < 2:
        return False
    for p in SMALL_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False
    for a in rh_bases(n):
        if _mr_witness(n, a):
            return False
    return True


def passes_prefilter(n: int, rounds: int = 12) -> bool:
    """Certified compositeness rejection with the standard small-base set.

    Rejections are unconditionally correct: a base that witnesses compositeness has
    *proved* compositeness, no hypothesis needed. A pass only means "worth the full
    ERH/GRH base sweep", so this prefilter never weakens the final certificate.
    """
    if n < 2:
        return False
    for p in SMALL_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False
    for a in SMALL_PRIMES[:rounds]:
        if _mr_witness(n, a):
            return False
    return True


def is_prime_13(n: int) -> bool:
    """Deterministic for n < 3,317,044,064,679,887,385,961,981 (first 13 primes)."""
    if n < 2:
        return False
    for p in SMALL_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False
    for a in SMALL_PRIMES:
        if _mr_witness(n, a):
            return False
    return True


@dataclass
class Certificate:
    n: int
    bits: int
    bases: list[int]
    bound: float
    verdict: str
    witness: int | None = None

    def as_dict(self) -> dict:
        return {
            "n": str(self.n),
            "bits": self.bits,
            "base_count": len(self.bases),
            "base_ceiling": self.bound,
            "verdict": self.verdict,
            "witness": self.witness,
            "hypothesis": HYPOTHESIS,
            "claim": (
                "all bases a <= 2 log^2 n were tested and none is a Miller-Rabin "
                "witness; the verdict is conditional on the hypothesis above and is "
                "unconditionally valid when n < 3.317e24"
            ),
        }


def certify(n: int, base_cap: int | None = None) -> Certificate:
    """Full base sweep, optionally truncated to ``base_cap``.

    ``base_cap`` exists only for fast previews: a truncated verdict is reported as
    "probable" so it can never be mistaken for a certificate.
    """
    bits = n.bit_length()
    ceiling = rh_base_bound(n) if n > 2 else 0.0
    bases = rh_bases(n) if base_cap is None else [a for a in rh_bases(n) if a <= base_cap]
    truncated = base_cap is not None and len(bases) < len(rh_bases(n))
    if n < 2:
        return Certificate(n, bits, [], 0.0, "composite")
    for p in SMALL_PRIMES:
        if n == p:
            return Certificate(n, bits, bases, ceiling, "prime")
        if n % p == 0:
            return Certificate(n, bits, bases, ceiling, "composite", witness=p)
    for a in bases:
        if _mr_witness(n, a):
            return Certificate(n, bits, bases, ceiling, "composite", witness=a)
    return Certificate(n, bits, bases, ceiling, "probable" if truncated else "prime")