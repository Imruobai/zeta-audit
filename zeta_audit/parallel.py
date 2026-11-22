"""Parallel exhaustive base sweep (parallel to the point of being measurable).

Proving n prime under the ERH/GRH base bound means showing *no* base a <= 2 log^2 n is a
Miller-Rabin witness. That is an embarrassingly parallel search with a one-sided answer:

  * any worker that finds a witness => n is composite (unconditional proof, stop);
  * all workers exhaust their shares with no witness => n is prime *given ERH/GRH*
    (unconditionally, if n < 3.317e24 via the 13-base set).

Cost model, measured here: one 1024-bit modexp ≈ 2 ms, base count ≈ 8·10⁴, so a
sequential sweep is minutes and a 16-core sweep is seconds. This module makes the
difference measurable instead of hand-waved.

Falls back to a sequential sweep when multiprocessing is unavailable.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from .primality import SMALL_PRIMES, _mr_witness, passes_prefilter, rh_bases, rh_base_bound


@dataclass
class SweepResult:
    n_bits: int
    base_ceil: float
    bases_total: int
    bases_tested: int
    verdict: str
    witness: int | None
    workers: int
    elapsed_s: float
    modexp_per_s: float

    def as_dict(self) -> dict:
        return {
            "n_bits": self.n_bits,
            "base_ceiling": self.base_ceil,
            "bases_total": self.bases_total,
            "bases_tested": self.bases_tested,
            "verdict": self.verdict,
            "witness": self.witness,
            "workers": self.workers,
            "elapsed_s": round(self.elapsed_s, 2),
            "modexp_per_s": round(self.modexp_per_s, 1),
        }


def _chunk_worker(args):
    """Test a slice of bases; return the first witness found (or None)."""
    n, chunk = args
    for a in chunk:
        if _mr_witness(n, a):
            return a
    return None


def sweep_parallel(n: int, workers: int | None = None, chunk: int = 64) -> SweepResult:
    workers = workers or max(1, min(32, (os.cpu_count() or 4)))
    bases = rh_bases(n)
    t0 = time.time()
    tested = 0
    witness = None

    if not passes_prefilter(n):
        # prefilter rejections are unconditional: some small prime either divides n
        # or is a Miller-Rabin witness. Report that witness, do not just say "no".
        witness = None
        for a in SMALL_PRIMES:
            if n % a == 0:
                witness = a
                break
            if _mr_witness(n, a):
                witness = a
                break
        return SweepResult(
            n_bits=n.bit_length(),
            base_ceil=rh_base_bound(n),
            bases_total=len(rh_bases(n)),
            bases_tested=0,
            verdict="composite",
            witness=witness,
            workers=1,
            elapsed_s=time.time() - t0,
            modexp_per_s=0.0,
        )

    if workers > 1 and len(bases) > 256:
        try:
            from multiprocessing import Pool

            chunks = [(n, bases[i:i + chunk]) for i in range(0, len(bases), chunk)]
            with Pool(workers) as pool:
                for res in pool.imap_unordered(_chunk_worker, chunks, chunksize=1):
                    tested += chunk if res is None else chunk
                    if res is not None:
                        witness = res
                        pool.terminate()
                        break
        except Exception:  # noqa: BLE001 - fall back to sequential
            witness, tested = None, 0
            workers = 1

    if witness is None and (workers == 1 or tested == 0):
        for i, a in enumerate(bases):
            tested = i + 1
            if _mr_witness(n, a):
                witness = a
                break

    elapsed = time.time() - t0
    verdict = "composite" if witness is not None else "prime"
    tested = min(tested or len(bases), len(bases))
    return SweepResult(
        n_bits=n.bit_length(),
        base_ceil=rh_base_bound(n),
        bases_total=len(bases),
        bases_tested=tested,
        verdict=verdict,
        witness=witness,
        workers=workers,
        elapsed_s=elapsed,
        modexp_per_s=(tested / elapsed) if elapsed > 0 else 0.0,
    )


def single_thread_rate(n: int, sample: int = 32, min_dt: float = 0.02) -> float:
    """Modexp per second on one thread, measured on a sample of bases.

    Small moduli run in microseconds, so the sample is repeated until the clock has
    actually advanced (``min_dt``); otherwise the rate would be a division by ~0.
    Used to convert parallel wall-clock into an honest sequential estimate instead of
    a guessed constant.
    """
    bases = rh_bases(n)[:sample]
    if not bases:
        return 0.0
    done = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < min_dt:
        for a in bases:
            _mr_witness(n, a)
            done += 1
    dt = time.perf_counter() - t0
    return done / dt if dt > 0 else 0.0


def estimate_sequential(n: int, sample: int = 32) -> dict:
    rate = single_thread_rate(n, sample)
    total = len(rh_bases(n))
    secs = total / rate if rate else None
    return {
        "single_thread_modexp_per_s": round(rate, 1),
        "bases": total,
        # keep sub-second resolution: a 128-bit sweep is milliseconds, and rounding to
        # 0.0 s would read as "no estimate" downstream
        "sequential_estimate_s": round(secs, 4) if secs is not None else None,
        "sampled_bases": min(sample, total),
    }


def benchmark(bits_list=(256, 512, 1024), workers_list=(1, None)) -> list[dict]:
    import secrets

    rows = []
    for bits in bits_list:
        n = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        # find a prime of this size with the sequential path first (cheap: prefilter kills)
        from .certify import next_prime

        p, _ = next_prime(n)
        for w in workers_list:
            r = sweep_parallel(p, workers=w)
            row = r.as_dict()
            row["base_ceiling"] = round(rh_base_bound(p), 1)
            rows.append(row)
    return rows


if __name__ == "__main__":
    import json

    print(json.dumps(benchmark(), indent=2))