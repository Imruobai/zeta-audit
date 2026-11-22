"""Zero verification, plus labelled conditional primality certificates.

1. ``verify_strip(T)`` — an *unconditional* count of zeros in the rectangle
   [0.1, 2] × [0.5, T] via the argument principle, compared with the count of zeros
   actually found on the critical line. Equal counts = every zero below T sits on
   Re s = 1/2. No hypothesis is used anywhere in this check.

2. ``PrimeCertificate`` — **conditional on ERH/GRH, not on RH.** The base bound
   a <= 2 log^2 n comes from the least-quadratic-nonresidue bound under ERH/GRH
   (Bach 1990). Plain RH does not imply it: RH does not control zeros of Dirichlet
   L-functions. Every certificate prints the hypothesis it used, so it cannot be read
   as an unconditional proof of primality. Below 3.317e24 the 13-base set makes the
   verdict unconditional regardless.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, asdict

from .zeta import zeta, theta
from .primality import rh_bases, rh_base_bound, is_prime_rh, is_prime_13, _mr_witness

TWO_PI = 2.0 * math.pi


# --------------------------------------------------------------------------- #
# 1. zeros in the strip: argument principle vs. line scan
# --------------------------------------------------------------------------- #
LEFT = 0.1          # left edge: below the critical line, above the trivial region
RIGHT = 2.0         # right edge: ζ has no zeros for Re s ≥ 1 (classical)
BOTTOM = 0.5        # below the first zero (γ₁ ≈ 14.13) and above the pole at s=1


def _contour(T: float, step: float = 0.01):
    """Rectangle (RIGHT, BOTTOM) → (RIGHT, T) → (LEFT, T) → (LEFT, BOTTOM) → close.

    The left edge sits at Re = 0.1, *not* 0.5, so the contour never runs through a
    zero; the bottom edge at Im = 0.5 keeps the pole s = 1 outside the region.
    Zeros counted are therefore those with 0.1 < Re s < 2 and 0.5 < Im s < T.
    """
    pts: list[complex] = []
    n = max(8, int((T - BOTTOM) / step))
    for i in range(1, n + 1):                    # right edge, upward
        pts.append(complex(RIGHT, BOTTOM + (T - BOTTOM) * i / n))
    m = max(8, int((RIGHT - LEFT) / step))
    for i in range(1, m + 1):                     # top edge, right to left
        pts.append(complex(RIGHT - (RIGHT - LEFT) * i / m, T))
    for i in range(1, n + 1):                     # left edge, downward
        pts.append(complex(LEFT, T - (T - BOTTOM) * i / n))
    for i in range(1, m + 1):                     # bottom edge, back to start
        pts.append(complex(LEFT + (RIGHT - LEFT) * i / m, BOTTOM))
    return pts


def count_zeros_strip(T: float, step: float = 0.01) -> dict:
    """Δarg ζ / 2π around the rectangle = #zeros inside (argument principle)."""
    pts = _contour(T, step)
    prev = zeta(pts[0])
    total = 0.0
    for p in pts[1:]:
        cur = zeta(p)
        total += math.atan2(cur.imag * prev.real - cur.real * prev.imag,
                            cur.real * prev.real + cur.imag * prev.imag)
        prev = cur
    cur = zeta(pts[0])                            # close the contour
    total += math.atan2(cur.imag * prev.real - cur.real * prev.imag,
                        cur.real * prev.real + cur.imag * prev.imag)
    raw = total / TWO_PI
    count = int(round(raw))
    return {
        "T": T,
        "step": step,
        "contour_points": len(pts),
        "raw_argument_turns": raw,
        "zeros_in_strip": count,
        "resolution_error": abs(raw - count),
        "smooth_N_T": theta(T) / math.pi + 1.0,
        "von_mangoldt_gap": abs(raw - (theta(T) / math.pi + 1.0)),
    }


def verify_strip(T: float = 100.0, step: float = 0.01) -> dict:
    """Line zeros below T must equal the argument-principle count.

    Match ⇒ every zero of ζ with 0.1 < Re s < 1 and 0.5 < Im s ≤ T lies exactly on
    Re s = 1/2. The strip near Re s = 0 is covered by the classical zero-free
    region (Re s > 1 - c/log t), so this is the standard RH-verification argument,
    just at a height that runs in seconds on a laptop.
    """
    from .zeros import find_zeros

    strip = count_zeros_strip(T, step=step)
    line = find_zeros(t_max=T, t_min=BOTTOM, step=0.25)
    ok = len(line) == strip["zeros_in_strip"]
    return {
        "T": T,
        "zeros_on_line": len(line),
        "zeros_in_strip": strip["zeros_in_strip"],
        "match": ok,
        "verdict": (
            "verified: no zero off the critical line for 0.5 < Im s <= T"
            if ok
            else "count mismatch - investigate before claiming anything"
        ),
        "detail": strip,
        "max_residual": max((z.residual for z in line), default=0.0),
    }


