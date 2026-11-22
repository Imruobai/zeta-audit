"""Attested prime generation (demonstration wrapper, not a commercial offering).

One call produces: a prime of the requested bit size, a certificate block, the observed
scan length, the RH-conditional gap ceiling (Cramér), and an append-only log entry.

Status of the verdict: "prime" here means "every prime base <= 2 log^2 n was tested and
none witnessed", which is exact under ERH/GRH (Bach 1990) and unconditional below
3.317e24. The block prints the hypothesis so it cannot be read as an unconditional proof.
Nothing in this module is a product: the sweep is ~100x slower than fixed-base MR.
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass, asdict
from pathlib import Path

from .bounds import cramer_gap_ceiling
from .certify import certificate, next_prime
from .parallel import estimate_sequential, sweep_parallel
from .primality import rh_base_bound
from .transparency import CertificateLog


@dataclass
class Attestation:
    requested_bits: int
    prime: str
    actual_bits: int
    delta_from_start: str
    candidates_scanned: int
    provable_scan_ceiling: float
    base_count: int
    base_ceiling: float
    verdict: str
    fingerprint: str
    sequential_estimate_s: float | None
    elapsed_s: float
    log_seq: int | None
    log_entry_hash: str | None
    theorem: str

    def as_dict(self) -> dict:
        return asdict(self)

    def json(self, indent: int = 2) -> str:
        return json.dumps(self.as_dict(), indent=indent, ensure_ascii=False)


def attest(
    bits: int = 256,
    log: CertificateLog | None = None,
    start: int | None = None,
    workers: int | None = None,
    measure_sequential: bool = True,
) -> Attestation:
    """Generate one attested prime. ``workers`` > 1 re-proves via the parallel sweep."""
    t0 = time.time()
    start_value = start if start is not None else (secrets.randbits(bits) | (1 << (bits - 1)) | 1)
    p, scanned = next_prime(start_value)
    cert = certificate(p, cross_check=bits <= 62)

    verdict = cert.verdict
    if workers and workers > 1 and verdict == "prime":
        sweep = sweep_parallel(p, workers=workers)
        verdict = sweep.verdict

    est = estimate_sequential(p) if measure_sequential else None
    seq = None
    entry_hash = None
    if log is not None:
        rec = cert.as_dict()
        rec["base_count"] = len(rec.pop("bases"))
        rec["bases_preview"] = cert.bases[:8]
        rec["candidates_scanned"] = scanned
        rec["requested_bits"] = bits
        rec["provable_scan_ceiling"] = cramer_gap_ceiling(p)
        entry = log.append(rec)
        seq, entry_hash = entry.seq, entry.hash

    return Attestation(
        requested_bits=bits,
        prime=str(p),
        actual_bits=p.bit_length(),
        delta_from_start=str(p - start_value),
        candidates_scanned=scanned,
        provable_scan_ceiling=cramer_gap_ceiling(p),
        base_count=len(cert.bases),
        base_ceiling=rh_base_bound(p),
        verdict=verdict,
        fingerprint=cert.hmac_fingerprint,
        sequential_estimate_s=(
            est["sequential_estimate_s"]
            if est is not None and est["sequential_estimate_s"] is not None
            else None
        ),
        elapsed_s=round(time.time() - t0, 2),
        log_seq=seq,
        log_entry_hash=entry_hash,
        theorem=cert.theorem,
    )


def batch(
    bits_list=(128, 256, 512),
    log_path: str | Path | None = None,
    out_dir: str | Path | None = None,
    reset_log: bool = False,
) -> dict:
    """Attest one prime per requested size, write attestations + the CT log.

    ``reset_log`` truncates an existing log first. That is what a reproducible pipeline
    run wants (a fresh anchor per run); a production log would never reset, because the
    entire point of an append-only log is that it does not.
    """
    if log_path and reset_log:
        Path(log_path).unlink(missing_ok=True)
    log = CertificateLog(log_path) if log_path else None
    rows = []
    for bits in bits_list:
        a = attest(bits=bits, log=log)
        rows.append(a.as_dict())
        print(f"  {bits:>4} bits -> {a.actual_bits} bits, +{a.delta_from_start}, "
              f"{a.base_count:,} bases, {a.elapsed_s}s")
        if out_dir:
            d = Path(out_dir)
            d.mkdir(parents=True, exist_ok=True)
            (d / f"attestation_{bits}.json").write_text(a.json(), encoding="utf-8")

    result = {"rows": rows}
    if log is not None:
        result["chain"] = log.verify()
        result["anchor"] = log.anchor()
    if out_dir:
        d = Path(out_dir)
        (d / "batch_attestations.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="attested prime generation (rhprime)")
    ap.add_argument("--bits", default="128,256,512")
    ap.add_argument("--log", default="out/ct.log")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    res = batch(tuple(int(b) for b in a.bits.split(",")), a.log, a.out)
    print(json.dumps(res.get("anchor", {}), indent=2))