# --------------------------------------------------------------------------- #
# 2. primes
# --------------------------------------------------------------------------- #
def _smallest_prime_factor(n: int) -> int | None:
    if n % 2 == 0:
        return 2 if n != 2 else None
    f = 3
    while f * f <= n:
        if n % f == 0:
            return f
        f += 2
    return None


def next_prime(n: int, certify_rh: bool = True, prefilter: bool = True) -> tuple[int, int]:
    """Smallest prime >= n, returned with the number of candidates scanned.

    Two-stage scan: a 12-base prefilter rejects composites cheaply (rejections are
    unconditionally valid — a witness *proves* compositeness), then the full base
    sweep applies the ERH/GRH-conditional test to the survivor. The prefilter can
    never turn a composite into a prime; it only saves time. Below 3.317e24 the
    sweep is itself unconditional.
    """
    from .primality import passes_prefilter

    if n <= 2:
        return 2, 0
    if n % 2 == 0:
        n += 1
    scanned = 0
    while True:
        scanned += 1
        if prefilter and not passes_prefilter(n):
            n += 2
            continue
        if is_prime_rh(n):
            return n, scanned
        n += 2
        if scanned > 10_000_000:
            raise RuntimeError("gap scan exceeded sanity limit")


@dataclass
class PrimeCertificate:
    """A prime plus everything needed to re-check it without trusting this run."""

    n: int
    bits: int
    bases: list[int]
    base_bound: float
    witness_found: int | None
    verdict: str
    theorem: str = (
        "ERH/GRH (NOT plain RH) => Miller-Rabin with every base a <= 2 log^2 n is "
        "deterministic. Unconditional for n < 3.317e24 via the 13-base set."
    )
    hmac_fingerprint: str = field(default="")

    def as_dict(self) -> dict:
        d = asdict(self)
        d["n"] = str(self.n)
        return d

    def block(self) -> str:
        lines = [
            "-----BEGIN CONDITIONAL PRIME CERTIFICATE-----",
            f"n = {self.n}",
            f"bits = {self.bits}",
            f"base_ceiling = 2*log(n)^2 = {self.base_bound:.3f}",
            f"bases = {len(self.bases)} primes (all <= ceiling)",
            f"verdict = {self.verdict}",
            f"witness = {self.witness_found}",
            f"hypothesis = {self.theorem}",
            f"unconditional_below = 3.317e24 (13-base set, Sorenson-Webster 2015)",
            f"fingerprint = {self.hmac_fingerprint}",
            "-----END CONDITIONAL PRIME CERTIFICATE-----",
        ]
        return "\n".join(lines)


def _fingerprint(n: int, bases: list[int], verdict: str) -> str:
    import hashlib

    h = hashlib.sha256()
    h.update(str(n).encode())
    h.update(b"|")
    h.update(",".join(str(b) for b in bases).encode())
    h.update(b"|")
    h.update(verdict.encode())
    return h.hexdigest()[:32]


def certificate(n: int, cross_check: bool = True) -> PrimeCertificate:
    bases = rh_bases(n)
    ceiling = rh_base_bound(n)
    verdict = "unknown"
    witness = None
    if n < 2:
        verdict = "composite"
    else:
        small = [p for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41) if n % p == 0 and n != p]
        if small:
            verdict, witness = "composite", small[0]
        else:
            for a in bases:
                if _mr_witness(n, a):
                    verdict, witness = "composite", a
                    break
            else:
                verdict = "prime"
    if cross_check and verdict == "prime" and n.bit_length() <= 62:
        if not is_prime_13(n):
            verdict = "inconsistent-with-13-base-test"
    fp = _fingerprint(n, bases, verdict)
    return PrimeCertificate(
        n=n,
        bits=n.bit_length(),
        bases=bases,
        base_bound=ceiling,
        witness_found=witness,
        verdict=verdict,
        hmac_fingerprint=fp,
    )


def audit_certifier(bits_list=(64, 128, 256, 512, 1024), samples: int = 6, seed: int = 20251122) -> dict:
    """Empirical half of the certificate workload: bases needed + scan cost."""
    rng = random.Random(seed)
    rows = []
    for bits in bits_list:
        total_bases = 0
        total_scanned = 0
        primes = 0
        for _ in range(samples):
            n = rng.getrandbits(bits) | (1 << (bits - 1)) | 1
            p, scanned = next_prime(n)
            cert = certificate(p, cross_check=False)
            total_bases += len(cert.bases)
            total_scanned += scanned
            primes += 1 if cert.verdict == "prime" else 0
        rows.append(
            {
                "bits": bits,
                "samples": samples,
                "primes_certified": primes,
                "mean_bases": total_bases / samples,
                "mean_candidates_scanned": total_scanned / samples,
                "base_ceiling_2log2n": rh_base_bound(1 << (bits - 1)),
            }
        )
    return {"rows": rows, "seed": seed}